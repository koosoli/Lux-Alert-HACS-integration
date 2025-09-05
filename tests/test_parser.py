import unittest
from datetime import datetime, timezone, timedelta
from cap_lu.models import Alert, Info, Area, Parameter
from cap_lu.enums import Status, MsgType, Scope, Code, Category, Urgency, Severity, Certainty, Canal
from cap_lu.builder import build_xml
from cap_lu.parser import parse_xml

class TestParser(unittest.TestCase):

    def test_round_trip(self):
        """
        Tests that an Alert object can be built into XML and then parsed
        back into an identical object, ensuring the builder and parser are compatible.
        """
        # 1. Create the original Alert object.
        # Using a comprehensive object with many fields populated.
        original_alert = Alert(
            identifier="MIGOA.1646310540.9030.0",
            sender="ctie@etat.lu",
            sent=datetime(2025, 9, 5, 6, 30, 0, tzinfo=timezone(timedelta(hours=2))),
            status=Status.TEST,
            msgType=MsgType.ALERT,
            scope=Scope.PUBLIC,
            code=[Code.IN_ZONE],
            note="This is a test note.",
            references="test@test.com,2025-09-05T06:00:00+02:00,ref1",
            info=[
                Info(
                    language="fr-LU",
                    category=[Category.SAFETY, Category.HEALTH],
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

        # 2. Build the XML string from the original object.
        xml_string = build_xml(original_alert)

        # 3. Parse the XML string back into a new object.
        parsed_alert = parse_xml(xml_string)

        # 4. Assert that the parsed object is equal to the original.
        # Python's dataclasses provide a default __eq__ method which recursively
        # compares all fields, making this assertion very powerful.
        self.assertEqual(original_alert, parsed_alert)

if __name__ == '__main__':
    unittest.main()
