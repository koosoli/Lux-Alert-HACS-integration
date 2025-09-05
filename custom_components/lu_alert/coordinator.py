"""DataUpdateCoordinator for the LU-Alert integration."""
from __future__ import annotations

import logging
from datetime import timedelta
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
from .enums import Severity

_LOGGER = logging.getLogger(__name__)

# Define the order of severity for filtering. Higher number is more severe.
SEVERITY_ORDER = {
    Severity.UNKNOWN.value: 0,
    Severity.MINOR.value: 1,
    Severity.MODERATE.value: 2,
    Severity.SEVERE.value: 3,
    Severity.EXTREME.value: 4,
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
        xml_url = await self._get_latest_alert_url()
        if not xml_url:
            raise UpdateFailed("Could not get latest alert XML URL from API.")

        xml_content = await self._fetch_xml_content(xml_url)
        if not xml_content:
            return self._get_default_state()

        try:
            all_alerts = await self.hass.async_add_executor_job(parse_xml, xml_content)
        except Exception as err:
            raise UpdateFailed(f"Failed to parse alert XML: {err}") from err

        filtered_alerts = []
        for alert in all_alerts:
            if not alert.info:
                continue

            # Get the severity level of the alert's first info block
            # Default to 0 if severity is not set.
            alert_severity_str = alert.info[0].severity.value if alert.info[0].severity else Severity.UNKNOWN.value
            alert_severity_level = SEVERITY_ORDER.get(alert_severity_str, 0)

            # Filter based on the user's configuration
            if alert_severity_level >= self.min_severity_level:
                # Find the English info block, otherwise fall back to the first one.
                info = next((i for i in alert.info if i.language and i.language.lower().startswith("en")), alert.info[0])

                filtered_alerts.append({
                    "status": alert.status.value if alert.status else "Not Provided",
                    "msgType": alert.msgType.value if alert.msgType else "Not Provided",
                    "event": info.event or "Not Provided",
                    "headline": info.headline or "Not Provided",
                    "description": info.description or "Not Provided",
                    "instruction": info.instruction or "Not Provided",
                    "senderName": info.senderName or "Not Provided",
                    "certainty": info.certainty.value if info.certainty else "Not Provided",
                    "severity": info.severity.value if info.severity else "Not Provided",
                    "urgency": info.urgency.value if info.urgency else "Not Provided",
                    "sent": alert.sent.isoformat() if alert.sent else "Not Provided",
                    "expires": info.expires.isoformat() if info.expires else "Not Provided",
                    "web": info.web or "Not Provided",
                    "identifier": alert.identifier or "Not Provided",
                })

        return {
            "count": len(filtered_alerts),
            "alerts": filtered_alerts,
        }

    async def _get_latest_alert_url(self) -> str | None:
        """Get the URL of the latest alert XML from the dataset API."""
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(DATASET_API_URL) as response:
                        response.raise_for_status()
                        data = await response.json()
                        if data and "resources" in data:
                            for resource in data["resources"]:
                                if resource.get("format", "").lower() == "xml":
                                    return resource.get("url")
            return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Failed to get latest alert URL: %s", err)
            return None

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
        return {"count": 0, "alerts": []}
