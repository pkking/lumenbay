# Contributing

Lumenbay is being built incrementally. Read [AGENTS.md](AGENTS.md) before opening a PR.

## Local development

Use [mise](https://mise.jdx.dev/) on Windows or Linux. The repository's `mise.toml` selects Python 3.11 and creates the ignored `.venv` automatically.

```sh
mise install
mise exec -- python -m pip install -e ".[dev]"
mise exec -- ruff check .
mise exec -- ruff format --check .
mise exec -- mypy src
mise exec -- pytest
mise exec -- python -m build
```

No `py` launcher or manual virtualenv activation is required. To fix formatting, run `mise exec -- ruff format .`; for lint fixes, `mise exec -- ruff check --fix .`. Do not silently change behavior to satisfy automated checks.

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
