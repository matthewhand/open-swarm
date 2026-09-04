# REQ-7

Intent: treat Hermes and DeepSeek Harness as first-class remotes, and start DSH with Ollama when it is installed.

Success:
1. Remote catalog includes hermes, openmausbot, rakazo, herdr, and dsh (DeepSeek Harness).
2. Hermes and DSH are choices on the single Remote starter dropdown (not extra sidebar rows).
3. DSH default endpoint is http://127.0.0.1:3080/v1.
4. If Ollama is on PATH and `ollama launch` lists `dsh`, launch via `ollama launch dsh`. Otherwise fall back to `npx @deepseek-ai/dsh web`.
5. Header button on the DSH starter: Launch DSH / ollama launch dsh. First message to DSH also tries launch if :3080 is down.
6. Do not invent TBD Rakazo/OMB ports. Do not spawn launches under pytest.

Owner: open-swarm engineer.
