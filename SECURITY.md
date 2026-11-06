# Security Policy

## Supported versions

| Version | Security support |
|---|---|
| 0.1.x | Current maintained release line, subject to maintainer availability |
| Development snapshots | No support guarantee |

## Reporting a vulnerability

Do not report exploitable vulnerabilities in public issues. Use GitHub's **Report a vulnerability** feature in the repository Security tab. If private reporting is unavailable, contact the maintainer privately through their GitHub profile.

Include affected version, impact, safe reproduction steps and suggested mitigation. Do not include credentials, private URLs or personal data.

## Security expectations

- Treat dataset entries and CAP documents as untrusted.
- Preserve HTTPS-only requests, allowed-host validation, redirect validation and response-size limits.
- Do not disable TLS verification.
- Avoid logging full alert payloads or private location data.
- Keep bundled third-party frontend libraries and their license notices up to date.
