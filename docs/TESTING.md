# Testing Strategy

## Automated checks

The CI workflow runs the following checks on Python 3.12 and 3.13:

1. Compile the integration and test modules: `python -m compileall -q custom_components tests`.
2. Run the existing pytest suite: `python -m pytest -q`.
3. Run Ruff: `ruff check custom_components tests`.
4. Run Home Assistant hassfest.
5. Run HACS validation for the `integration` category.

The test suite uses mocked Home Assistant services and fixed CAP fixtures; it does not depend on the live LU-Alert service.

## Existing automated coverage

The existing tests cover CAP parsing, alert lifecycle and filtering rules, URL validation and dataset resource handling, polygon/circle geometry, configuration flow, Home Assistant entities and coordinator behavior, frontend card registration, and translations.

Add regression tests when changing behavior. Keep network responses deterministic and never call the live feed from unit tests.

## Manual smoke test

On the test Home Assistant instance, record Core version and commit SHA. Verify installation, first refresh, entities, empty feed, active alert, options update, outage/recovery and card rendering. Record any limitations in release notes.
