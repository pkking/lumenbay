# WeChat desktop adapter

The optional `WxAutoImageSource` in `lumenbay.wechat` uses the `wxauto4` free
interface on Windows. It connects only to an already signed-in WeChat desktop
client. Supported functions: `ChatWith`, `ChatInfo`, `GetAllMessage`, and
`msg.download(original=True)`. No login or historical backfill is attempted.

## Dependencies and compatibility

- Install `wxauto4` explicitly on a compatible Windows machine, not in CI.
- Official wxauto documentation (checked October 2026) specifies Python
  3.9-3.12 for the free package and WeChat through 4.1.8.107.
- Live compatibility with any particular client version is **not yet tested
  by Lumenbay**.
- Supply an explicitly authorized group name; the active chat is checked
  before reading image messages.

## Limitations

1. `GetAllMessage` reads the visible/current conversation list and **is not
   reliable catch-up after prolonged downtime**. A different message source
   with stable IDs or a controlled backlog is required for guaranteed capture.
2. wxauto UI runtime IDs may change. An exposed `hash` is preferred; SHA256
   of downloaded bytes will be used as the final destination deduplication key.
3. Calling `download(original=True)` does not independently prove the
   returned file is the original. Events are marked `quality=unknown` until
   media provenance can be established; no silent promotion to `original`.
4. If a download fails, the adapter raises an error. It does not silently
   substitute a thumbnail or invent a file path.
5. To avoid unnecessary repeated UI download calls, pass a `seen` predicate.
   Durable source-event tracking will be integrated in a subsequent PR.

Keep real account credentials and group photos out of repository issues,
fixtures and CI logs.
