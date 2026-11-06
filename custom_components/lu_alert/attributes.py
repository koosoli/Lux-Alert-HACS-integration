"""The state attributes of the entities: alerts as plain, JSON-safe dictionaries. No Home Assistant imports."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .const import SEVERITY_RANK
from .model import ActiveAlert, Area, Snapshot

# Attributes that can be large (text, geometry). They are not written to the recorder database, which refuses
# states with more than 16 kB of attributes; the state machine and the dashboard card still have them.
UNRECORDED = frozenset({"description", "instruction", "area", "alerts"})


def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat() if moment is not None else None


def _area(area: Area) -> dict[str, Any]:
    return {"areaDesc": area.desc, "polygons": list(area.polygons), "circles": list(area.circles),
            "geocodes": list(area.geocodes)}


def alert_attributes(alert: ActiveAlert) -> dict[str, Any]:
    """One alert as it appears in the attributes of the entities and in the dashboard card."""
    return {
        "identifier": alert.identifier,
        "headline": alert.headline,
        "description": alert.description,
        "instruction": alert.instruction,
        "severity": alert.severity,
        "severity_level": SEVERITY_RANK[alert.severity],
        "level_code": alert.level_code or None,
        "event": alert.event,
        "senderName": alert.sender_name,
        "status": alert.status or None,
        "msgType": alert.msg_type or None,
        "urgency": alert.urgency or None,
        "certainty": alert.certainty or None,
        "language": alert.language,
        "category": list(alert.categories),
        "sent": _iso(alert.sent),
        "effective": _iso(alert.effective),
        "expires": _iso(alert.expires),
        "web": alert.web or None,
        "area_desc": list(alert.area_desc),
        "area": [_area(a) for a in alert.areas],
        "is_local": alert.local,
        "watch_match": alert.watch_match,
        "allergen_match": alert.allergen_match,
    }


def snapshot_attributes(snapshot: Snapshot) -> list[dict[str, Any]]:
    return [alert_attributes(a) for a in snapshot.alerts]
