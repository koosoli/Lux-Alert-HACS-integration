# Contributing

## Branch workflow

- `development` is the integration and release-candidate branch.
- `master` is the production/release branch.
- Create focused feature/fix branches from `development` and submit pull requests into it.
- Promote only tested code to `master`; do not develop directly on `master`.

The repository initially had only `feat/cap-lu-integration`. The `development` branch was created from it to preserve existing work. Keep the source branch until the maintainer confirms it can be retired.

## Pull requests

Explain the change, link issues, include tests, update documentation/changelog, and pass required checks. Do not merge failing checks without a documented maintainer decision.

## Coding standards

- Follow Home Assistant integration conventions and the existing module structure.
- Use async Home Assistant APIs; never block the event loop.
- Keep parsing/filtering independent from Home Assistant and network I/O where practical.
- Centralize polling in the coordinator.
- Handle timeouts, HTTP failures, malformed JSON/XML and missing CAP fields.
- Preserve stable entity unique IDs after release.
- Keep attributes JSON-safe and respect recorder size limits.
- Treat upstream payloads as untrusted.
- Never log secrets, private coordinates or unnecessary full payloads.
- Add regression tests for fixed defects.

## Required local checks

```bash
python3 -m compileall -q .
python3 -m pytest -q
ruff check custom_components tests
```

Also verify Home Assistant hassfest and HACS validation. Behavior and frontend changes require a manual Home Assistant smoke test.

## Commit messages

Use concise imperative messages, e.g. `Handle malformed CAP area coordinates` or `Add coordinator recovery tests`. Never include credentials or personal data.
