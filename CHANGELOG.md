# Changelog

## [2.1.1] - 2026-02-14

### Changed
- Improved resilience of alert fetching with concurrency control (semaphore).
- Increased fetch limit to 100 most recent resources to ensure all active alerts are captured.
- Refined severity detection to support a broader range of CAP-LU parameter names.
- Fixed potential sorting issues with offset-naive and offset-aware datetimes.
- Enhanced debug logging for easier troubleshooting.

## [2.1.0] - 2026-02-11 (Reverted)

### Added
- New deduplication logic to handle alert updates and cancellations correctly.
- Support for `cb-eu-level` severity parameter used in recent alerts.

### Changed
- Optimized API fetching by limiting to the 50 most recent alerts to prevent timeouts.
- Migrated to using a shared `aiohttp` session for improved performance.
- Updated minimum Home Assistant version requirements.
