# Changelog

## [2.1.0] - 2026-02-11

### Fixed
- Fixed integration stopping working due to timeouts when fetching a large number of historical alert files.
- Improved data fetching efficiency by limiting requests to the most recent 50 alert resources.
- Optimized network usage by using Home Assistant's shared aiohttp session.

### Added
- Added support for additional severity parameter names (`cb-eu-level`, `cb-lu-level`) for better compatibility.
- Added more robust error handling and logging during the update process.
