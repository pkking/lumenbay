# Contributing

Lumenbay is being built incrementally. Read [AGENTS.md](AGENTS.md) before opening a PR.

## Local development

Use Python 3.11 or newer (Windows and Linux are covered by CI).

```sh
python -m venv .venv
# Activate your environment.
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy src
pytest
python -m build
```

To fix formatting locally, run `ruff format .`; to fix lint issues, run `ruff check --fix .`. Do not silently change behavior to satisfy automated checks.

## Pull requests

- Prefer one behavior or infrastructure concern per PR, with focused tests.
- Keep platform adapters behind interfaces and run default unit tests entirely offline.
- Document any platform versions and manual verification needed for new adapters.
- Do not include personal WeChat/QQ account details, session cookies, chat messages or photos.
- Integration tests must be explicitly marked `@pytest.mark.integration` and must never run by default.
- Wait for green CI before merging. Do not bypass required checks.

## Integration test policy

Real client tests require an explicitly authorized test WeChat group and test QQ album. Use a disposable test media fixture and keep credentials in local environment variables, never in issue comments, workflow logs or repository files. The GitHub-hosted CI runners do not perform real uploads.

## License

Contributions are licensed under the [MIT License](LICENSE).
