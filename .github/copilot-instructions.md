# Lumenbay coding instructions

Follow `AGENTS.md` at the repository root. This repository currently contains only the Python development scaffold, not functioning WeChat/QQ integrations.

Prefer small typed Python modules, pytest with fake adapters, Ruff and mypy. Implement WeChat ingestion and NapCat album uploads behind independent interfaces. Preserve durable, idempotent delivery and explicit original-image status. Never embed credentials, private group media, or real account IDs. No network, desktop automation or personal logins in standard CI.
