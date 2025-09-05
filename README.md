# LU-Alert (Luxembourg) Integration for Home Assistant

This is a custom integration for Home Assistant that provides alerts from the official Luxembourg government's [LU-Alert](https://www.lu-alert.lu/) system.

It fetches data from the public data portal ([data.public.lu](https://data.public.lu/fr/datasets/alertes-du-systeme-lu-alert/)) and presents the latest alert information as a series of sensors in Home Assistant. This allows you to build automations based on official government warnings, such as public safety alerts, weather warnings, or other important announcements.

## Features

- **UI-Based Configuration**: No YAML required. Add and configure the integration directly from the Home Assistant UI.
- **Device Representation**: Creates a single "LU-Alert" device in Home Assistant, which groups all related sensors for a clean and organized experience.
- **Efficient Polling**: Uses a `DataUpdateCoordinator` to fetch data from the source API efficiently, ensuring all sensors are updated from a single, shared data source.
- **Dedicated Sensors**: Provides individual sensors for each piece of alert data (headline, description, severity, etc.), making them easy to use in automations and dashboards.

## Installation

### Via HACS (Home Assistant Community Store) - Recommended

1.  Ensure you have [HACS](https://hacs.xyz/) installed.
2.  Go to HACS > Integrations > and click the three dots in the top right.
3.  Select "Custom repositories" and add the URL for this repository.
4.  Select "Integration" as the category and click "Add".
5.  The "LU-Alert" integration will now be available in HACS. Click "Install".
6.  Restart Home Assistant.

### Manual Installation

1.  Download the latest release from the [Releases](https://github.com/your-github-username/your-repo-name/releases) page.
2.  Copy the `lu_alert` directory from the `custom_components` folder in the downloaded zip file.
3.  Paste the `lu_alert` directory into the `custom_components` folder of your Home Assistant configuration directory.
4.  Restart Home Assistant.

## Configuration

1.  In Home Assistant, go to **Settings** > **Devices & Services**.
2.  Click the **+ ADD INTEGRATION** button in the bottom right.
3.  Search for **"LU-Alert"** and click on it.
4.  Follow the on-screen instructions to complete the setup.

The integration will be added, and you will find a new LU-Alert device with all its associated sensors ready to be used.

## Sensors

The integration will create the following sensors:

- **Headline**: The main title of the alert.
- **Status**: The operational status of the alert (e.g., "Actual", "Test").
- **Message Type**: The type of message (e.g., "Alert", "Update").
- **Description**: A detailed description of the alert, often containing HTML.
- **Sender**: The agency that sent the alert.
- **Severity**: The severity level of the alert (e.g., "Severe", "Moderate").
- **Certainty**: The certainty level of the alert (e.g., "Observed", "Likely").
- **Urgency**: The urgency level of the alert (e.g., "Immediate", "Expected").
- **Event**: The category of the event (e.g., "Avertissement alimentaire").
- **Instruction**: Recommended actions to take.
- **Sent Time**: The timestamp when the alert was sent.
- **Expires Time**: The timestamp when the alert is expected to expire.
- **Web**: A URL for more information.

When no alert is active, the sensors will report a default "clear" state (e.g., "No active alert").
