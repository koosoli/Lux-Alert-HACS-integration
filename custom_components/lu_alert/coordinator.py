"""DataUpdateCoordinator for the LU-Alert integration: polls the feed, applies the rules, keeps the last known alerts.

Error policy (the one of the Domoticz-LUAlert plugin):

    * a failed poll NEVER clears the alerts: the entities keep showing the last known alerts, they still end when their
      end time passes, and the "Feed connection" binary sensor turns off, so an outage is not mistaken for "all clear"
    * the very first poll has nothing to fall back on: it fails, and Home Assistant retries the setup
    * every problem is logged ONCE as a warning, repeats go to the debug log, and the recovery is logged once
    * after a failed poll the next attempt waits longer (backoff, capped)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .alerts import Filters, build_snapshot
from .api import ApiError, Client
from .const import (
    CONF_ALLERGENS, CONF_LANGUAGE, CONF_LOCATION_MODE, CONF_MIN_SEVERITY, CONF_SHOW_TEST, CONF_WATCHLIST_KEYWORDS,
    DATASET_URL, DEFAULT_LANGUAGE, DEFAULT_LOCATION_MODE, DEFAULT_MAX_RESOURCES, DEFAULT_MIN_SEVERITY,
    DEFAULT_SCAN_INTERVAL, DEFAULT_STALE_DAYS, DOMAIN, LANGUAGES, LOCATION_MODE_VALUES, MAX_BACKOFF, SEVERITY_RANK,
    UNKNOWN,
)
from .feed import Feed, FeedResult
from .model import CapAlert, Snapshot
from .util import split_list

_LOGGER = logging.getLogger(__name__)


@dataclass
class LuAlertData:
    """What the entities show."""

    snapshot: Snapshot
    feed_ok: bool = True                    # the last poll worked
    last_success: datetime | None = None
    last_error: str | None = None
    listed: int = 0                         # alert files the dataset lists (within the limit)
    fetched: int = 0                        # downloaded in the last poll
    failed: int = 0                         # files that could not be read in the last poll
    unreadable: int = 0                     # files that are not valid CAP
    errors: list[str] = field(default_factory=list)


def filters_from_entry(hass: HomeAssistant, entry: ConfigEntry) -> Filters:
    """The filter rules of the options (and the data of the first setup). The location never goes into a log."""
    config = {**entry.data, **entry.options}
    language = str(config.get(CONF_LANGUAGE) or DEFAULT_LANGUAGE).lower()
    location = None
    mode = LOCATION_MODE_VALUES.get(config.get(CONF_LOCATION_MODE, DEFAULT_LOCATION_MODE), 0)
    if mode:
        lat, lon = config.get(CONF_LATITUDE), config.get(CONF_LONGITUDE)
        location = (float(lat), float(lon)) if lat is not None and lon is not None else (
            hass.config.latitude, hass.config.longitude)
    return Filters(
        min_rank=SEVERITY_RANK.get(str(config.get(CONF_MIN_SEVERITY, DEFAULT_MIN_SEVERITY)).capitalize(), SEVERITY_RANK[UNKNOWN]),
        language=language if language in LANGUAGES else DEFAULT_LANGUAGE,
        show_test=bool(config.get(CONF_SHOW_TEST, False)),
        stale_days=DEFAULT_STALE_DAYS,
        location_mode=mode,
        location=location,
        keywords=tuple(k.lower() for k in split_list(config.get(CONF_WATCHLIST_KEYWORDS))),
        allergens=tuple(a.lower() for a in (config.get(CONF_ALLERGENS) or []) if str(a).strip()),
    )


class LuAlertCoordinator(DataUpdateCoordinator[LuAlertData]):
    """Fetch, parse and filter the LU-Alert feed."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: Client | None = None) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN,
                         update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL))
        self._client = client or Client(async_get_clientsession(hass), DATASET_URL)
        self._feed = Feed(self._client, DEFAULT_MAX_RESOURCES, executor=hass.async_add_executor_job)
        self.filters = filters_from_entry(hass, entry)
        self._cap_alerts: list[CapAlert] = []
        self._failures = 0
        self._problems: set[str] = set()                # problems the log already told about
        self._tests_told: set[str] = set()              # identifiers of test messages the log already named
        self._levels_told: set[str] = set()             # level codes the log already called unknown
        self._unsub_expiry: CALLBACK_TYPE | None = None

    # -- life cycle -----------------------------------------------------------------------------------------
    async def async_shutdown(self) -> None:
        self._cancel_expiry()
        await super().async_shutdown()

    # -- polling --------------------------------------------------------------------------------------------
    async def _async_update_data(self) -> LuAlertData:
        try:
            result = await self._feed.refresh()
        except ApiError as exc:
            return self._poll_failed(exc)
        return self._poll_worked(result)

    def _poll_worked(self, result: FeedResult) -> LuAlertData:
        self._failures = 0
        self.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
        if self._recovered("feed"):
            _LOGGER.info("The LU-Alert feed answers again")
        self._cap_alerts = result.cap_alerts
        snapshot = self._build()

        if result.failed:
            self._report("files", "Could not read %d of %d alert files (%s): the alerts shown may be incomplete, the "
                         "next poll tries again" % (result.failed, result.listed, _short(result.errors)))
        elif self._recovered("files"):
            _LOGGER.info("All alert files can be read again")
        if result.unreadable:
            self._report("unreadable", "%d alert file(s) are not valid CAP or too large and are ignored (%s)"
                         % (result.unreadable, _short(result.errors)))
        elif self._recovered("unreadable"):
            _LOGGER.info("No alert file is unreadable any more")

        return LuAlertData(snapshot, True, dt_util.utcnow(), None, result.listed, result.fetched, result.failed,
                           result.unreadable, result.errors)

    def _poll_failed(self, exc: ApiError) -> LuAlertData:
        self._failures += 1
        interval = DEFAULT_SCAN_INTERVAL
        delay = max(interval, min(interval * 2 ** min(self._failures - 1, 6), MAX_BACKOFF))
        if self.data is None:
            # the first poll: there are no last known alerts to show, so Home Assistant retries the setup
            raise UpdateFailed("LU-Alert feed poll failed: %s" % exc) from exc
        self.update_interval = timedelta(seconds=delay)
        self._report("feed", "LU-Alert feed poll failed: %s. The entities keep the last known alerts, the next "
                     "attempt is in %d s" % (exc, delay))
        return replace(self.data, snapshot=self._build(), feed_ok=False, last_error=str(exc), fetched=0)

    # -- the rules ------------------------------------------------------------------------------------------
    def _build(self) -> Snapshot:
        """Apply the rules to the messages read so far, now. Also the place that plans the next expiry."""
        snapshot = build_snapshot(self._cap_alerts, dt_util.utcnow(), self.filters)
        for identifier, level, headline in snapshot.ignored_tests:
            if identifier not in self._tests_told:
                self._tests_told.add(identifier)
                _LOGGER.info("Test message ignored (%s): %s", level, headline)
        for level in snapshot.unknown_levels:
            if level not in self._levels_told:
                self._levels_told.add(level)
                _LOGGER.warning("Unknown LU-Alert level '%s': the CAP severity of the message is used. The level table "
                                "may need a new entry", level)
        if snapshot.dropped:
            _LOGGER.debug("Left out: %s", ", ".join("%s %d" % (k, v) for k, v in sorted(snapshot.dropped.items())))
        self._schedule_expiry(snapshot.next_expiry)
        return snapshot

    # -- alerts end on time, also between polls --------------------------------------------------------------
    def _cancel_expiry(self) -> None:
        if self._unsub_expiry is not None:
            self._unsub_expiry()
            self._unsub_expiry = None

    def _schedule_expiry(self, moment: datetime | None) -> None:
        self._cancel_expiry()
        if moment is None or self._shutdown_requested:
            return
        self._unsub_expiry = async_track_point_in_utc_time(
            self.hass, self._handle_expiry, dt_util.as_utc(moment) + timedelta(seconds=1))

    @callback
    def _handle_expiry(self, _now: datetime) -> None:
        """An alert has ended: show the alerts that are left, without polling (and without moving the next poll)."""
        self._unsub_expiry = None
        if self.data is None:
            return
        self.data = replace(self.data, snapshot=self._build())
        self.async_update_listeners()

    # -- log once -------------------------------------------------------------------------------------------
    def _report(self, key: str, text: str) -> None:
        if key in self._problems:
            _LOGGER.debug(text)
        else:
            self._problems.add(key)
            _LOGGER.warning(text)

    def _recovered(self, key: str) -> bool:
        if key in self._problems:
            self._problems.discard(key)
            return True
        return False


def _short(errors: list[str], limit: int = 150) -> str:
    text = errors[0] if errors else "see the debug log"
    return text if len(text) <= limit else text[: limit - 3] + "..."
