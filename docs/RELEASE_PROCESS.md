# Release Process

## Release model

- Feature/fix branches merge into `development`.
- Promote tested code to `master` using a non-fast-forward merge.
- Use annotated tags without a leading v, e.g. `0.1.0`.
- Publish only after all checks and manual smoke tests pass.

## Checklist

- [ ] Intended changes merged into development.
- [ ] Changelog and README match implementation.
- [ ] Integration manifest version matches tag.
- [ ] `python3 -m compileall -q .` passes.
- [ ] `python3 -m pytest -q` passes.
- [ ] `ruff check custom_components tests` passes.
- [ ] Home Assistant hassfest passes.
- [ ] HACS validation passes.
- [ ] Manual smoke test passes on rpi4office.
- [ ] No secrets/local files staged.
- [ ] Known limitations documented.
- [ ] Working tree clean.

## Promote and tag

Inspect branch state first; never force-push or rewrite history.

```bash
git fetch --all --tags
git switch development
git pull --ff-only origin development
# Run checks and review changes.
git switch master
git pull --ff-only origin master
git merge --no-ff development -m "Release 0.1.0"
# Run checks again on the merge result.
git tag -a 0.1.0 -m "Release 0.1.0"
git push origin master
git push origin 0.1.0
git show --no-patch --decorate 0.1.0
```

If master does not exist, create it from the approved development commit after reviewing the current refs. Do not guess an unrelated base.

## After release

Verify tag and GitHub Release, confirm HACS detects it, install on the test instance, then deploy to production. Start the next cycle with an Unreleased changelog section.
