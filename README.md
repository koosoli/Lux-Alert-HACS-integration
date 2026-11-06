# LU-Alert — Home Assistant integration

[![Tests](https://github.com/janreimen/Lux-Alert-HACS-integration/actions/workflows/tests.yml/badge.svg)](https://github.com/janreimen/Lux-Alert-HACS-integration/actions/workflows/tests.yml)
[![Validation](https://github.com/janreimen/Lux-Alert-HACS-integration/actions/workflows/validate.yml/badge.svg)](https://github.com/janreimen/Lux-Alert-HACS-integration/actions/workflows/validate.yml)

A Home Assistant custom integration for official Luxembourg LU-Alert warnings, using the public dataset published by [data.public.lu](https://data.public.lu/).

## Release target

**0.1.0** — initial maintained release line. Publish only after the release checks and manual smoke tests pass.

## Features

- Retrieves CAP alert files from the LU-Alert public dataset.
- Parses CAP messages, severity levels, language blocks, references, expiry times and geographic areas.
- Supports minimum severity, language, test-message, location, watchlist keyword and allergen options.
- Exposes summary, highest-severity and indexed alert sensors.
- Exposes binary sensors for Extreme, Severe, Critical, Local, Watchlist, Allergen and feed connectivity states.
- Uses a Home Assistant `DataUpdateCoordinator`, caches downloaded resources and retains last-known alerts during feed outages.
- Includes a Lovelace alert card with optional area maps.

This integration is not an emergency-notification guarantee. Continue to use official warning channels and follow emergency-service instructions.

## HACS installation

1. Open HACS → Integrations.
2. Add `https://github.com/janreimen/Lux-Alert-HACS-integration` as a custom repository if needed.
3. Select **Integration**, install **LU-Alert**, then restart Home Assistant.
4. Go to Settings → Devices & services → Add integration → **LU-Alert**.

## Manual installation

Copy `custom_components/lu_alert` into your Home Assistant `custom_components` directory and restart.

## Configuration

Add the integration through the UI. Select the minimum severity during setup. Further options are available from the integration's **Configure** action:

- Preferred language.
- Location filter: Off, flag local alerts, or only show local alerts.
- Optional latitude and longitude override (both or neither).
- Watchlist keywords separated by commas, semicolons or newlines.
- Allergen terms.
- Whether to show test/exercise alerts.

## Entities

The integration creates one LU-Alert device. Main sensors include `sensor.lu_alert`, `sensor.lu_alert_highest_severity` and indexed alert sensors `sensor.lu_alert_1` to `sensor.lu_alert_3`.

Binary sensors cover Extreme, Severe, Critical, Local, Watchlist, Allergen and feed connection states. Entity IDs can be customised by Home Assistant's entity registry; verify actual IDs under Settings → Devices & services → Entities.

## Lovelace card

The integration serves frontend assets from `/lu_alert_static/` and registers the card through its frontend setup. See `custom_components/lu_alert/www/lu-alert-card.js` for the current configuration options. After upgrades, restart Home Assistant and refresh the browser cache before adding any manual resource; avoid duplicate resource registrations.

## Data and privacy

The integration reads public data from data.public.lu. Its HTTP client enforces HTTPS, allowed-host and redirect validation, and response-size limits. No API credentials are required. Home Assistant coordinates are used only when location filtering is configured.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md), [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), [docs/TESTING.md](docs/TESTING.md) and [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md).

```bash
python3 -m pip install -r requirements_test.txt
python3 -m compileall -q .
python3 -m pytest -q
ruff check custom_components tests
```

## Support and security

Use GitHub issue templates for bugs and feature requests. Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md). This community integration is not an official Luxembourg government support channel.

## License

The repository does not currently declare a license. Do not assume redistribution or relicensing rights until the maintainer adds one.
