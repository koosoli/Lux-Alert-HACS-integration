import requests
import sys

# The API endpoint to get the latest alert dataset information.
DATASET_API_URL = "https://data.public.lu/api/1/datasets/67aca67bcaea3ae62308114f/"

def get_latest_alert_url() -> str:
    """
    Fetches the dataset information from the data.public.lu API
    and returns the URL of the latest CAP XML file.

    Returns:
        The URL of the XML file as a string.

    Raises:
        requests.exceptions.RequestException: If there is a network-related error.
        ValueError: If the JSON response is not in the expected format.
    """
    print(f"Fetching dataset info from {DATASET_API_URL}...")
    try:
        response = requests.get(DATASET_API_URL, timeout=15)
        # Raise an HTTPError for bad responses (4xx or 5xx)
        response.raise_for_status()

        data = response.json()

        if "resources" in data and data["resources"]:
            # The API response lists resources, with the most recent first.
            # We will iterate through them and pick the first one that is an XML file.
            for resource in data["resources"]:
                if resource.get("format", "").lower() == "xml":
                    url = resource.get("url")
                    if url:
                        print(f"Found latest alert XML: {url}")
                        return url

            # If no XML resource is found after checking all, raise an error.
            raise ValueError("No XML resource found in the dataset.")
        else:
            raise ValueError("'resources' list not found or is empty in API response.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}", file=sys.stderr)
        raise
    except (ValueError, KeyError) as e:
        print(f"Error parsing JSON response or finding URL: {e}", file=sys.stderr)
        raise

from cap_lu.parser import parse_xml
from cap_lu.models import Alert
import json

def fetch_and_parse_alert(xml_url: str) -> Alert | None:
    """
    Fetches the CAP XML file from the given URL and parses it.
    Returns an Alert object or None if no alert is found.
    """
    try:
        print(f"Fetching XML alert from {xml_url}...")
        response = requests.get(xml_url, timeout=15)
        response.raise_for_status()
        print("Successfully fetched XML content. Parsing...")
        return parse_xml(response.text)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching XML file: {e}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Error parsing XML content: {e}", file=sys.stderr)
        raise


def get_default_sensor_data() -> dict:
    """Returns a dictionary with default values for a 'clear' state."""
    return {
        "LU-Alert Status": "OK",
        "LU-Alert Type": "Keine",
        "LU-Alert Certainty": "N/A",
        "LU-Alert Urgency": "N/A",
        "LU-Alert Severity": "N/A",
        "LU-Alert Event": "Keine Warnung",
        "LU-Alert Headline": "Keine Warnung",
        "LU-Alert Description": "Derzeit liegt keine aktive Warnung vor.",
        "LU-Alert Sender": "N/A",
        "LU-Alert Sent": "N/A",
        "LU-Alert Identifier": "N/A",
    }


if __name__ == "__main__":
    sensor_data = {}
    try:
        latest_url = get_latest_alert_url()
        alert = fetch_and_parse_alert(latest_url)

        if alert and alert.info:
            # We assume the first info block is the most relevant one
            info = alert.info[0]
            sensor_data = {
                "LU-Alert Status": alert.status.value if alert.status else "N/A",
                "LU-Alert Type": alert.msgType.value if alert.msgType else "N/A",
                "LU-Alert Certainty": info.certainty.value if info.certainty else "N/A",
                "LU-Alert Urgency": info.urgency.value if info.urgency else "N/A",
                "LU-Alert Severity": info.severity.value if info.severity else "N/A",
                "LU-Alert Event": info.event,
                "LU-Alert Headline": info.headline,
                "LU-Alert Description": info.description,
                "LU-Alert Sender": alert.sender,
                "LU-Alert Sent": alert.sent.isoformat() if alert.sent else "N/A",
                "LU-Alert Identifier": alert.identifier,
            }
            print("Successfully processed alert data.")
        else:
            print("No active alert found or alert has no info. Using default values.")
            sensor_data = get_default_sensor_data()

    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"An error occurred: {e}. Using default values.", file=sys.stderr)
        sensor_data = get_default_sensor_data()

    # Output the final sensor data as a JSON object
    print("\n--- Sensor Data ---")
    print(json.dumps(sensor_data, indent=4, ensure_ascii=False))
