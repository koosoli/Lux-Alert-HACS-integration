# Testing Strategy

## Automated checks

1. Syntax/bytecode: `python3 -m compileall -q .`
2. Test suite: `python3 -m pytest -q`
3. Lint: `ruff check custom_components tests`
4. Home Assistant metadata: hassfest.
5. HACS repository validation.

Automated tests must not depend on the live LU-Alert service. Mock HTTP responses and use fixed CAP fixtures.

## Existing test areas

Preserve existing tests for CAP parsing, severity and alert rules, HTTP client security, configuration/options flow and entities. Extend tests whenever behavior changes.

## Required regression scenarios

- Dataset success, empty resources and conditional/cache behavior.
- Network timeout, HTTP error, malformed JSON, invalid redirect and oversized response.
- Valid CAP, malformed XML, DTD/entity rejection and missing optional fields.
- Alert update/cancel/reference handling, duplicate messages and expiry.
- Severity thresholds, unknown severity/level and test/exercise filtering.
- Language/channel selection.
- Location polygon/circle matching, no geometry and invalid coordinates.
- Watchlist/allergen matching, empty values and case handling.
- Coordinator first-refresh failure, outage retaining last-known alerts, backoff and recovery.
- Config flow duplicate entry, options validation and reload.
- Entity unique IDs, state/attributes, binary sensor transitions and feed diagnostics.
- Frontend registration, card loading, safe rendering and map behavior.

## Manual smoke test

On the test Home Assistant instance, record Core version and commit SHA. Verify install, first refresh, entities, empty feed, active alert, options update, outage/recovery and card rendering. Record limitations in release notes.
