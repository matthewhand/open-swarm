# REQ-11

Intent: blueprint create/generate is agent-assisted Python: a `BlueprintBase` subclass that matches the published interface spec, not a silent stub.

Success:
1. `swarm.core.blueprint_spec` is the interface: class-level `metadata` (name/title/description/version) and `async def run(self, messages, **kwargs)` yielding `{"messages": [{"role": "assistant", "content": "..."}]}` chunks.
2. Blueprint Creator (`/blueprint-library/creator/`) and Agent Creator generate (`/agent-creator/generate/`) call the default LLM with `BLUEPRINT_AGENT_BRIEF` + `BLUEPRINT_INTERFACE` plus the author’s name, description, and requirements.
3. Creator pages show that spec so humans and the model share the same contract.
4. `BlueprintCodeValidator` accepts spec-shaped modules (subclass `BlueprintBase`, async `run`). Typing imports (`AsyncGenerator`, `Any`) are optional. Annotated `metadata: ClassVar[...]` counts.
5. If the LLM draft fails syntax/structure validation, keep the known-good AsyncOpenAI streaming template so create never stores invalid Python. Template `run()` still includes the author’s requirements in the system prompt.
6. Do not invent a different base class. Do not `asyncio.run` / `if __name__ == "__main__"` in generated modules. Do not exec untrusted LLM code on save (AST + sandbox only).

Constraints: Under pytest, LLM assist is off unless `SWARM_LLM_ASSIST=1`. Live LiteLLM is optional; template fallback must always work.

Owner: open-swarm engineer.
