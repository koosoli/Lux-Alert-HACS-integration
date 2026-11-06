"""From CAP messages to the alerts that are in force now. Pure functions: no I/O, no Home Assistant, no clock of its own.

This is the part that decides what a person sees. It is the logic of the Domoticz-LUAlert plugin
(https://github.com/janreimen/Domoticz-LUAlert), whose tests it shares. The rules:

  1. A reply (Ack, Error) is not an alert. Of several messages with one identifier the newest counts.
  2. A Cancel message ends the alert it references, and an Update replaces the alert it references: the referenced
     message (sender, identifier, sent) is dropped, the Cancel itself is never shown.
  3. An alert ends when its LATEST end time (over all language and channel blocks) has passed. One without any end
     time is shown for ``stale_days`` days after it was sent.
  4. Test, Exercise, System and Draft messages and the test levels are left out, unless tests are asked for. A
     test that is left out is named once in the log, so a real alert that is wrongly taken for a test is not silent.
  5. The severity comes from the LU-Alert level of the message (N1, N2, ... see const.LEVEL_TO_SEVERITY), and
     only without one from the CAP severity field. Nothing is dropped because of its category unless the user
     listed that category.
  6. Messages with the same text and the same end (the portal sometimes publishes a recall again under a new number)
     are shown once, the newest.
  7. The text is taken from the block in the preferred language and, among those, from the fullest channel
     (app, website) rather than the siren or SMS block.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple

from . import geo
from .cap import parse_time
from .const import (
    CHANNEL_LAST, CHANNEL_ORDER, CHANNEL_PARAMETER, DEFAULT_STALE_DAYS, DEFAULT_TEST_LEVELS, LEVEL_PARAMETERS,
    LEVEL_TO_SEVERITY, LOCATION_ONLY, MSG_NO_ALERT, REAL_STATUS, SEVERITIES, SEVERITY_RANK, TEST, UNKNOWN,
)
from .model import ActiveAlert, Area, CapAlert, Info, Snapshot

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_CAP_SEVERITY = {s.lower(): s for s in SEVERITIES}


class Filters(NamedTuple):
    min_rank: int = SEVERITY_RANK[UNKNOWN]
    language: str = "en"
    show_test: bool = False
    test_levels: Tuple[str, ...] = tuple(level.lower() for level in DEFAULT_TEST_LEVELS)
    ignore_categories: Tuple[str, ...] = ()                                          # lower case
    stale_days: int = DEFAULT_STALE_DAYS
    location_mode: int = 0
    location: Optional[Tuple[float, float]] = None
    keywords: Tuple[str, ...] = ()                                                   # lower case
    allergens: Tuple[str, ...] = ()                                                  # lower case


# -- helpers --------------------------------------------------------------------------------------------------
def _sent(alert: CapAlert) -> datetime:
    return alert.sent or _EPOCH


def _latest_end(alert: CapAlert) -> Optional[datetime]:
    ends = [info.expires for info in alert.infos if info.expires is not None]
    return max(ends) if ends else None


def parse_references(text: str) -> List[Tuple[str, Optional[datetime]]]:
    """'sender,identifier,sent sender,identifier,sent' -> [(identifier, sent), ...]"""
    found = []
    for part in text.split():
        pieces = part.split(",")
        if len(pieces) >= 2 and pieces[1]:
            found.append((pieces[1], parse_time(",".join(pieces[2:])) if len(pieces) > 2 else None))
    return found


def _param_values(info: Info, names: Iterable[str]) -> List[str]:
    """Values of the parameters whose name (after the last ':') is one of ``names``."""
    wanted = set(names)
    return [p.value.strip() for p in info.parameters if p.name.rsplit(":", 1)[-1].strip().lower() in wanted and p.value.strip()]


def level_code(infos: Iterable[Info]) -> str:
    """The LU-Alert level: the first value that is a known level in any block, else the first value, else ''."""
    first = ""
    for info in infos:
        for value in _param_values(info, LEVEL_PARAMETERS):
            if value.lower() in LEVEL_TO_SEVERITY:
                return value
            first = first or value
    return first


def severity_of(alert: CapAlert, code: str) -> str:
    """The severity of an alert: the one of its LU-Alert level, else the highest CAP severity of its blocks."""
    mapped = LEVEL_TO_SEVERITY.get(code.lower()) if code else None
    if mapped:
        return mapped
    best = UNKNOWN
    for info in alert.infos:
        severity = _CAP_SEVERITY.get(info.severity.strip().lower(), UNKNOWN)
        if SEVERITY_RANK[severity] > SEVERITY_RANK[best]:
            best = severity
    return best


def channel_rank(info: Info) -> int:
    for value in _param_values(info, (CHANNEL_PARAMETER,)):
        name = value.lower()
        if name in CHANNEL_ORDER:
            return CHANNEL_ORDER.index(name)
        if name in CHANNEL_LAST:
            return 100 + CHANNEL_LAST.index(name)
    return 50                                                   # no channel named: after the known ones, before a siren


def choose_info(infos: Iterable[Info], language: str) -> Optional[Info]:
    """The block to show: preferred language, then English, then any; within a language the fullest channel."""
    infos = list(infos)
    if not infos:
        return None

    def language_rank(info: Info) -> int:
        tag = info.language.lower()
        if tag.startswith(language):
            return 0
        return 1 if tag.startswith("en") else 2

    return min(infos, key=lambda i: (language_rank(i), channel_rank(i), -len(i.headline) - len(i.description)))


def _is_test(alert: CapAlert, code: str, test_levels: Tuple[str, ...]) -> bool:
    if alert.status and alert.status.strip().lower() != REAL_STATUS:
        return True
    levels = [code.lower()] if code else []
    for info in alert.infos:
        levels.extend(v.lower() for v in _param_values(info, LEVEL_PARAMETERS))
    return any(level in test_levels for level in levels)


def _search_text(alert: CapAlert) -> str:
    return " ".join(" ".join((i.headline, i.event, i.description, i.instruction)) for i in alert.infos).lower()


def _areas(alert: CapAlert) -> Tuple[Area, ...]:
    """The distinct areas of all blocks (every language and channel repeats them)."""
    areas, seen = [], set()
    for info in alert.infos:
        for area in info.areas:
            key = (area.desc, area.polygons, area.circles)
            if key not in seen:
                seen.add(key)
                areas.append(area)
    return tuple(areas)


def _local_flag(areas: Iterable[Area], filters: Filters) -> Optional[bool]:
    if filters.location is None or not filters.location_mode:
        return None
    return geo.locate(filters.location[0], filters.location[1], areas)


# -- the main function ----------------------------------------------------------------------------------------
def build_snapshot(cap_alerts: Iterable[CapAlert], now: datetime, filters: Filters) -> Snapshot:
    dropped: Dict[str, int] = {}
    ignored_tests: List[Tuple[str, str, str]] = []
    unknown_levels: Dict[str, None] = {}                # in order of appearance

    def drop(reason: str) -> None:
        dropped[reason] = dropped.get(reason, 0) + 1

    # 1. replies are no alerts; of one identifier the newest message counts
    latest: Dict[str, CapAlert] = {}
    for alert in cap_alerts:
        if alert.msg_type.strip().lower() in MSG_NO_ALERT:
            drop("reply")
        elif not alert.identifier:
            drop("no identifier")
        elif alert.identifier not in latest or _sent(alert) > _sent(latest[alert.identifier]):
            latest[alert.identifier] = alert

    # 2. what a Cancel or an Update points at is over
    referenced: Dict[str, List[Optional[datetime]]] = {}
    for alert in latest.values():
        for identifier, sent in parse_references(alert.references):
            if identifier != alert.identifier:
                referenced.setdefault(identifier, []).append(sent)

    def replaced(alert: CapAlert) -> bool:
        return any(sent is None or sent >= _sent(alert) for sent in referenced.get(alert.identifier, ()))

    stale_before = now - timedelta(days=filters.stale_days)
    active: List[ActiveAlert] = []
    for alert in latest.values():
        if alert.msg_type.strip().lower() == "cancel" or replaced(alert):
            drop("cancelled or replaced")
            continue
        info = choose_info(alert.infos, filters.language)
        if info is None:
            drop("no text")
            continue
        end = _latest_end(alert)
        if end is not None and end < now:
            drop("expired")
            continue
        if end is None and alert.sent is not None and alert.sent < stale_before:
            drop("old and without an end")
            continue
        code = level_code(alert.infos)
        if code and code.lower() not in LEVEL_TO_SEVERITY:
            unknown_levels[code] = None                 # named once in the log: the table may need a new entry
        severity = severity_of(alert, code)
        is_test = severity == TEST or _is_test(alert, code, filters.test_levels)
        if is_test and not filters.show_test:
            drop("test")
            ignored_tests.append((alert.identifier, code or alert.status.strip(), info.headline or info.event))
            continue
        if is_test:
            severity = TEST
        categories = tuple(dict.fromkeys(c for i in alert.infos for c in i.categories))
        if filters.ignore_categories and categories and all(c.lower() in filters.ignore_categories for c in categories):
            drop("ignored category")
            continue
        if severity != TEST and SEVERITY_RANK[severity] < filters.min_rank:
            drop("below the minimum severity")
            continue
        areas = _areas(alert)
        local = _local_flag(areas, filters)
        if filters.location_mode == LOCATION_ONLY and local is False:
            drop("outside the location")
            continue
        text = _search_text(alert)
        active.append(ActiveAlert(
            identifier=alert.identifier, severity=severity, rank=SEVERITY_RANK[severity], level_code=code,
            headline=info.headline or info.event or "Alert", description=info.description,
            instruction=info.instruction, event=info.event, sender_name=info.sender_name, language=info.language,
            categories=categories, sent=alert.sent, effective=info.effective, expires=end, web=info.web,
            area_desc=tuple(dict.fromkeys(a.desc for a in areas if a.desc)), local=local,
            watch_match=any(k.lower() in text for k in filters.keywords),
            allergen_match=any(a.lower() in text for a in filters.allergens),
            areas=areas, status=alert.status, msg_type=alert.msg_type, urgency=info.urgency, certainty=info.certainty))

    active.sort(key=lambda a: (a.rank, a.sent or _EPOCH), reverse=True)
    # The portal sometimes publishes the same text again as a new alert (its own number, no reference to the first).
    # Of messages that agree in everything a person reads and in their end, only the newest is kept.
    seen = set()
    unique: List[ActiveAlert] = []
    for alert in active:
        key = (alert.severity, alert.headline, alert.description, alert.instruction, alert.event, alert.area_desc,
               alert.expires)
        if key in seen:
            drop("duplicate")
        else:
            seen.add(key)
            unique.append(alert)
    active = unique
    counts = {severity: 0 for severity in SEVERITIES}
    for alert in active:
        counts[alert.severity] += 1
    ends = [a.expires for a in active if a.expires is not None]
    return Snapshot(tuple(active), counts, min(ends) if ends else None, dropped, tuple(ignored_tests),
                    tuple(unknown_levels))
