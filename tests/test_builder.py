import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from cap_lu.models import Alert, Info, Area, Parameter
from cap_lu.enums import Status, MsgType, Scope, Code, Category, Urgency, Severity, Certainty, Canal
from cap_lu.builder import build_xml, CAP_XMLNS

class TestBuilder(unittest.TestCase):

    def test_build_xml_full(self):
        """
        Tests the build_xml function with a comprehensive Alert object
        to ensure all parts are serialized correctly.
        """
        # 1. Create a comprehensive Alert object to simulate a real-world use case.
        alert_obj = Alert(
            identifier="MIGOA.1646310540.9030.0",
            sender="ctie@etat.lu",
            sent=datetime(2025, 9, 5, 6, 30, 0, tzinfo=timezone(timedelta(hours=2))),
            status=Status.TEST,
            msgType=MsgType.ALERT,
            scope=Scope.PUBLIC,
            code=[Code.IN_ZONE],
            info=[
                Info(
                    language="fr-LU",
                    category=[Category.SAFETY],
                    event="Test Event",
                    urgency=Urgency.IMMEDIATE,
                    severity=Severity.SEVERE,
                    certainty=Certainty.OBSERVED,
                    expires=datetime(2025, 9, 5, 7, 30, 0, tzinfo=timezone(timedelta(hours=2))),
                    senderName="LU-ALERT",
                    headline="Test Alert Headline",
                    description="This is a test description.",
                    instruction="This is a test instruction.",
                    web="http://www.test.lu",
                    parameters=[
                        Parameter(valueName="canal", value=Canal.SMS.value),
                        Parameter(valueName="canal-id", value="1")
                    ],
                    area=[
                        Area(
                            areaDesc="Test Area",
                            polygon="49.6,6.1 49.7,6.1 49.7,6.2 49.6,6.2 49.6,6.1"
                        )
                    ]
                )
            ]
        )

        # 2. Build the XML string from the Alert object.
        xml_string = build_xml(alert_obj)

        # 3. Parse the generated XML back using ElementTree to verify its structure and content.
        # This will fail if the XML is not well-formed.
        root = ET.fromstring(xml_string)

        # 4. Assert that the generated XML matches the source object.
        self.assertEqual(root.tag, f"{{{CAP_XMLNS}}}alert")

        # Check top-level elements of <alert>
        self.assertEqual(root.find(f"{{{CAP_XMLNS}}}identifier").text, "MIGOA.1646310540.9030.0")
        self.assertEqual(root.find(f"{{{CAP_XMLNS}}}sender").text, "ctie@etat.lu")
        self.assertEqual(root.find(f"{{{CAP_XMLNS}}}sent").text, "2025-09-05T06:30:00+02:00")
        self.assertEqual(root.find(f"{{{CAP_XMLNS}}}status").text, "Test")
        self.assertEqual(root.find(f"{{{CAP_XMLNS}}}msgType").text, "Alert")
        self.assertEqual(root.find(f"{{{CAP_XMLNS}}}scope").text, "Public")
        self.assertEqual(root.find(f"{{{CAP_XMLNS}}}code").text, "In-zone")

        # Check <info> block
        info_element = root.find(f"{{{CAP_XMLNS}}}info")
        self.assertIsNotNone(info_element)
        self.assertEqual(info_element.find(f"{{{CAP_XMLNS}}}language").text, "fr-LU")
        self.assertEqual(info_element.find(f"{{{CAP_XMLNS}}}category").text, "Safety")
        self.assertEqual(info_element.find(f"{{{CAP_XMLNS}}}headline").text, "Test Alert Headline")

        # Check <area> block within <info>
        area_element = info_element.find(f"{{{CAP_XMLNS}}}area")
        self.assertIsNotNone(area_element)
        self.assertEqual(area_element.find(f"{{{CAP_XMLNS}}}areaDesc").text, "Test Area")
        self.assertEqual(area_element.find(f"{{{CAP_XMLNS}}}polygon").text, "49.6,6.1 49.7,6.1 49.7,6.2 49.6,6.2 49.6,6.1")

        # Check <parameter> blocks within <info>
        param_elements = info_element.findall(f"{{{CAP_XMLNS}}}parameter")
        self.assertEqual(len(param_elements), 2)
        self.assertEqual(param_elements[0].find(f"{{{CAP_XMLNS}}}valueName").text, "canal")
        self.assertEqual(param_elements[0].find(f"{{{CAP_XMLNS}}}value").text, "Sms")

if __name__ == '__main__':
    unittest.main()
