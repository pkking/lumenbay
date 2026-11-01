# Agent development contract

Read this file before changing code. Lumenbay archives pictures from authorized WeChat groups to specified QQ group albums. Current status: tooling scaffold only; no live adapters yet.

## What to optimize for
1. **No lost photos:** persist inputs and delivery state before any remote side effect.
2. **No duplicate album entries:** deduplicate per destination; reconcile ambiguous responses before retries.
3. **No silent quality downgrade:** distinguish original, compressed and thumbnail media.
4. **No account compromise or privacy leaks:** never require real accounts or private photos in automated CI.

## Technical boundaries
- Python 3.11+, package under `src/lumenbay/`, tests under `tests/`.
- Keep WeChat transport, NapCat client, SQLite storage and orchestration in separate modules; do not put API calls in domain logic.
- In tests inject fake adapters, clocks and temporary storage. No live WeChat/QQ login, network or desktop UI in default tests.
- Keep configuration and secrets out of git. Do not log message bodies, credentials, private image content, or account cookies.
- Use the NapCat group album API, not QQ chat messages. Treat album creation and remote write verification as separate concerns.
- Unofficial integrations are compatibility-sensitive. Pin or record tested client versions when implementing adapters. Do not claim an adapter is supported without a real check.
- Do not add image transcoding, a web service, LLMs, queues or microservices without a concrete requirement.

## Workflow
1. Inspect relevant code and document the smallest behavioral change.
2. Add or modify tests for success, failure, restart and uncertain remote outcomes as applicable.
3. Run `ruff check .`, `ruff format --check .`, `mypy src`, `pytest`, and `python -m build`.
4. Update README/docs for user-visible behavior or compatibility changes.
5. Open a focused PR with summary, testing evidence, risks and any manual steps. Do not put real QQ/WeChat identifiers, tokens or media in PRs.
6. Do not merge until required CI checks pass. Never bypass failing checks or remove tests just to get green CI.

## Human-only or opt-in steps
- Logging into personal messaging accounts, changing their settings, accepting platform risk, real-group uploads, deleting remote photos, and credential rotation require explicit authorization.
- Integration tests must be opt-in and use a test group/album; CI excludes tests marked `integration`.
- Do not perform live uploads or delete user data as part of scaffolding or unit tests.

See `docs/architecture.md` for the planned delivery state model.
