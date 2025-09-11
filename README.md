# LU-Alert (Luxembourg) Integration for Home Assistant

This is a custom integration for Home Assistant that provides alerts from the official Luxembourg government's [LU-Alert](https://www.lu-alert.lu/) system.

It fetches data from the public data portal ([data.public.lu](https://data.public.lu/fr/datasets/alertes-du-systeme-lu-alert/)) and presents alerts in a powerful and flexible way, allowing you to build robust automations and dashboard views based on official government warnings.

## Features

- **Main Summary Sensor**: A primary sensor (`sensor.lu_alert`) that provides a count of active alerts and contains all alert details in its attributes.
- **Indexed Sensors for Dashboards**: Simple sensors (`sensor.lu_alert_1`, `sensor.lu_alert_2`, etc.) where the state is the alert's headline, for easy display on dashboards.
- **Critical Alert Binary Sensors**: Dedicated binary sensors (e.g., `binary_sensor.lu_alert_critical_alert_active`) that turn `on` for "Severe" or "Extreme" alerts, perfect for critical automations.
- **Custom Lovelace Card**: A simple card to display the alerts on your dashboard.
- **Single Device**: All entities are grouped under a single "LU-Alert" device to keep your entity list clean.
- **Configurable Severity Filtering**: A dropdown menu in the configuration allows you to select the minimum severity of alerts you want the integration to process.
- **UI-Based Configuration**: No YAML required. Add and configure the integration directly from the Home Assistant UI.
- **Efficient Polling**: Uses a `DataUpdateCoordinator` to fetch data from the source API efficiently.

## Installation

This integration is best installed via the [Home Assistant Community Store (HACS)](https://hacs.xyz/).

1.  Ensure you have HACS installed.
2.  Go to HACS > Integrations > and click the three dots in the top right.
3.  Select "Custom repositories", add `https://github.com/koosoli/Lux-Alert-HACS-integration` as the repository URL, and select "Integration" as the category.
4.  The "LU-Alert" integration will now be available in HACS. Click "Install".
5.  Restart Home Assistant.

## Configuration

1.  In Home Assistant, go to **Settings** > **Devices & Services**.
2.  Click the **+ ADD INTEGRATION** button in the bottom right.
3.  Search for **"LU-Alert"** and click on it.
4.  You will be prompted to select a **minimum severity level**. Alerts below this level will be ignored by the entire integration. Select your desired level and click **Submit**.
5.  To change the severity level later, go to the integration's card on the Devices & Services page and click **"Configure"**.

## Dashboard Card

This integration includes a custom Lovelace card (`lu-alert-card`) to display the alerts in a clean and organized way.

### Automatic Installation (HACS)

If you installed this integration via HACS, the card should be automatically registered with Home Assistant. You should be able to find the "Custom: LU-Alert Card" when you add a new card to your dashboard.

### Manual Installation

If the card is not available automatically, you can register it manually:
1.  Go to **Settings** > **Dashboards**.
2.  Click the three dots (⋮) in the top-right corner and select **Resources**.
3.  Click the **+ ADD RESOURCE** button.
4.  Set the **URL** to `/hacsfiles/lu_alert/lu-alert-card.js`.
5.  Set the **Resource Type** to `JavaScript Module`.
6.  Click **CREATE**.

## Available Entities

The integration provides a set of powerful entities to work with:

### Main Entities
-   **`sensor.lu_alert`**: The main sensor. Its state is the total number of active alerts that match your filter. The attributes contain a full list of all alert data.
-   **`sensor.lu_alert_highest_severity`**: Shows the severity of the most critical active alert (e.g., "Minor", "Severe", or "None").

### Indexed Sensors
For easy display on dashboards, the integration creates sensors for the top alerts:
-   **`sensor.lu_alert_1`**, **`sensor.lu_alert_2`**, etc.
    -   **State**: The headline of the alert.
    -   **Attributes**: All other data for that alert (description, severity, sent time, etc.).
    -   If no alert exists for that index, the state will be "No Alert".

### Binary Sensors for Automation
These are perfect for triggering automations for critical events:
-   **`binary_sensor.lu_alert_critical_alert_active`**: Turns `on` if there is any **Severe** OR **Extreme** alert.
-   **`binary_sensor.lu_alert_severe_alert_active`**: Turns `on` only for **Severe** alerts.
-   **`binary_sensor.lu_alert_extreme_alert_active`**: Turns `on` only for **Extreme** alerts.

## Dashboard Example: Show Only Critical Alerts

This is a powerful and recommended way to configure your dashboard. It will be completely hidden until a "Severe" or "Extreme" alert occurs, at which point it will appear with the alert details.

Set the integration's "Minimum Severity" to "Information" to ensure it is aware of all alerts, then add this card to your dashboard:

```yaml
type: conditional
conditions:
  - entity: binary_sensor.lu_alert_critical_alert_active
    state: 'on'
card:
  type: entities
  title: 🚨 CRITICAL ALERT 🚨
  entities:
    - sensor.lu_alert_1
    - sensor.lu_alert_2
    - sensor.lu_alert_3
```
