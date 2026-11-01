## Purpose

<!-- What does this change, and why? -->

## Changes

<!-- Scope and design decisions. Link the issue if applicable. -->

## Validation

- [ ] `ruff check .`
- [ ] `ruff format --check .`
- [ ] `mypy src`
- [ ] `pytest` (offline)
- [ ] `python -m build`

## Safety

- [ ] No real account credentials, group identifiers, photos or private logs
- [ ] No live upload or other external side effect in CI
- [ ] Failure and retry behavior covered by tests, if applicable
- [ ] Adapter compatibility limitations documented, if applicable

## Manual verification (if applicable)

<!-- Use a dedicated test group/album. Never include its secrets. -->
