"""Plain data objects handed between the layers. Nothing here knows about Home Assistant, HTTP or XML parsers."""
from datetime import datetime
from typing import Dict, NamedTuple, Optional, Tuple


class Parameter(NamedTuple):
    name: str
    value: str


class Area(NamedTuple):
    desc: str
    polygons: Tuple[str, ...] = ()          # "lat,lon lat,lon ..." as in CAP
    circles: Tuple[str, ...] = ()           # "lat,lon radius_km"
    geocodes: Tuple[str, ...] = ()


class Info(NamedTuple):
    """One <info> block. CAP-LU sends one block per language and per channel (Sms, Cell-Broadcast, Mobile-App, ...)."""
    language: str = ""
    categories: Tuple[str, ...] = ()
    event: str = ""
    urgency: str = ""
    severity: str = ""
    certainty: str = ""
    effective: Optional[datetime] = None
    onset: Optional[datetime] = None
    expires: Optional[datetime] = None
    sender_name: str = ""
    headline: str = ""
    description: str = ""                   # plain text: the markup of the feed is removed by the parser
    instruction: str = ""
    web: str = ""
    parameters: Tuple[Parameter, ...] = ()
    areas: Tuple[Area, ...] = ()


class CapAlert(NamedTuple):
    """One <alert> (a CAP message)."""
    identifier: str
    sender: str = ""
    sent: Optional[datetime] = None
    status: str = ""
    msg_type: str = ""
    scope: str = ""
    codes: Tuple[str, ...] = ()
    note: str = ""
    references: str = ""
    infos: Tuple[Info, ...] = ()


class ActiveAlert(NamedTuple):
    """An alert that is in force now, with the text and the numbers the entities show."""
    identifier: str
    severity: str                           # Extreme | Severe | Moderate | Minor | Information | Unknown | Test
    rank: int                               # see const.SEVERITY_RANK
    level_code: str                         # the LU-Alert level of the feed ("N2", "LU-Alert Level 2", "" if absent)
    headline: str
    description: str
    instruction: str
    event: str
    sender_name: str
    language: str                           # the language of the text above
    categories: Tuple[str, ...]
    sent: Optional[datetime]
    effective: Optional[datetime]
    expires: Optional[datetime]             # the latest end over all language blocks; None = no end given
    web: str
    area_desc: Tuple[str, ...]
    local: Optional[bool]                   # True inside the area, False outside, None: location unknown or no geometry
    watch_match: bool
    allergen_match: bool
    areas: Tuple[Area, ...] = ()            # the distinct areas over all blocks, with their geometry
    status: str = ""                        # CAP status of the message (Actual, ...)
    msg_type: str = ""                      # Alert | Update | ...
    urgency: str = ""
    certainty: str = ""


class Snapshot(NamedTuple):
    """Everything the devices show, computed from the CAP messages at one moment."""
    alerts: Tuple[ActiveAlert, ...] = ()    # most severe first, newest first within a severity
    counts: Dict[str, int] = {}             # alerts per severity
    next_expiry: Optional[datetime] = None  # when the first alert with an end ends: time to compute again
    dropped: Dict[str, int] = {}            # why messages were left out ("expired", "test", "cancelled", ...)
    ignored_tests: Tuple[Tuple[str, str, str], ...] = ()    # (identifier, level or status, headline) of tests left out
    unknown_levels: Tuple[str, ...] = ()    # level codes the plugin does not know (the CAP severity was used instead)

    @property
    def total(self) -> int:
        return len(self.alerts)
