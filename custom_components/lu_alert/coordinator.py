"""DataUpdateCoordinator for the LU-Alert integration."""
from __future__ import annotations
import logging
from datetime import timedelta, datetime
import asyncio

import async_timeout
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import (
    DATASET_API_URL,
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CONF_MIN_SEVERITY,
    DEFAULT_MIN_SEVERITY,
    CONF_ENABLE_LOCATION_FILTER,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    DEFAULT_ENABLE_LOCATION_FILTER,
    CONF_ALLERGENS,
    DEFAULT_ALLERGENS,
)
from .parser import parse_xml
from .utils import is_point_in_polygons
from .enums import Severity, Category, MsgType
from .models import Alert, Info

_LOGGER = logging.getLogger(__name__)

# Define the order of severity for filtering. Higher number is more severe.
SEVERITY_ORDER = {
    Severity.TEST.value: -2,
    Severity.UNKNOWN.value: -1,
    Severity.INFORMATION.value: 0,
    Severity.MINOR.value: 1,
    Severity.MODERATE.value: 2,
    Severity.SEVERE.value: 3,
    Severity.EXTREME.value: 4,
}

# Mapping from cb-lu-level parameter to Severity enum
LEVEL_TO_SEVERITY = {
    # Extreme
    "N1": Severity.EXTREME,
    "L1": Severity.EXTREME,
    "D": Severity.EXTREME,
    "LU-Alert Level 1": Severity.EXTREME,
    "ALERT_LVL_1": Severity.EXTREME,

    # Severe
    "N2": Severity.SEVERE,
    "L2": Severity.SEVERE,
    "LU-Alert Level 2": Severity.SEVERE,
    "ALERT_LVL_2": Severity.SEVERE,

    # Moderate
    "A": Severity.MODERATE,
    "LU-Alert Amber": Severity.MODERATE,

    # Minor
    "N3": Severity.MINOR,
    "L3": Severity.MINOR,
    "LU-Alert Level 3": Severity.MINOR,
    "ALERT_LVL_3": Severity.MINOR,

    # Information
    "I": Severity.INFORMATION,
    "LU-Alert Level 4": Severity.INFORMATION,
    "ALERT_LVL_4": Severity.INFORMATION,

    # Test
    "T": Severity.TEST,
    "LU-Alert Test": Severity.TEST,
    "LU-Alert Exercise": Severity.TEST,
}

# Set of alert levels that should be considered as "Test" and filtered out
TEST_ALERT_LEVELS = {"T", "D", "LU-Alert Test", "LU-Alert Exercise"}


def _parse_references(references_str: str | None) -> list[str]:
    """Parse the references string into a list of alert identifiers."""
    if not references_str:
        return []

    identifiers = []
    # The string is space-separated, and each part is comma-separated.
    parts = references_str.strip().split()
    for part in parts:
        # Each part is like "sender,identifier,sent_time"
        sub_parts = part.split(',')
        if len(sub_parts) > 1:
            # The identifier is the second element
            identifiers.append(sub_parts[1])
    return identifiers


class LuAlertDataUpdateCoordinator(DataUpdateCoordinator):
    """A coordinator to fetch, parse, and filter LU-Alert data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.config_entry = entry

    @property
    def min_severity_level(self) -> int:
        """Get the minimum severity level from config options or data."""
        # Prioritize options, but fall back to data for initial setup
        severity_str = self.config_entry.options.get(CONF_MIN_SEVERITY) or self.config_entry.data.get(
            CONF_MIN_SEVERITY, DEFAULT_MIN_SEVERITY
        )
        return SEVERITY_ORDER.get(severity_str, 0)

    async def _async_update_data(self) -> dict:
        """Fetch, process, and filter data from the LU-Alert feed."""
        xml_urls = await self._get_all_alert_urls()
        if not xml_urls:
            _LOGGER.info("No alert XML URLs found.")
            return self._get_default_state()

        # Concurrently fetch all XML files to improve performance
        fetch_tasks = [self._fetch_xml_content(url) for url in xml_urls]
        all_xml_contents = await asyncio.gather(*fetch_tasks)

        all_alerts = []
        for i, xml_content in enumerate(all_xml_contents):
            if not xml_content:
                continue  # Skip failed downloads

            try:
                # Use hass.async_add_executor_job for the CPU-bound parsing
                alerts_from_file = await self.hass.async_add_executor_job(
                    parse_xml, xml_content
                )
                all_alerts.extend(alerts_from_file)
            except Exception as err:
                # Log the specific URL that failed to parse
                _LOGGER.warning(f"Failed to parse alert XML from {xml_urls[i]}: {err}")

        # --- Start of new deduplication logic ---
        if not all_alerts:
            return self._get_default_state()

        # 1. Create a dictionary of alerts by ID, keeping the most recent one.
        alerts_by_id: dict[str, Alert] = {}
        for alert in all_alerts:
            if not alert.identifier or not alert.sent:
                continue
            if (
                alert.identifier not in alerts_by_id
                or alert.sent > alerts_by_id[alert.identifier].sent
            ):
                alerts_by_id[alert.identifier] = alert

        # 2. Identify all superseded or canceled alerts.
        ids_to_remove = set()
        for alert in alerts_by_id.values():
            # If an alert is a cancellation, it should be removed.
            if alert.msgType == MsgType.CANCEL:
                ids_to_remove.add(alert.identifier)

            # The alerts it refers to should also be removed.
            if alert.references:
                referenced_ids = _parse_references(alert.references)
                for ref_id in referenced_ids:
                    ids_to_remove.add(ref_id)

        # 3. Create the final list of active, deduplicated alerts.
        active_alerts = [
            alert
            for identifier, alert in alerts_by_id.items()
            if identifier not in ids_to_remove
        ]
        # --- End of new deduplication logic ---

        if not active_alerts:
            return self._get_default_state()

        # Filter for relevant alert categories
        allowed_categories = {
            Category.GEO, Category.MET, Category.SAFETY, Category.SECURITY,
            Category.RESCUE, Category.FIRE, Category.ENV, Category.TRANSPORT,
            Category.INFRA, Category.HEALTH
        }

        # Use `active_alerts` instead of `all_alerts`
        filtered_alerts = [
            alert for alert in active_alerts
            if alert.info and any(cat in allowed_categories for cat in alert.info[0].category)
        ]

        now = dt_util.utcnow()
        fourteen_days_ago = now - timedelta(days=10)
        processed_alerts = []
        for alert in filtered_alerts:
            # Prefer English language info, fall back to the first available
            info = next((i for i in alert.info if i.language and i.language.lower().startswith("en")),
                        alert.info[0])

            # Filter out expired alerts
            if info.expires and info.expires < now:
                _LOGGER.debug(f"Filtering expired alert: {alert.identifier}")
                continue

            # Filter out old alerts that have no expiration date (after 14 days)
            if not info.expires and alert.sent and alert.sent < fourteen_days_ago:
                _LOGGER.debug(f"Filtering old, non-expiring alert: {alert.identifier}")
                continue

            # Filter out test alerts
            is_test_alert = False
            for param in info.parameters:
                if param.valueName == "urn:oasis:names:tc:emergency:cap:1.2:profile:cap-lu:1.0:cb-eu-level" and param.value in TEST_ALERT_LEVELS:
                    is_test_alert = True
                    break
            if is_test_alert:
                _LOGGER.debug(f"Filtering test alert: {alert.identifier}")
                continue

            severity_enum = self._get_severity(info)
            alert_severity_str = severity_enum.value if severity_enum else Severity.UNKNOWN.value
            alert_severity_level = SEVERITY_ORDER.get(alert_severity_str, 0)

            # Filter based on the user's configuration for minimum severity
            if alert_severity_level >= self.min_severity_level:
                processed_alerts.append({
                    "identifier": alert.identifier or "Not Provided",
                    "headline": info.headline or "Not Provided",
                    "description": info.description or "Not Provided",
                    "instruction": info.instruction or "Not Provided",
                    "severity_level": alert_severity_level,
                    "severity": alert_severity_str,
                    "status": alert.status.value if alert.status else "Not Provided",
                    "msgType": alert.msgType.value if alert.msgType else "Not Provided",
                    "event": info.event or "Not Provided",
                    "senderName": info.senderName or "Not Provided",
                    "certainty": info.certainty.value if info.certainty else "Not Provided",
                    "urgency": info.urgency.value if info.urgency else "Not Provided",
                    "sent": alert.sent.isoformat() if alert.sent else "Not Provided",
                    "sent_time": alert.sent or datetime.min,
                    "expires": info.expires.isoformat() if info.expires else "Not Provided",
                    "web": info.web or "Not Provided",
                    "language": info.language or "Not Provided",
                    "category": [c.value for c in info.category if c] or ["Not Provided"],
                    "effective": info.effective.isoformat() if info.effective else "Not Provided",
                    "area": [
                        {
                            "areaDesc": a.areaDesc,
                            "polygon": a.polygon,
                            "circle": a.circle,
                            "geocode": a.geocode,
                        }
                        for a in info.area
                    ] or ["Not Provided"],
                    "sender": alert.sender or "Not Provided",
                    "scope": alert.scope.value if alert.scope else "Not Provided",
                    "code": [c.value for c in alert.code if c] or ["Not Provided"],
                    "note": alert.note or "Not Provided",
                    "references": alert.references or "Not Provided",
                    "structured_description": info.structured_description or {},
                })

        # Sort alerts by severity (desc) and then by sent time (desc)
        processed_alerts.sort(key=lambda x: (x["severity_level"], x["sent_time"]), reverse=True)

        # --- New: Location Filtering ---
        location_filter_enabled = self.config_entry.options.get(
            CONF_ENABLE_LOCATION_FILTER, DEFAULT_ENABLE_LOCATION_FILTER
        )
        if location_filter_enabled:
            user_lat = self.config_entry.options.get(CONF_LATITUDE, self.hass.config.latitude)
            user_lon = self.config_entry.options.get(CONF_LONGITUDE, self.hass.config.longitude)

            if user_lat is not None and user_lon is not None:
                for alert in processed_alerts:
                    # An alert is local if the user's point is in any of its polygons
                    polygons = [
                        area["polygon"]
                        for area in alert.get("area", [])
                        if area and area.get("polygon")
                    ]
                    alert["is_local"] = is_point_in_polygons(user_lat, user_lon, polygons)
            else:
                # If location isn't configured, mark all as not local
                 for alert in processed_alerts:
                    alert["is_local"] = False
        else:
            # If the filter is disabled, mark all as not local
            for alert in processed_alerts:
                alert["is_local"] = False
        # --- End Location Filtering ---

        # --- New: Allergen Matching ---
        user_allergens = {
            allergen.lower()
            for allergen in self.config_entry.options.get(CONF_ALLERGENS, DEFAULT_ALLERGENS)
        }
        if user_allergens:
            for alert in processed_alerts:
                alert["allergen_match"] = False
                # Combine all text fields where an allergen could be mentioned
                search_text = (
                    (alert.get("headline", "") or "")
                    + " "
                    + (alert.get("description", "") or "")
                    + " "
                    + (alert.get("event", "") or "")
                ).lower()

                if any(allergen in search_text for allergen in user_allergens):
                    alert["allergen_match"] = True
        else:
            for alert in processed_alerts:
                alert["allergen_match"] = False
        # --- End Allergen Matching ---


        # Count alerts by severity
        severity_counts = {
            "extreme": 0,
            "severe": 0,
            "moderate": 0,
            "minor": 0,
            "information": 0,
            "unknown": 0,
            "test": 0,
        }
        for alert in processed_alerts:
            severity_key = alert["severity"].lower()
            if severity_key in severity_counts:
                severity_counts[severity_key] += 1

        # Determine highest severity alert
        highest_severity_alert = None
        if processed_alerts:
            highest_severity_alert = processed_alerts[0]

        return {
            "count": len(processed_alerts),
            "alerts": processed_alerts,
            "severity_counts": severity_counts,
            "highest_severity_alert": highest_severity_alert,
        }

    def _get_severity(self, info: Info) -> Severity:
        """Determine the severity of an alert, prioritizing the parameter code."""
        # First, try to find the specific LU-Alert level parameter, as it's the most reliable.
        # Note: The official CAP-LU documentation specifies "cb-lu-level",
        # but the actual XML feed uses "urn:oasis:names:tc:emergency:cap:1.2:profile:cap-lu:1.0:cb-eu-level".
        for param in info.parameters:
            if param.valueName == "urn:oasis:names:tc:emergency:cap:1.2:profile:cap-lu:1.0:cb-eu-level":
                severity = LEVEL_TO_SEVERITY.get(param.value)
                if severity:
                    return severity

        # If no specific parameter is found, fall back to the direct severity field.
        if info.severity:
            return info.severity

        return Severity.UNKNOWN

    async def _get_all_alert_urls(self) -> list[str]:
        """Get the URLs of all alert XMLs from the dataset API."""
        urls = []
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(DATASET_API_URL) as response:
                        response.raise_for_status()
                        data = await response.json()
                        if data and "resources" in data:
                            # Process all available XML resources
                            for resource in data["resources"]:
                                if resource.get("format", "").lower() == "xml":
                                    url = resource.get("url")
                                    if url:
                                        urls.append(url)
            return urls
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Failed to get alert URLs: %s", err)
            return []

    async def _fetch_xml_content(self, url: str) -> str | None:
        """Fetch the raw XML content from a given URL."""
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Failed to fetch XML content from %s: %s", url, err)
            return None

    def _get_default_state(self) -> dict:
        """Return a dictionary representing a clear/default state."""
        return {
            "count": 0,
            "alerts": [],
            "severity_counts": {
                "extreme": 0,
                "severe": 0,
                "moderate": 0,
                "minor": 0,
                "information": 0,
                "unknown": 0,
                "test": 0,
            },
            "highest_severity_alert": None,
        }
