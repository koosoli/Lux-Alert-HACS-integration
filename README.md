# LU-Alert (Luxembourg) Integration for Home Assistant

This is a custom integration for Home Assistant that provides alerts from the official Luxembourg government's [LU-Alert](https://www.lu-alert.lu/) system.

It fetches data from the public data portal ([data.public.lu](https://data.public.lu/fr/datasets/alertes-du-systeme-lu-alert/)) and presents all active alerts in a single, cohesive sensor. This allows you to build powerful automations and dashboard views based on official government warnings.

This integration is designed to handle multiple simultaneous alerts and allows you to filter them by severity.

## Features

- **Single, Cohesive Sensor**: Provides one sensor, `sensor.lu_alert`, whose state is the number of active alerts. All alert data is stored in a list in the `alerts` attribute.
- **Handles Multiple Alerts**: Correctly parses and displays all active alerts from the feed, not just the first one.
- **Configurable Severity Filtering**: A dropdown menu in the configuration allows you to select the minimum severity of alerts you want to see (e.g., "Moderate" and above).
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

## Using the Sensor

The integration creates one sensor: `sensor.lu_alert`.

-   **State**: The number of active alerts that meet your minimum severity criteria.
-   **Attributes**: A list named `alerts` contains the detailed information for each active alert.

### Example Template for Lovelace

You can use a Markdown card with a template to display the alerts in a user-friendly way, similar to the official website.

```yaml
type: markdown
content: |
  {% set alerts = state_attr('sensor.lu_alert', 'alerts') %}
  {% if alerts %}
    {% for alert in alerts %}
      ## {{ alert.headline }}
      **Severity:** {{ alert.severity }} | **Status:** {{ alert.status }}

      **Sent:** {{ as_timestamp(alert.sent) | timestamp_custom('%d %B %Y at %H:%M') }}

      **Description:**
      {{ alert.description }}

      {% if alert.instruction %}
      **Instruction:**
      {{ alert.instruction }}
      {% endif %}
      ***
    {% endfor %}
  {% else %}
    ## No Active Alerts
    There are currently no active alerts meeting your criteria.
  {% endif %}
title: LU-Alert
```
