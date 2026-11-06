# Changelog

Notable changes are documented here. Dates use ISO format (YYYY-MM-DD).

## [0.1.0] - 2026-11-06

First stable release of the maintained LU-Alert integration for Home Assistant.

### Added
- Home Assistant config flow for setting up the Luxembourg LU-Alert service.
- CAP feed retrieval and parsing, with filtering and alert data exposed through sensor and binary sensor platforms.
- Alert severity, active-alert, watchlist and allergen-related entities.
- Coordinator-managed updates with caching, expiry handling, retry backoff and last-known-data behavior.
- Lovelace dashboard card served by the integration, including bundled Leaflet assets.
- English and German config-flow translations.
- Three example automation blueprints for allergen, critical and local alerts.
- HACS metadata and repository documentation, contribution, support and security guidance.
- Automated CI checks for Python 3.12 and 3.13, Home Assistant validation and HACS validation.

### Quality and compatibility
- Added automated tests covering API behavior, CAP parsing, alert filtering, geographic handling, translations, config flow, entities, blueprints and card delivery.
- Fixed test-session resolver cleanup to prevent background pycares shutdown threads from leaking during test teardown.
- Verified the release candidate with passing Python 3.12 and 3.13 test workflows, plus Home Assistant and HACS validation.

### Notes
- This is the first maintained 0.1.x release. The integration is intended for Luxembourg LU-Alert data.
- Install and update through HACS using this repository as a custom integration repository.
