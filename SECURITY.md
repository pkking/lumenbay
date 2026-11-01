# Security policy

Lumenbay uses unofficial messaging automation interfaces. Account restrictions, client incompatibility and exposure of personal media are material risks.

## Report vulnerabilities

Please report security-sensitive findings privately using the repository's GitHub security advisory flow when available; do not post credentials, tokens, decrypted chat databases or private photos in a public issue.

## Secrets and privacy

- Keep QQ/WeChat authentication tokens, cookies and local account databases outside the repository.
- Never run live-account integration tests in public GitHub Actions.
- Use explicit authorization for every source group and destination album.
- Sanitize logs, test fixtures, crashes and issue attachments. Do not expose personal identifiers or image contents.
- Use a dedicated test group and test album before enabling real archival.
- Do not auto-delete locally retained media on a failed or ambiguous remote upload.
