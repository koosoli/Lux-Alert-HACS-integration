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

from .const import (
    DATASET_API_URL,
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CONF_MIN_SEVERITY,
    DEFAULT_MIN_SEVERITY,
)
from .parser import parse_xml
from .enums import Severity, Category
from .models import Info

_LOGGER = logging.getLogger(__name__)

# Define the order of severity for filtering. Higher number is more severe.
SEVERITY_ORDER = {
    Severity.UNKNOWN.value: 0,
    Severity.MINOR.value: 1,
    Severity.MODERATE.value: 2,
    Severity.SEVERE.value: 3,
    Severity.EXTREME.value: 4,
}

# Mapping from cb-lu-level parameter to Severity enum
LEVEL_TO_SEVERITY = {
    "ALERT_LVL_1": Severity.MINOR,
    "ALERT_LVL_2": Severity.SEVERE,
    "LU-Alert Amber": Severity.MODERATE,
    "ALERT_LVL_3": Severity.MODERATE,
    "ALERT_LVL_4": Severity.EXTREME,
}


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
        """Get the minimum severity level from config options."""
        severity_str = self.config_entry.options.get(
            CONF_MIN_SEVERITY, DEFAULT_MIN_SEVERITY
        )
        return SEVERITY_ORDER.get(severity_str, 0)

    async def _async_update_data(self) -> dict:
        """Fetch, process, and filter data from the LU-Alert feed."""
        xml_urls = await self._get_all_alert_urls()
        if not xml_urls:
            _LOGGER.info("No alert XML URLs found.")
            return self._get_default_state()

        all_alerts = []
        for xml_url in xml_urls:
            xml_content = await self._fetch_xml_content(xml_url)
            if not xml_content:
                continue

            try:
                alerts_from_file = await self.hass.async_add_executor_job(parse_xml, xml_content)
                all_alerts.extend(alerts_from_file)
            except Exception as err:
                _LOGGER.warning(f"Failed to parse alert XML from {xml_url}: {err}")

        if not all_alerts:
            return self._get_default_state()

        # Filter for relevant alert categories
        allowed_categories = {
            Category.GEO, Category.MET, Category.SAFETY, Category.SECURITY,
            Category.RESCUE, Category.FIRE, Category.ENV, Category.TRANSPORT,
            Category.INFRA
        }

        filtered_alerts = [
            alert for alert in all_alerts
            if alert.info and any(cat in allowed_categories for cat in alert.info[0].category)
        ]

        processed_alerts = []
        for alert in filtered_alerts:
            severity_enum = self._get_severity(alert.info[0])
            alert_severity_str = severity_enum.value if severity_enum else Severity.UNKNOWN.value
            alert_severity_level = SEVERITY_ORDER.get(alert_severity_str, 0)

            # Filter based on the user's configuration
            if alert_severity_level >= self.min_severity_level:
                info = next((i for i in alert.info if i.language and i.language.lower().startswith("fr")), alert.info[0])

                processed_alerts.append({
                    "severity_level": alert_severity_level,
                    "sent_time": alert.sent or datetime.min,
                    "status": alert.status.value if alert.status else "Not Provided",
                    "msgType": alert.msgType.value if alert.msgType else "Not Provided",
                    "event": info.event or "Not Provided",
                    "headline": info.headline or "Not Provided",
                    "description": info.description or "Not Provided",
                    "instruction": info.instruction or "Not Provided",
                    "senderName": info.senderName or "Not Provided",
                    "certainty": info.certainty.value if info.certainty else "Not Provided",
                    "severity": alert_severity_str,
                    "urgency": info.urgency.value if info.urgency else "Not Provided",
                    "sent": alert.sent.isoformat() if alert.sent else "Not Provided",
                    "expires": info.expires.isoformat() if info.expires else "Not Provided",
                    "web": info.web or "Not Provided",
                    "identifier": alert.identifier or "Not Provided",
                })

        # Sort alerts by severity (desc) and then by sent time (desc)
        processed_alerts.sort(key=lambda x: (x["severity_level"], x["sent_time"]), reverse=True)

        primary_headline = "No active alerts"
        if processed_alerts:
            primary_headline = processed_alerts[0]["headline"]

        return {
            "headline": primary_headline,
            "count": len(processed_alerts),
            "alerts": processed_alerts,
        }

    def _get_severity(self, info: Info) -> Severity:
        """Determine the severity of an alert, checking parameters as a fallback."""
        # First, try the direct severity field
        if info.severity and info.severity != Severity.UNKNOWN:
            return info.severity

        # If it's unknown, try to find it in the parameters.
        # Note: The official CAP-LU documentation specifies "cb-lu-level",
        # but the actual XML feed uses "cb-eu-level".
        for param in info.parameters:
            if param.valueName and "cb-eu-level" in param.valueName.lower():
                return LEVEL_TO_SEVERITY.get(param.value, Severity.UNKNOWN)

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
                            # Only process the most recent 20 files to avoid performance issues
                            for resource in data["resources"][:20]:
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
        return {"headline": "No active alerts", "count": 0, "alerts": []}
