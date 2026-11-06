# Architecture

## Data flow

1. The config flow creates one config entry.
2. `LuAlertCoordinator` owns polling, cache state, filters, expiry scheduling and recovery behavior.
3. `Client` retrieves the dataset description and CAP XML over HTTPS with host, redirect and response-size checks.
4. `Feed` selects new/changed resources, downloads concurrently, parses CAP and caches per-resource results.
5. `cap.py` parses CAP messages into plain objects from `model.py`.
6. `alerts.py` applies business rules and produces a normalized snapshot.
7. Sensor and binary-sensor platforms expose the snapshot.
8. The frontend card renders summary and alert attributes; Leaflet is bundled locally.

## Module responsibilities

- `api.py`: secure asynchronous HTTP client.
- `feed.py`: resource selection, concurrency and cache.
- `cap.py`: CAP XML parser.
- `model.py`: plain data structures.
- `alerts.py` / `geo.py`: alert lifecycle, severity, language and geographic rules.
- `coordinator.py`: Home Assistant update lifecycle, backoff, last-known state and expiry callbacks.
- `config_flow.py`: UI configuration.
- `sensor.py`, `binary_sensor.py`, `entity.py`: entity presentation.
- `www/`: dashboard card and bundled map assets.

## Reliability and security

A successful empty feed is not the same as a failed poll. During an outage retain last-known alerts and expose feed connectivity separately. First-refresh failure must fail setup so Home Assistant can retry. Never interpret unavailable data as all-clear.

Remote URLs are untrusted. Preserve HTTPS-only requests, allowed-host and redirect validation, response limits and XML DTD/entity rejection. Feed text must be escaped before insertion into frontend HTML.
