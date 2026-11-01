# Architecture and delivery semantics (planned)

**Current implementation:** only package skeleton, CLI and offline checks are implemented. The following is a design contract, not a statement of working features.

## MVP boundaries

One authorized WeChat group -> one pre-created QQ group album. Only images; originals preferred. No automatic remote album creation, history backfill, video, multi-group routing or background web service in MVP.

| Component | Responsibility |
| --- | --- |
| WeChat adapter | Discover image messages and download media; explicitly indicate original vs fallback vs missing |
| Durable spool | Retain downloaded bytes and metadata until verified or safely quarantined |
| SQLite repository | Store identity, destination, hash, state and retry metadata; enforce deduplication constraints |
| Delivery service | Coordinate state transitions, retries and remote reconciliation |
| NapCat adapter | Resolve album IDs, call album upload API and query remote album media |

## Identity and idempotency

Track source identity (`source_group`, `message_id`) to avoid reprocessing one event. Track content identity (`destination_group`, `destination_album`, `sha256`) to avoid uploading identical bytes twice to the same destination. Do not globally deduplicate across distinct target albums.

## Delivery state

```text
DISCOVERED -> DOWNLOADED -> UPLOADING -> VERIFIED
                |               |
                v               v
              FAILED          UNKNOWN
                ^               |
                |               v
                +-- retry only after remote reconciliation
```

- Write durable metadata and retain the local image **before** calling NapCat.
- `VERIFIED` means a remote read or other reliable confirmation proved persistence, not merely that the HTTP request returned 200.
- If the upload times out or the response is inconclusive, mark `UNKNOWN` and reconcile before another upload. Never blindly resend uncertain deliveries.
- Do not call a thumbnail an original; surface the actual media quality in state.
- Preserve unknown/failed media for human inspection until an explicit retention policy exists.
- Initial delivery may be at-least-once at the transport layer; prevent logical duplicates by reconciliation and destination-scoped deduplication.

## Test strategy

Default unit tests use fake WeChat and NapCat clients, temporary paths and an in-memory or temporary SQLite database. Cover: duplicate events, same image from different messages, restart replay, network errors before/after remote commit, missing originals, no hardcoded identifiers, and no credential output. Real-platform integration tests are opt-in and use a dedicated authorized group and test album.

## Deployment

Initial target is Windows with desktop WeChat. NapCat can run on the same host or separately. A local path on Windows is not automatically readable from a separate NapCat container; prefer controlled media transfer rather than assuming shared filesystems. No login automation or remote account setup in CI.
