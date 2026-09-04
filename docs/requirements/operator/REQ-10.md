# REQ-10

Intent: when editing an agent, generate quickstart overrides from its name and system prompt using the default LLM.

Success:
1. Inspector (and empty chat for that agent) can replace the four default pills with agent-specific copy.
2. Generate uses the operator default LLM (LiteLLM profile / LITELLM_MODEL), not a hardcoded OpenAI model.
3. Input is agent display name + purpose/system prompt (plus persona instructions when present).
4. Output is four items: label + prompt, same A–D themes rewritten for this agent.
5. Persist overrides per agent. Reset restores product defaults.
6. If the LLM fails or returns junk, keep/fall back to name-templated defaults. No hang under pytest.

Owner: open-swarm engineer.
