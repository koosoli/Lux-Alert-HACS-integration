"""DataUpdateCoordinator for the LU-Alert integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MIN_SEVERITY,
    DATASET_API_URL,
    DEFAULT_MIN_SEVERITY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .enums import Category, MsgType, Severity
from .models import Alert, Info
from .parser import parse_xml

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
    "ALERT_LVL_3": Severity.MODERATE,
    # Minor
    "N3": Severity.MINOR,
    "L3": Severity.MINOR,
    "LU-Alert Level 3": Severity.MINOR,
    # Information
    "I": Severity.INFORMATION,
    "LU-Alert Level 4": Severity.INFORMATION,
    "ALERT_LVL_4": Severity.INFORMATION,
    # Test
    "T": Severity.TEST,
    "LU-Alert Test": Severity.TEST,
    "LU-Alert Exercise": Severity.TEST,
    "ALERT_LVL_5": Severity.TEST,
}

# Set of alert levels that should be considered as "Test" and filtered out
TEST_ALERT_LEVELS = {"T", "D", "LU-Alert Test", "LU-Alert Exercise", "ALERT_LVL_5"}


def _parse_references(references_str: str | None) -> list[str]:
    """Parse the references string into a list of alert identifiers."""
    if not references_str:
        return []

    identifiers = []
    # The string is space-separated, and each part is comma-separated.
    parts = references_str.strip().split()
    for part in parts:
        # Each part is like "sender,identifier,sent_time"
        sub_parts = part.split(",")
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
        self._fetch_semaphore = asyncio.Semaphore(10)

    @property
    def min_severity_level(self) -> int:
        """Get the minimum severity level from config options or data."""
        # Prioritize options, but fall back to data for initial setup
        severity_str = self.config_entry.options.get(
            CONF_MIN_SEVERITY
        ) or self.config_entry.data.get(CONF_MIN_SEVERITY, DEFAULT_MIN_SEVERITY)
        return SEVERITY_ORDER.get(severity_str, 0)

    @property
    def language(self) -> str | None:
        """Get the preferred language from config options."""
        return self.config_entry.options.get("language")

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch, process, and filter data from the LU-Alert feed."""
        session = async_get_clientsession(self.hass)
        xml_urls = await self._get_all_alert_urls(session)
        if not xml_urls:
            _LOGGER.info("No alert XML URLs found.")
            return self._get_default_state()

        _LOGGER.debug("Fetching %d XML alert files...", len(xml_urls))

        # Concurrently fetch XML files using a semaphore to limit concurrency
        fetch_tasks = [self._fetch_xml_content(session, url) for url in xml_urls]
        all_xml_contents = await asyncio.gather(*fetch_tasks)

        all_alerts: list[Alert] = []
        for i, xml_content in enumerate(all_xml_contents):
            if not xml_content:
                continue

            try:
                # Use hass.async_add_executor_job for the CPU-bound parsing
                alerts_from_file = await self.hass.async_add_executor_job(
                    parse_xml, xml_content
                )
                all_alerts.extend(alerts_from_file)
            except Exception as err:
                _LOGGER.warning("Failed to parse alert XML from %s: %s", xml_urls[i], err)

        if not all_alerts:
            _LOGGER.debug("No alerts found in any fetched XML files.")
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
            if alert.msgType == MsgType.CANCEL:
                ids_to_remove.add(alert.identifier)

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

        if not active_alerts:
            _LOGGER.debug("All found alerts were either canceled or superseded.")
            return self._get_default_state()

        # Filter for relevant alert categories
        allowed_categories = {
            Category.GEO,
            Category.MET,
            Category.SAFETY,
            Category.SECURITY,
            Category.RESCUE,
            Category.FIRE,
            Category.ENV,
            Category.TRANSPORT,
            Category.INFRA,
            Category.HEALTH,
        }

        now = dt_util.utcnow()
        old_alert_threshold = now - timedelta(days=14)
        processed_alerts = []

        # Reference for sorting (must be aware)
        min_sent_time = datetime.min.replace(tzinfo=timezone.utc)

        for alert in active_alerts:
            # Filter for categories
            if not alert.info or not any(
                cat in allowed_categories for cat in alert.info[0].category
            ):
                continue

            # Prefer preferred language if set, then English, then first available
            info = alert.info[0]
            if self.language:
                info = next(
                    (i for i in alert.info if i.language and self.language in i.language),
                    info,
                )
            else:
                info = next(
                    (
                        i
                        for i in alert.info
                        if i.language and i.language.lower().startswith("en")
                    ),
                    info,
                )

            # Filter out expired alerts
            if info.expires and info.expires < now:
                continue

            # Filter out old alerts that have no expiration date (after 14 days)
            if not info.expires and alert.sent and alert.sent < old_alert_threshold:
                continue

            # Filter out test alerts based on parameters
            is_test_alert = False
            for param in info.parameters:
                if (
                    param.valueName
                    in (
                        "urn:oasis:names:tc:emergency:cap:1.2:profile:cap-lu:1.0:cb-eu-level",
                        "cb-lu-level",
                        "cb-eu-level",
                    )
                    and param.value in TEST_ALERT_LEVELS
                ):
                    is_test_alert = True
                    break
            if is_test_alert:
                continue

            severity_enum = self._get_severity(info)
            alert_severity_str = (
                severity_enum.value if severity_enum else Severity.UNKNOWN.value
            )
            alert_severity_level = SEVERITY_ORDER.get(alert_severity_str, 0)

            # Filter based on the user's configuration for minimum severity
            if alert_severity_level >= self.min_severity_level:
                processed_alerts.append(
                    {
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
                        "sent_time": alert.sent or min_sent_time,
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
                    }
                )

        # Sort alerts by severity (desc) and then by sent time (desc)
        processed_alerts.sort(
            key=lambda x: (x["severity_level"], x["sent_time"]), reverse=True
        )

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

        _LOGGER.debug("Found %d active and relevant alerts.", len(processed_alerts))

        return {
            "count": len(processed_alerts),
            "alerts": processed_alerts,
            "severity_counts": severity_counts,
            "highest_severity_alert": processed_alerts[0] if processed_alerts else None,
        }

    def _get_severity(self, info: Info) -> Severity:
        """Determine the severity of an alert, prioritizing the parameter code."""
        for param in info.parameters:
            if param.valueName in (
                "urn:oasis:names:tc:emergency:cap:1.2:profile:cap-lu:1.0:cb-eu-level",
                "cb-lu-level",
                "cb-eu-level",
            ):
                severity = LEVEL_TO_SEVERITY.get(param.value)
                if severity:
                    return severity

        return info.severity or Severity.UNKNOWN

    async def _get_all_alert_urls(self, session: aiohttp.ClientSession) -> list[str]:
        """Get the URLs of the most recent alert XMLs from the dataset API."""
        try:
            async with async_timeout.timeout(15):
                async with session.get(DATASET_API_URL) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data and "resources" in data:
                        xml_resources = [
                            res
                            for res in data["resources"]
                            if res.get("format", "").lower() == "xml"
                        ]
                        # Limiting to 100 resources covers all recent active alerts
                        return [res.get("url") for res in xml_resources[:100] if res.get("url")]
            return []
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Failed to get alert URLs from %s: %s", DATASET_API_URL, err)
            raise UpdateFailed(f"Failed to get alert URLs: {err}") from err

    async def _fetch_xml_content(
        self, session: aiohttp.ClientSession, url: str
    ) -> str | None:
        """Fetch the raw XML content from a given URL with concurrency control."""
        async with self._fetch_semaphore:
            try:
                async with async_timeout.timeout(10):
                    async with session.get(url) as response:
                        response.raise_for_status()
                        return await response.text()
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.debug("Failed to fetch XML content from %s: %s", url, err)
                return None

    def _get_default_state(self) -> dict[str, Any]:
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
