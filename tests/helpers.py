"""Helpers for the integration tests: a fake data.public.lu on the aiohttp client mock, and a loaded config entry."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from cap_samples import cap_xml
from custom_components.lu_alert.const import DATASET_URL, DOMAIN

FILES = "https://data.public.lu/f"


def now() -> datetime:
    return datetime.now(timezone.utc)


def times(**kw):
    """sent five minutes ago, ends in two hours: an alert in force now (override with sent= / expires=)."""
    return dict({"sent": now() - timedelta(minutes=5), "expires": now() + timedelta(hours=2)}, **kw)


def mock_feed(mocker: AiohttpClientMocker, documents: list[str], dataset_status: int = 200) -> None:
    """The dataset lists one XML file per document, newest first (the stamp of file i is later than i-1)."""
    mocker.clear_requests()
    if dataset_status != 200:
        mocker.get(DATASET_URL, status=dataset_status)
        return
    resources = []
    for i, document in enumerate(documents):
        url = f"{FILES}/{i}.xml"
        resources.append({"format": "xml", "url": url, "last_modified": f"2026-11-01T10:{i % 60:02d}:00",
                          "checksum": {"type": "sha1", "value": f"c{i}"}, "title": f"file {i}"})
        mocker.get(url, text=document)
    mocker.get(DATASET_URL, json={"resources": resources})


def alert(identifier: str, **kw) -> str:
    return cap_xml(identifier, **times(**kw))


async def setup_entry(hass: HomeAssistant, options: dict | None = None, data: dict | None = None) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=data or {"min_severity": "unknown"}, options=options or {},
                            unique_id=DOMAIN)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
