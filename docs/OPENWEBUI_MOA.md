# Open WebUI / OpenAI client preset for MoA

Point any OpenAI-compatible client (Open WebUI, Continue, curl) at **swarm-api**.

## Connection

| Field | Value |
|-------|--------|
| Base URL | `http://localhost:8000/v1` (or your deployed host) |
| API key | `SWARM_API_KEY` / token configured for the API |
| Model | `moa` (aliases: `mixture_of_agents`, `cli_fusion`, `cli_ensemble`) |
| Hybrid | `hybrid_moa` — MoA consult then write `decision.md` |

## Example request

```bash
curl -s "$OPENAI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "moa",
    "messages": [{"role": "user", "content": "Should we rate-limit the public API?"}],
    "params": {
      "backend": "grok",
      "participants": ["analyst", "critic"]
    }
  }'
```

CI-safe (no live CLI):

```json
"params": {
  "backend": "fake",
  "participants": ["analyst", "critic"],
  "fake_responses": {
    "analyst": "{\"claim\":\"yes token bucket\",\"confidence\":0.9}",
    "critic": "{\"claim\":\"yes with metrics\",\"confidence\":0.85}"
  }
}
```

`system_fingerprint` looks like `moa:analyst+critic`.

## Open WebUI UI steps

1. Admin → Connections → OpenAI → add connection with Base URL + API key above  
2. Enable model **`moa`** (and optionally **`hybrid_moa`**)  
3. In chat advanced/body params, pass `params` as custom body if your Open WebUI build supports it; otherwise configure defaults via `swarm_config.json` `moa` block  

## Config init

```bash
swarm-cli moa-init --write
# or merge into a specific file:
swarm-cli moa-init --config ./swarm_config.json --write
swarm-cli moa-init --show-openwebui   # print connection JSON
```
