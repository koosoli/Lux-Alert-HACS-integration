# LU-Alert (Luxembourg) Integration for Home Assistant

This is a custom integration for Home Assistant that provides alerts from the official Luxembourg government's [LU-Alert](https://www.lu-alert.lu/) system.

It fetches data from the public data portal ([data.public.lu](https://data.public.lu/fr/datasets/alertes-du-systeme-lu-alert/)) and presents the most important alerts as a fixed set of sensors. This allows you to build powerful automations and dashboard views based on official government warnings.

This integration is designed to handle multiple simultaneous alerts and allows you to filter them by severity.

## Features

- **Fixed Sensor Sets**: Creates a dedicated set of sensors for each of the top 3 most important alerts (e.g., `sensor.lu_alert_1_headline`, `sensor.lu_alert_2_headline`).
- **Grouped Devices**: The sensors for each alert are grouped into a dedicated device in Home Assistant (e.g., "LU-Alert 1", "LU-Alert 2"), keeping your entity list clean and organized.
- **Handles Multiple Alerts**: Correctly parses and displays the most important alerts from the feed, sorted by severity and date.
- **Configurable Severity Filtering**: A dropdown menu in the configuration allows you to select the minimum severity of alerts you want the integration to consider.
- **UI-Based Configuration**: No YAML required. Add and configure the integration directly from the Home Assistant UI.
- **Efficient Polling**: Uses a `DataUpdateCoordinator` to fetch data from the source API efficiently.

## Installation

### Via HACS (Home Assistant Community Store) - Recommended

1.  Ensure you have [HACS](https://hacs.xyz/) installed.
2.  Go to HACS > Integrations > and click the three dots in the top right.
3.  Select "Custom repositories", add `https://github.com/koosoli/Lux-Alert-HACS-integration` as the repository URL, and select "Integration" as the category.
4.  The "LU-Alert" integration will now be available in HACS. Click "Install".
5.  Restart Home Assistant.

### Manual Installation

1.  Download the latest release from the [Releases](https://github.com/koosoli/Lux-Alert-HACS-integration/releases) page.
2.  Copy the `lu_alert` directory from the `custom_components` folder in the downloaded zip file.
3.  Paste the `lu_alert` directory into the `custom_components` folder of your Home Assistant configuration directory.
4.  Restart Home Assistant.

## Configuration

1.  In Home Assistant, go to **Settings** > **Devices & Services**.
2.  Click the **+ ADD INTEGRATION** button in the bottom right.
3.  Search for **"LU-Alert"** and click on it.
4.  You will be prompted to select a **minimum severity level**. Alerts below this level will be ignored. Select your desired level and click **Submit**.
5.  To change the severity level later, go to the integration's card on the Devices & Services page and click **"Configure"**.

## Using the Sensors

The integration creates up to 3 devices, one for each of the most important alerts found in the feed. Each device contains a set of sensors, for example:

-   `sensor.lu_alert_1_headline`
-   `sensor.lu_alert_1_severity`
-   `sensor.lu_alert_1_description`
-   `sensor.lu_alert_2_headline`
-   etc.

If fewer than 3 alerts are active (that meet your severity filter), the remaining sets of sensors will have a state of "Not Active" or "No Alert".

### Example Lovelace Card

You can use an `entities` card or a custom `vertical-stack` with `conditional` cards to display the active alerts.

```yaml
type: vertical-stack
cards:
  - type: conditional
    conditions:
      - entity: sensor.lu_alert_1_headline
        state_not: "No Alert"
    card:
      type: entities
      title: LU-Alert 1
      entities:
        - entity: sensor.lu_alert_1_headline
        - entity: sensor.lu_alert_1_severity
        - entity: sensor.lu_alert_1_status
        - entity: sensor.lu_alert_1_description
  - type: conditional
    conditions:
      - entity: sensor.lu_alert_2_headline
        state_not: "No Alert"
    card:
      type: entities
      title: LU-Alert 2
      entities:
        - entity: sensor.lu_alert_2_headline
        - entity: sensor.lu_alert_2_severity
        - entity: sensor.lu_alert_2_status
        - entity: sensor.lu_alert_2_description
```
