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

Requires Python 3.11+.

```sh
python -m venv .venv
# Activate .venv, then:
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy src
pytest
python -m build
lumenbay --version
```

### Authorized Windows test setup

Use a supported Windows desktop WeChat client with **Python 3.11 or 3.12** and an already logged-in account; the free `wxauto4` dependency is installed separately:

```powershell
python -m pip install -e ".[dev]"
python -m pip install wxauto4
Copy-Item config.example.json config.json
$env:LUMENBAY_NAPCAT_TOKEN="your-local-napcat-token"
lumenbay status --config config.json
lumenbay run --config config.json --once --execute
```

Edit `config.json` with the authorized WeChat test group, QQ test group ID and **pre-created** QQ album name. The local `config.json`, credentials and spool are gitignored. For continuous best-effort polling, omit `--once`. Only `--execute` enables real access and uploads.

**Limitations:** free wxauto4 polls currently visible messages and may miss messages during downtime. It cannot prove the downloaded image is the original; quality is recorded as `unknown`. NapCat currently returns an acknowledgement but no confirmed remote media reference, so successful submissions remain `acknowledged` until separate verification. An inconclusive upload remains `unknown` and is not resent automatically. There is no automated reconciliation, photo deletion or historical backfill.

See [WeChat adapter notes](docs/wechat-adapter.md) and [architecture](docs/architecture.md).

See [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), and [docs/architecture.md](docs/architecture.md).

## Security and privacy

Only ingest groups whose members have authorized archiving. Never commit login credentials, chat images, decrypted message databases, logs containing personal data, or QQ/WeChat account artifacts. Use a dedicated test group and test album for manual integration checks. Unofficial client integrations may break after app updates or trigger account restrictions.

## License

Licensed under the [MIT License](LICENSE).
