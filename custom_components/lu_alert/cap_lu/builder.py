import xml.etree.ElementTree as ET
from datetime import datetime
from .models import Alert

# The official namespace for CAP 1.2, which CAP-LU is based on.
CAP_XMLNS = "urn:oasis:names:tc:emergency:cap:1.2"

def build_xml(alert: Alert) -> str:
    """
    Builds a CAP 1.2 XML string from an Alert object.

    Args:
        alert: An instance of the Alert dataclass.

    Returns:
        A string containing the formatted XML.
    """
    # Register the namespace to avoid "ns0:" prefixes in the output.
    ET.register_namespace("", CAP_XMLNS)

    # Create the root <alert> element with the correct namespace.
    root = ET.Element(f"{{{CAP_XMLNS}}}alert")

    # Helper function to add a new XML element to a parent.
    # It correctly handles various data types and skips optional fields that are None.
    def add_element(parent, tag, value):
        if value is None:
            return  # Skip optional elements that are not set.

        # If the value is a list, create a separate element for each item.
        if isinstance(value, list):
            for item in value:
                # Recursive call to handle each item in the list.
                add_element(parent, tag, item)
            return

        # Format the value into a string for the XML text content.
        if isinstance(value, datetime):
            # Format datetime to ISO 8601 with timezone, as required by CAP.
            # Python's isoformat() works well here.
            text = value.isoformat()
        elif hasattr(value, 'value'):  # Check for Enum members
            text = str(value.value)
        else:
            text = str(value)

        element = ET.SubElement(parent, f"{{{CAP_XMLNS}}}{tag}")
        element.text = text

    # Populate the direct children of the <alert> element.
    add_element(root, "identifier", alert.identifier)
    add_element(root, "sender", alert.sender)
    add_element(root, "sent", alert.sent)
    add_element(root, "status", alert.status)
    add_element(root, "msgType", alert.msgType)
    add_element(root, "scope", alert.scope)
    add_element(root, "code", alert.code)
    add_element(root, "note", alert.note)
    add_element(root, "references", alert.references)

    # Process and add each <info> block.
    for info_obj in alert.info:
        info_element = ET.SubElement(root, f"{{{CAP_XMLNS}}}info")
        add_element(info_element, "language", info_obj.language)
        add_element(info_element, "category", info_obj.category)
        add_element(info_element, "event", info_obj.event)
        add_element(info_element, "urgency", info_obj.urgency)
        add_element(info_element, "severity", info_obj.severity)
        add_element(info_element, "certainty", info_obj.certainty)
        add_element(info_element, "effective", info_obj.effective)
        add_element(info_element, "expires", info_obj.expires)
        add_element(info_element, "senderName", info_obj.senderName)
        add_element(info_element, "headline", info_obj.headline)
        add_element(info_element, "description", info_obj.description)
        add_element(info_element, "instruction", info_obj.instruction)
        add_element(info_element, "web", info_obj.web)

        # Process and add each <parameter> block within <info>.
        for param_obj in info_obj.parameters:
            param_element = ET.SubElement(info_element, f"{{{CAP_XMLNS}}}parameter")
            add_element(param_element, "valueName", param_obj.valueName)
            add_element(param_element, "value", param_obj.value)

        # Process and add each <area> block within <info>.
        for area_obj in info_obj.area:
            area_element = ET.SubElement(info_element, f"{{{CAP_XMLNS}}}area")
            add_element(area_element, "areaDesc", area_obj.areaDesc)
            add_element(area_element, "polygon", area_obj.polygon)
            add_element(area_element, "circle", area_obj.circle)
            add_element(area_element, "geocode", area_obj.geocode)

    # Convert the XML tree to a string with a proper XML declaration.
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
