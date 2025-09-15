import xml.etree.ElementTree as ET
import re
from datetime import datetime
from typing import List, Optional, Type, TypeVar
from .models import Alert, Info, Area, Parameter
from .enums import Status, MsgType, Scope, Code, Category, Urgency, Severity, Certainty
from .builder import CAP_XMLNS  # Reuse the namespace constant

# Generic TypeVar for Enum types
T = TypeVar('T', bound='Enum')

def _get_inner_html(element: Optional[ET.Element]) -> Optional[str]:
    """Helper to get the full inner HTML of an element."""
    if element is None:
        return None
    # This combines the initial text with the serialized child elements.
    # The tail of each child is included by tostring.
    return (element.text or "") + "".join(
        ET.tostring(child, encoding="unicode") for child in element
    )


def _parse_html_description(html_string: Optional[str]) -> dict[str, str]:
    """
    Parses an HTML string from a description to extract key-value data.
    It robustly handles different structures within the HTML.
    """
    if not html_string:
        return {}

    try:
        # Sanitize and wrap HTML to ensure it's parsable as XML
        sanitized_html = html_string.replace("&nbsp;", " ").replace("<br>", "<br/>").replace("&", "&amp;")
        sanitized_html = re.sub(r"<img([^>]+)>", r"<img\1/>", sanitized_html)
        root = ET.fromstring(f"<div>{sanitized_html}</div>")
    except ET.ParseError:
        return {}

    data = {}

    # Helper to get all text from an element, including children
    def get_full_text(element):
        return "".join(element.itertext()).strip()

    # Process <li> tags, which are the most common structure
    for li in root.findall(".//li"):
        strong_tag = li.find("strong")
        if strong_tag is not None and strong_tag.text:
            key_text = get_full_text(strong_tag)
            key = key_text.strip().rstrip(":").lower().replace(" ", "_").replace("(", "").replace(")", "")

            # The value is the rest of the text in the <li> after the key
            full_li_text = get_full_text(li)
            value = full_li_text[len(key_text):].strip()

            if key and value:
                data[key] = value

    # Process <p> tags for cases like "Reason"
    for p in root.findall(".//p"):
        strong_tag = p.find("strong")
        if strong_tag is not None and strong_tag.text:
            key_text = get_full_text(strong_tag)
            key = key_text.strip().rstrip(":").lower().replace(" ", "_").replace("(", "").replace(")", "")

            # The value is the rest of the text in the <p> after the key
            full_p_text = get_full_text(p)
            value = full_p_text[len(key_text):].strip()

            if key and value:
                data[key] = value

    return data

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

def parse_xml(xml_string: str) -> List[Alert]:
    """
    Parses a CAP XML string and deserializes it into a list of Alert data objects.
    This function handles XML with a root that contains <alert> tags.
    It will parse *all* <alert> tags found.

    Args:
        xml_string: A string containing the CAP XML data.

    Returns:
        A list of Alert dataclass instances. Returns an empty list if no
        <alert> tags are found.
    """
    root = ET.fromstring(xml_string)

    # Dynamically extract the namespace from the root element's tag
    ns = ''
    if '}' in root.tag:
        ns = root.tag.split('}')[0][1:]

    alert_elements = []
    if root.tag == f"{{{ns}}}alert":
        # The root element itself is an alert
        alert_elements.append(root)
    else:
        # Find all <alert> children under the root
        alert_elements.extend(root.findall(f"{{{ns}}}alert"))

    parsed_alerts = []
    for alert_element in alert_elements:
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
                description=_get_inner_html(info_element.find(f"{{{ns}}}description")),
                instruction=_find_text(info_element, "instruction", ns),
                web=_find_text(info_element, "web", ns),
                parameters=param_list,
                area=area_list,
                structured_description=_parse_html_description(
                    _get_inner_html(info_element.find(f"{{{ns}}}description"))
                ),
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
        parsed_alerts.append(alert_obj)

    return parsed_alerts
