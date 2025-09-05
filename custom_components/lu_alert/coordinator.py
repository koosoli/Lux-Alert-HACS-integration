"""DataUpdateCoordinator for the LU-Alert integration."""
from __future__ import annotations

import logging
from datetime import timedelta
import asyncio

import async_timeout
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DATASET_API_URL, DOMAIN, DEFAULT_SCAN_INTERVAL
from .cap_lu.parser import parse_xml

_LOGGER = logging.getLogger(__name__)


class LuAlertDataUpdateCoordinator(DataUpdateCoordinator):
    """A coordinator to fetch and parse LU-Alert data."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        """Fetch and process data from the LU-Alert API and XML feed."""

        xml_url = await self._get_latest_alert_url()

        if not xml_url:
            # If we can't get the XML URL, something is wrong with the main API.
            raise UpdateFailed("Could not retrieve the latest alert XML URL from the dataset API.")

        xml_content = await self._fetch_xml_content(xml_url)

        if not xml_content:
            # This can happen if the XML file is empty or unreachable.
            # We return a default "clear" state.
            return self._get_default_state()

        try:
            alert = await self.hass.async_add_executor_job(parse_xml, xml_content)
        except Exception as err:
            raise UpdateFailed(f"Failed to parse alert XML: {err}") from err

        if alert and alert.info:
            # Find the English info block, otherwise fall back to the first one.
            info = next((i for i in alert.info if i.language and i.language.lower().startswith("en")), alert.info[0])

            return {
                "status": alert.status.value if alert.status else "N/A",
                "msgType": alert.msgType.value if alert.msgType else "N/A",
                "event": info.event,
                "headline": info.headline,
                "description": info.description,
                "instruction": info.instruction,
                "senderName": info.senderName,
                "certainty": info.certainty.value if info.certainty else "N/A",
                "severity": info.severity.value if info.severity else "N/A",
                "urgency": info.urgency.value if info.urgency else "N/A",
                "sent": alert.sent.isoformat() if alert.sent else "N/A",
                "expires": info.expires.isoformat() if info.expires else "N/A",
                "web": info.web,
                "identifier": alert.identifier,
            }

        # If parsing succeeds but there's no alert or no info block, return a clear state.
        return self._get_default_state()

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
        return {
            "status": "OK",
            "headline": "No active alert",
            "event": "No active alert",
            # Fill with default values for all other fields
            "msgType": "N/A",
            "description": "No active alert is currently issued.",
            "instruction": "N/A",
            "senderName": "N/A",
            "certainty": "N/A",
            "severity": "N/A",
            "urgency": "N/A",
            "sent": "N/A",
            "expires": "N/A",
            "web": "N/A",
            "identifier": "N/A",
        }
