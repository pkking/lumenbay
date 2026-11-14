# Lumenbay

Archive photos from authorized WeChat group chats into QQ group albums with local deduplication and delivery safeguards.

> **Development preview.** The adapters and local workflow are implemented and covered by offline tests. Real WeChat/QQ versions and actual album persistence remain **unverified**. Use a dedicated authorized test group/album first.

## Scope

Lumenbay is a small Python application intended to:

1. Observe image messages from explicitly configured WeChat groups.
2. Download original images when available; never label previews as originals.
3. Persist images and message identities before upload; deduplicate by content and destination.
4. Upload images to a configured QQ group album through NapCat's album API.
5. Record upload acknowledgements separately from verified writes and quarantine ambiguous results. Remote confirmation is not yet automated.

The first release targets one WeChat group and one existing QQ album on a Windows host. Cross-platform adapters and multi-group routing can follow later.

## Architecture

```text
WeChat desktop -> WeChat adapter -> durable image spool / SQLite
                                         |
                                         v
                              deduplication + delivery state
                                         |
                                         v
                                  NapCat OneBot API
                                         |
                                         v
                                    QQ group album
```

Adapters are isolated behind interfaces and tested with fakes. Ordinary CI must never require live accounts, network access, media, or credentials.

## Development

[mise](https://mise.jdx.dev/) manages **Python 3.11** and creates the local `.venv`; no `py` launcher, separate `python -m venv` step, or PowerShell activation is required.

```sh
mise install
mise exec -- python -m pip install -e ".[dev]"
mise exec -- ruff check .
mise exec -- ruff format --check .
mise exec -- mypy src
mise exec -- pytest
mise exec -- python -m build
mise exec -- lumenbay --version
```

The Python interpreter is selected by the committed [mise.toml](mise.toml). The virtual environment lives in the ignored `.venv/` directory. `mise install` installs the interpreter; the first `mise exec` creates and activates `.venv`. Shell activation (`mise activate`) is optional.

### Authorized Windows test setup

Install mise once (for example, `winget install jdx.mise`), then open a **new PowerShell** in the repository. Use an already signed-in compatible Windows WeChat client. The optional `wxauto4` adapter is installed separately because it requires desktop WeChat and is not used in CI.

```powershell
cd C:\work\lumenbay
mise install
mise exec -- python --version
mise exec -- python -m pip install -e .
mise exec -- python -m pip install wxauto4
Copy-Item config.example.json config.json
# Edit config.json with an authorized test group and pre-created QQ album.
$env:LUMENBAY_NAPCAT_TOKEN = "your-local-napcat-token"
mise exec -- lumenbay status --config config.json
mise exec -- lumenbay run --config config.json --once --execute
```

For continuous polling, run `mise exec -- lumenbay run --config config.json --execute`.

Edit `config.json` with the authorized WeChat test group, QQ test group ID and **pre-created** QQ album name. The local `config.json`, credentials and spool are gitignored. For continuous best-effort polling, omit `--once`. Only `--execute` enables real access and uploads.

**Limitations:** free wxauto4 polls currently visible messages and may miss messages during downtime. It cannot prove the downloaded image is the original; quality is recorded as `unknown`. NapCat currently returns an acknowledgement but no confirmed remote media reference, so successful submissions remain `acknowledged` until separate verification. An inconclusive upload remains `unknown` and is not resent automatically. There is no automated reconciliation, photo deletion or historical backfill.

See [WeChat adapter notes](docs/wechat-adapter.md) and [architecture](docs/architecture.md).

See [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), and [docs/architecture.md](docs/architecture.md).

## Security and privacy

Only ingest groups whose members have authorized archiving. Never commit login credentials, chat images, decrypted message databases, logs containing personal data, or QQ/WeChat account artifacts. Use a dedicated test group and test album for manual integration checks. Unofficial client integrations may break after app updates or trigger account restrictions.

## License

Licensed under the [MIT License](LICENSE).
