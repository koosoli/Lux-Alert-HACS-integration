import unittest
from datetime import datetime, timezone
from cap_lu.models import Alert, Info, Area, Parameter
from cap_lu.enums import Status, MsgType, Scope, Code, Category, Urgency, Severity, Certainty, Canal, RoamerSelection
from cap_lu.validator import validate_alert

class TestValidator(unittest.TestCase):

    def setUp(self):
        """
        Set up a valid, baseline Alert object before each test.
        Tests can modify this object to create specific invalid scenarios.
        """
        self.valid_alert = Alert(
            identifier="MIGOA.1646310540.9030.0",
            sender="ctie@etat.lu",
            sent=datetime.now(timezone.utc),
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
                    area=[Area(areaDesc="Test Area")],
                    parameters=[
                        Parameter(valueName="canal", value=Canal.SMS.value),
                        Parameter(valueName="canal-id", value="1"),
                        Parameter(valueName="roamer-selection", value=RoamerSelection.SUBSCRIBERS.value)
                    ]
                )
            ]
        )

    def test_valid_alert(self):
        """Tests that a correctly structured alert object passes validation with no errors."""
        errors = validate_alert(self.valid_alert)
        self.assertEqual(errors, [], "A valid alert should produce no validation errors.")

    def test_missing_identifier(self):
        """Tests that an alert with a missing 'identifier' fails validation."""
        self.valid_alert.identifier = ""  # Invalid state
        errors = validate_alert(self.valid_alert)
        self.assertIn("Alert 'identifier' is mandatory and cannot be empty.", errors)

    def test_invalid_scope(self):
        """Tests that an alert with a non-Public 'scope' generates a recommendation error."""
        self.valid_alert.scope = Scope.RESTRICTED  # Non-recommended state
        errors = validate_alert(self.valid_alert)
        self.assertIn("CAP-LU recommends 'scope' to be 'Public', but it is 'Restricted'.", errors)

    def test_missing_references_on_update(self):
        """Tests that an 'Update' message type requires the 'references' field."""
        self.valid_alert.msgType = MsgType.UPDATE
        self.valid_alert.references = None  # Invalid state for this msgType
        errors = validate_alert(self.valid_alert)
        self.assertIn("Alert 'references' is mandatory when 'msgType' is 'Update'.", errors)

    def test_missing_areaDesc(self):
        """Tests that an area block with a missing 'areaDesc' fails validation."""
        self.valid_alert.info[0].area[0].areaDesc = ""  # Invalid state
        errors = validate_alert(self.valid_alert)
        # Check if any of the returned errors contains the expected message.
        self.assertTrue(any("'areaDesc' is mandatory" in e for e in errors))

    def test_missing_conditional_parameter_for_sms(self):
        """Tests that the 'roamer-selection' parameter is correctly identified as mandatory for the SMS canal."""
        # Remove the 'roamer-selection' parameter to create the invalid state.
        self.valid_alert.info[0].parameters = [
            p for p in self.valid_alert.info[0].parameters if p.valueName != 'roamer-selection'
        ]
        errors = validate_alert(self.valid_alert)
        self.assertIn("Info block 1 ('fr-LU'): 'roamer-selection' parameter is mandatory for the 'Sms' canal.", errors)

    def test_missing_mandatory_parameter_canal_id(self):
        """Tests that the 'canal-id' parameter is correctly identified as mandatory."""
        self.valid_alert.info[0].parameters = [
            p for p in self.valid_alert.info[0].parameters if p.valueName != 'canal-id'
        ]
        errors = validate_alert(self.valid_alert)
        self.assertIn("Info block 1 ('fr-LU'): The 'canal-id' parameter is mandatory in CAP-LU.", errors)

if __name__ == '__main__':
    unittest.main()
