# hybrid_moa

Hybrid champagne: **MoA consult (read-only)** then **implementer write**.

```bash
# Via API
curl -s localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $SWARM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"hybrid_moa","messages":[{"role":"user","content":"Enable rate limits?"}],
       "params":{"backend":"fake","preset":"ci","workdir":"/tmp/hybrid-demo"}}'
```

See `docs/MOA.md` and `docs/SWARM_WORKFLOWS.md`.
