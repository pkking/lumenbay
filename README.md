# Lumenbay

Automatically archive photos from WeChat group chats into QQ group albums, with deduplication and reliable syncing.

> **Status: foundation only.** WeChat ingestion and QQ album uploading are not implemented yet. Do not use this repository to archive real chats until the adapters and end-to-end verification are complete.

## Scope

Lumenbay is a small Python application intended to:

1. Observe image messages from explicitly configured WeChat groups.
2. Download original images when available; never label previews as originals.
3. Persist images and message identities before upload; deduplicate by content and destination.
4. Upload images to a configured QQ group album through NapCat's album API.
5. Verify remote writes, retry recoverable failures, and quarantine ambiguous upload results.

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

The installed CLI currently provides `--help` and `--version` only. No sync command exists yet.

See [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), and [docs/architecture.md](docs/architecture.md).

## Security and privacy

Only ingest groups whose members have authorized archiving. Never commit login credentials, chat images, decrypted message databases, logs containing personal data, or QQ/WeChat account artifacts. Use a dedicated test group and test album for manual integration checks. Unofficial client integrations may break after app updates or trigger account restrictions.

## License

Licensed under the [MIT License](LICENSE).
