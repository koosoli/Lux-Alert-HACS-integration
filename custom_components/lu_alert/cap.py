"""Parser for CAP 1.2 messages as the LU-Alert feed publishes them (profile CAP-LU 1.1).

Lenient on purpose: an element that is missing or has an unknown value becomes an empty string or None, never an
exception. Only a document that is not CAP at all raises ``CapError``. The namespace is not checked (the feed writes
``urn:oasis:names:tc:emergency:cap:1.2``, other producers use ``...cap:1.1``): elements are matched by local name.

The parser refuses documents with a DOCTYPE or ENTITY declaration. CAP never needs them, and they are how an XML
bomb (an entity that expands to gigabytes) gets into a parser.
"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Iterator, List, Optional, Tuple, Union

from .model import Area, CapAlert, Info, Parameter
from .util import plain_text

_DECLARATION = re.compile(r"^\s*<\?xml[^>]*\?>")
_DTD = re.compile(r"<!\s*(DOCTYPE|ENTITY)", re.I)
_TIME = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(?:[.,]\d+)?)?\s*(Z|[+-]\d{2}:?\d{2})?$", re.I)


class CapError(ValueError):
    """The text is not a CAP document."""


def parse_time(text: Optional[str]) -> Optional[datetime]:
    """An ISO 8601 date and time (CAP writes 2026-10-01T14:30:00+02:00) as an aware datetime; None if it is not one.

    A time without zone is read as UTC; ``Z``, ``+0200`` and fractions of a second are understood too."""
    if not text:
        return None
    match = _TIME.match(text.strip())
    if not match:
        return None
    year, month, day, hour, minute, second, zone = match.groups()
    if zone is None or zone.upper() == "Z":
        tz = timezone.utc
    else:
        digits = zone[1:].replace(":", "")
        offset = timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
        tz = timezone(-offset if zone[0] == "-" else offset)
    try:
        return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second or 0), tzinfo=tz)
    except ValueError:                                  # month 13, hour 25, ...
        return None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _children(element: ET.Element, name: str) -> Iterator[ET.Element]:
    return (child for child in element if _local(child.tag) == name)


def _text(element: ET.Element, name: str) -> str:
    for child in _children(element, name):
        return (child.text or "").strip()
    return ""


def _texts(element: ET.Element, name: str) -> Tuple[str, ...]:
    return tuple(t for t in ((child.text or "").strip() for child in _children(element, name)) if t)


def _inner_text(element: ET.Element, name: str) -> str:
    """The text of an element that may contain markup (a CAP description), as plain text."""
    for child in _children(element, name):
        inner = (child.text or "") + "".join(ET.tostring(sub, encoding="unicode") for sub in child)
        return plain_text(inner)
    return ""


def _area(element: ET.Element) -> Area:
    geocodes = []
    for code in _children(element, "geocode"):
        value = _text(code, "value") or (code.text or "").strip()
        if value:
            name = _text(code, "valueName")
            geocodes.append("%s=%s" % (name, value) if name else value)
    return Area(desc=_text(element, "areaDesc"), polygons=_texts(element, "polygon"), circles=_texts(element, "circle"),
                geocodes=tuple(geocodes))


def _info(element: ET.Element) -> Info:
    return Info(
        language=_text(element, "language"),
        categories=_texts(element, "category"),
        event=_text(element, "event"),
        urgency=_text(element, "urgency"),
        severity=_text(element, "severity"),
        certainty=_text(element, "certainty"),
        effective=parse_time(_text(element, "effective")),
        onset=parse_time(_text(element, "onset")),
        expires=parse_time(_text(element, "expires")),
        sender_name=_text(element, "senderName"),
        headline=_text(element, "headline"),
        description=_inner_text(element, "description"),
        instruction=_inner_text(element, "instruction"),
        web=_text(element, "web"),
        parameters=tuple(Parameter(_text(p, "valueName"), _text(p, "value")) for p in _children(element, "parameter")),
        areas=tuple(_area(a) for a in _children(element, "area")),
    )


def _alert(element: ET.Element) -> CapAlert:
    return CapAlert(
        identifier=_text(element, "identifier"),
        sender=_text(element, "sender"),
        sent=parse_time(_text(element, "sent")),
        status=_text(element, "status"),
        msg_type=_text(element, "msgType"),
        scope=_text(element, "scope"),
        codes=_texts(element, "code"),
        note=_text(element, "note"),
        references=_text(element, "references"),
        infos=tuple(_info(i) for i in _children(element, "info")),
    )


def parse_cap(document: Union[bytes, str]) -> List[CapAlert]:
    """All <alert> messages of a document (the root is an <alert>, or has <alert> children). Raises CapError."""
    if isinstance(document, bytes):
        try:
            text = document.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise CapError("the document is not UTF-8 text") from None
    else:
        text = document
    if _DTD.search(text):
        raise CapError("the document has a DOCTYPE or ENTITY declaration, which CAP does not use")
    text = _DECLARATION.sub("", text, count=1)          # a str with an encoding declaration is parsed as it is
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise CapError("not well-formed XML: %s" % exc) from exc
    if _local(root.tag) == "alert":
        elements = [root]
    else:
        elements = list(_children(root, "alert"))
    if not elements:
        raise CapError("no <alert> element (the root is <%s>)" % _local(root.tag))
    return [_alert(e) for e in elements]
