import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional, Type, TypeVar
from .models import Alert, Info, Area, Parameter
from .enums import Status, MsgType, Scope, Code, Category, Urgency, Severity, Certainty
from .builder import CAP_XMLNS  # Reuse the namespace constant

# Generic TypeVar for Enum types
T = TypeVar('T', bound='Enum')

def _find_text(element: ET.Element, tag: str, namespace: str) -> Optional[str]:
    """Helper to find the text content of a single namespaced child element."""
    child = element.find(f"{{{namespace}}}{tag}")
    return child.text.strip() if child is not None and child.text else None

def _find_all_text(element: ET.Element, tag: str, namespace: str) -> List[str]:
    """Helper to find the text content of all namespaced child elements with the same tag."""
    return [child.text.strip() for child in element.findall(f"{{{namespace}}}{tag}") if child.text]

def _to_enum(enum_class: Type[T], value: Optional[str]) -> Optional[T]:
    """Helper to safely convert a string to a member of a given Enum."""
    if value is None:
        return None
    try:
        return enum_class(value)
    except ValueError:
        # If the value from the XML is not a valid member of the enum,
        # return None. This makes parsing more lenient.
        return None

def _to_datetime(value: Optional[str]) -> Optional[datetime]:
    """Helper to parse an ISO 8601 string to a datetime object."""
    if value is None:
        return None
    try:
        # datetime.fromisoformat is powerful and handles most W3C/ISO 8601 formats.
        return datetime.fromisoformat(value)
    except ValueError:
        return None

def parse_xml(xml_string: str) -> Optional[Alert]:
    """
    Parses a CAP XML string and deserializes it into an Alert data object.
    This function handles XML with a root that contains <alert> tags.
    It will parse the *first* <alert> tag found.

    Args:
        xml_string: A string containing the CAP XML data.

    Returns:
        An instance of the Alert dataclass, or None if no <alert> tag is found.
    """
    root = ET.fromstring(xml_string)

    # Dynamically extract the namespace from the root element's tag
    ns = ''
    if '}' in root.tag:
        ns = root.tag.split('}')[0][1:]

    # Find the first <alert> element. If the root is <alert>, this will be the root itself.
    # If the root is <alerts>, it will find the first child.
    alert_element = root
    if root.tag != f"{{{ns}}}alert":
        alert_element = root.find(f"{{{ns}}}alert")

    if alert_element is None:
        return None # No <alert> tag found in the document.

    # Parse all <info> blocks from the <alert> element
    info_list = []
    for info_element in alert_element.findall(f"{{{ns}}}info"):
        param_list = [
            Parameter(
                valueName=_find_text(p, "valueName", ns),
                value=_find_text(p, "value", ns)
            ) for p in info_element.findall(f"{{{ns}}}parameter")
        ]
        area_list = [
            Area(
                areaDesc=_find_text(a, "areaDesc", ns),
                polygon=_find_text(a, "polygon", ns),
                circle=_find_text(a, "circle", ns),
                geocode=_find_text(a, "geocode", ns)
            ) for a in info_element.findall(f"{{{ns}}}area")
        ]
        info_obj = Info(
            language=_find_text(info_element, "language", ns),
            category=[_to_enum(Category, cat) for cat in _find_all_text(info_element, "category", ns) if cat],
            event=_find_text(info_element, "event", ns),
            urgency=_to_enum(Urgency, _find_text(info_element, "urgency", ns)),
            severity=_to_enum(Severity, _find_text(info_element, "severity", ns)),
            certainty=_to_enum(Certainty, _find_text(info_element, "certainty", ns)),
            effective=_to_datetime(_find_text(info_element, "effective", ns)),
            expires=_to_datetime(_find_text(info_element, "expires", ns)),
            senderName=_find_text(info_element, "senderName", ns),
            headline=_find_text(info_element, "headline", ns),
            description=_find_text(info_element, "description", ns),
            instruction=_find_text(info_element, "instruction", ns),
            web=_find_text(info_element, "web", ns),
            parameters=param_list,
            area=area_list
        )
        info_list.append(info_obj)

    # Parse the main <alert> element's data
    alert_obj = Alert(
        identifier=_find_text(alert_element, "identifier", ns),
        sender=_find_text(alert_element, "sender", ns),
        sent=_to_datetime(_find_text(alert_element, "sent", ns)),
        status=_to_enum(Status, _find_text(alert_element, "status", ns)),
        msgType=_to_enum(MsgType, _find_text(alert_element, "msgType", ns)),
        scope=_to_enum(Scope, _find_text(alert_element, "scope", ns)),
        code=[_to_enum(Code, c) for c in _find_all_text(alert_element, "code", ns) if c],
        note=_find_text(alert_element, "note", ns),
        references=_find_text(alert_element, "references", ns),
        info=info_list
    )

    return alert_obj
