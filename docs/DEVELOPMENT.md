# Development

## Environment

```bash
git clone git@github.com:janreimen/Lux-Alert-HACS-integration.git
cd Lux-Alert-HACS-integration
git switch development
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements_test.txt
```

## Branch model

- `development`: integration work and release candidates.
- `master`: production-ready releases.
- Feature/fix branches: short-lived branches created from development and merged by PR.

The initial source branch was `feat/cap-lu-integration`; development was created from it to preserve existing work. Do not delete the source branch until the maintainer confirms it is no longer needed.

## Local validation

```bash
git status --short
git switch development
git pull --ff-only origin development
python3 -m compileall -q .
python3 -m pytest -q
ruff check custom_components tests
git diff --check
```

Develop and manually test on the dedicated Home Assistant test instance (`rpi4office`). Deploy to production only after validation and a recovery plan. Do not use production as the first test target.

## Secrets and hygiene

Never commit .env files, Home Assistant runtime files, databases, private configuration, tokens or credentials. Review git status and git diff before every commit.
