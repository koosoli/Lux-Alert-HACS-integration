import unittest
from unittest.mock import patch, Mock
import os
import sys
from datetime import datetime, timezone

# Add the project root to the Python path to allow importing from 'cap_lu' and 'integration'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integration import get_latest_alert_url, fetch_and_parse_alert, get_default_sensor_data
from cap_lu.models import Alert, Info, Status, MsgType, Certainty, Urgency, Severity

# Fixture data for mocking API responses
MOCK_DATASET_API_RESPONSE_OK = {
    "resources": [
        {"url": "https://example.com/latest_alert.xml", "format": "xml"},
        {"url": "https://example.com/old_alert.xml", "format": "xml"},
        {"url": "https://example.com/some_doc.pdf", "format": "pdf"},
    ]
}

MOCK_DATASET_API_RESPONSE_NO_XML = {
    "resources": [
        {"url": "https://example.com/some_doc.pdf", "format": "pdf"},
    ]
}

MOCK_DATASET_API_RESPONSE_EMPTY = {
    "resources": []
}

# Load XML fixtures from files for mocking alert fetches
def load_fixture(filename):
    with open(os.path.join(os.path.dirname(__file__), 'fixtures', filename), 'r') as f:
        return f.read()

TEST_XML_OK = load_fixture('test_alert_ok.xml')
TEST_XML_NO_ALERT = load_fixture('test_alert_no_alert.xml')

class TestIntegrationScript(unittest.TestCase):

    @patch('requests.get')
    def test_get_latest_alert_url_success(self, mock_get):
        """Test that get_latest_alert_url returns the first XML URL successfully."""
        mock_response = Mock()
        mock_response.json.return_value = MOCK_DATASET_API_RESPONSE_OK
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        url = get_latest_alert_url()
        self.assertEqual(url, "https://example.com/latest_alert.xml")
        mock_get.assert_called_once_with("https://data.public.lu/api/1/datasets/67aca67bcaea3ae62308114f/", timeout=15)

    @patch('requests.get')
    def test_get_latest_alert_url_no_xml(self, mock_get):
        """Test that a ValueError is raised if no XML resource is found."""
        mock_response = Mock()
        mock_response.json.return_value = MOCK_DATASET_API_RESPONSE_NO_XML
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            get_latest_alert_url()
        self.assertEqual(str(context.exception), "No XML resource found in the dataset.")

    @patch('requests.get')
    def test_get_latest_alert_url_empty_resources(self, mock_get):
        """Test that a ValueError is raised if the resources list is empty."""
        mock_response = Mock()
        mock_response.json.return_value = MOCK_DATASET_API_RESPONSE_EMPTY
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            get_latest_alert_url()
        self.assertEqual(str(context.exception), "'resources' list not found or is empty in API response.")

    @patch('requests.get')
    def test_fetch_and_parse_alert_success(self, mock_get):
        """Test successfully fetching and parsing an alert."""
        mock_response = Mock()
        mock_response.text = TEST_XML_OK
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        alert = fetch_and_parse_alert("http://example.com/dummy.xml")
        self.assertIsInstance(alert, Alert)
        self.assertEqual(alert.identifier, "LU-Alert.1721304000.4000.0")
        self.assertEqual(alert.status, Status.ACTUAL)
        self.assertIsInstance(alert.info[0], Info)

    @patch('requests.get')
    def test_fetch_and_parse_no_alert(self, mock_get):
        """Test fetching content with no <alert> tag, which should return None."""
        mock_response = Mock()
        mock_response.text = TEST_XML_NO_ALERT
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        alert = fetch_and_parse_alert("http://example.com/no_alert.xml")
        self.assertIsNone(alert)

    def test_get_default_sensor_data(self):
        """Test that the default sensor data is returned correctly."""
        data = get_default_sensor_data()
        self.assertEqual(data["LU-Alert Status"], "OK")
        self.assertEqual(data["LU-Alert Event"], "Keine Warnung")
        self.assertEqual(data["LU-Alert Identifier"], "N/A")

if __name__ == '__main__':
    unittest.main()
