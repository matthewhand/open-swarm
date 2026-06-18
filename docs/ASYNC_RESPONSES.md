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

## Cancelling a task

```bash
curl -s -X POST http://10.0.0.36:8000/v1/responses/resp_abc…/cancel
# -> {"status": "cancelled", ...}
```

Cooperative: the worker stops at its next chunk boundary and the record becomes
`cancelled`. A single in-flight CLI call still finishes (or hits its own
timeout) — for multi-step blueprints (fusion/pipeline/planner) cancellation
lands between CLI calls. Idempotent: cancelling a finished task is a no-op that
returns its current status.

## Restart durability

Each queued/in-progress task persists a task spec, so if the server restarts
mid-flight it **resumes** interrupted tasks on startup (re-runs from the stored
input — at-least-once). Terminal tasks are left alone.

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
- **Cancellation** — `POST /v1/responses/{id}/cancel`.
- **Restart durability** — interrupted tasks resume on startup.
- Per-task observability (`execution_ms`, `started_at`).
- Stateful chaining across async tasks (`previous_response_id`).
- Per-request `params` on `/v1/responses` (e.g. `preset`, `cli`).

**Auth:** none by default (warns). Set `API_AUTH_TOKEN` to require a Bearer
token; or, when an external layer (cloud OAuth proxy / API gateway) already gates
access, set `SWARM_ALLOW_NO_AUTH=true` to run unauthenticated in production
(DEBUG=false) with a warning instead of a hard refusal.

**Still missing (next)**
- **TLS** — plain HTTP today (front with a reverse proxy for HTTPS).
- **Hard cancel** — cancellation is cooperative; a single long in-flight CLI call isn't killed mid-call.
- **Cloud** — the CLIs are host-bound (OAuth/file-login); a cloud instance must re-auth them on its host.
- **Durable queue** — resume re-runs from stored input (at-least-once); not an exactly-once persistent job queue.

See [VISION.md](./VISION.md) and [ORCHESTRATION_PATTERNS.md](./ORCHESTRATION_PATTERNS.md) for the blueprints you can task this way.
