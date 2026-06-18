# Async tasking — `/v1/responses` background mode

For long-running agent work (real coding, research, multi-CLI consensus), a
synchronous HTTP call would block past sane timeouts. The Responses API supports
**fire-and-forget**: start a task, get a handle immediately, poll for the result.

OpenAI-compatible: add `"background": true` to a `/v1/responses` request.

## Lifecycle

```
POST /v1/responses {background:true}  ->  202  {id: resp_…, status: "queued"}
                                              │  (runs in a worker thread)
GET  /v1/responses/{id}  ->  status: "queued" -> "in_progress" -> "completed" | "failed"
```

- The handle (`resp_<id>`) is durable (file-backed store), survives restarts.
- On completion the record carries `output_text`, `output`, `system_fingerprint`
  (which CLIs answered), `usage`, and `execution_ms` (how long it actually took).
- On failure: `status: "failed"` with an `error` object.
- A completed async result is **chainable** — pass its `id` as
  `previous_response_id` to continue the conversation.
- Sync behavior is unchanged: omit `background` and the call blocks and returns
  the completed response as before.

## How a client (e.g. Grok) uses it

```bash
# 1. Start a task — returns immediately with a handle
curl -s http://10.0.0.36:8000/v1/responses -H "Content-Type: application/json" -d '{
  "model": "cli_fusion",
  "input": "Refactor the auth module and summarize the changes",
  "background": true,
  "params": {"preset": "tri"}
}'
# -> {"id":"resp_abc…","status":"queued", ...}

# 2. Poll until done
curl -s http://10.0.0.36:8000/v1/responses/resp_abc…
# -> {"status":"in_progress", ...}   (keep polling)
# -> {"status":"completed","output_text":"…","system_fingerprint":"cli_fusion:gemini+claude+grok|judge=claude","execution_ms":7893}

# 3. (optional) Continue the thread
curl -s http://10.0.0.36:8000/v1/responses -H "Content-Type: application/json" -d '{
  "model": "cli_fusion", "input": "now write tests for it", "previous_response_id": "resp_abc…"
}'
```

Polling guidance: the response carries `execution_ms` once done, so tune your
poll interval to observed task durations (CLI agent tasks here run ~5–30s; a
heavy multi-CLI fusion or coding task can be longer).

## What's now possible vs still missing

**Now possible**
- Fire-and-forget tasking with a durable handle and `queued → in_progress →
  completed/failed` polling.
- Per-task observability (`execution_ms`, `started_at`).
- Stateful chaining across async tasks (`previous_response_id`).
- Per-request `params` on `/v1/responses` (e.g. `preset`, `cli`).

**Still missing (next)**
- **Auth** — currently none (LAN/DEBUG). Add an API token before exposing beyond a trusted network.
- **TLS** — plain HTTP today.
- **Cancellation** — no `POST /v1/responses/{id}/cancel` yet (DELETE removes the record but doesn't stop a running worker).
- **Cloud** — the CLIs are host-bound (OAuth/file-login); a cloud instance must re-auth them on its host.
- **Worker durability** — in-process daemon threads; a server restart mid-task drops the in-progress run (the record stays at `in_progress`). A persistent queue would survive restarts.

See [VISION.md](./VISION.md) and [ORCHESTRATION_PATTERNS.md](./ORCHESTRATION_PATTERNS.md) for the blueprints you can task this way.
