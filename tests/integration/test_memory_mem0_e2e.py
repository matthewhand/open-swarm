"""End-to-end validation of the mem0 memory backend (ROADMAP 3.2).

Unlike tests/unit/test_memory_integration.py (which uses a fake backend),
this exercises the real ``mem0ai`` package in-process through BlueprintBase's
memory seam: store on run, then retrieve on a later run.

The mem0 instance runs fully locally except for OpenAI calls:
  - vector store: qdrant in embedded/local mode, on disk under ``tmp_path``
  - history db:   sqlite under ``tmp_path``
  - LLM + embedder: mem0's defaults (OpenAI) — used for fact extraction and
    embeddings, which is why a real ``OPENAI_API_KEY`` is required.

Opt-in by design so CI stays deterministic and keyless: the test is SKIPPED
unless BOTH ``RUN_MEM0_E2E=1`` and ``OPENAI_API_KEY`` are set, e.g.::

    RUN_MEM0_E2E=1 OPENAI_API_KEY=sk-... uv run pytest tests/integration/test_memory_mem0_e2e.py

Status (2026-06-11, mem0ai 2.0.4): the harness was executed locally with
``RUN_MEM0_E2E=1`` — mem0 initialized from this config (local qdrant created
under ``tmp_path``, blueprint seam wrapped run()) and the store cycle reached
OpenAI's embeddings endpoint, which returned 401 because the only available
``OPENAI_API_KEY`` (repo ``.env``) is revoked. mem0's local mode itself runs;
a full green pass just needs a valid key. Re-run with the command above once
one is available.
"""

import os

import pytest

from swarm.core.blueprint_base import BlueprintBase

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_MEM0_E2E") != "1" or not os.environ.get("OPENAI_API_KEY"),
        reason="mem0 e2e is opt-in: set RUN_MEM0_E2E=1 and a real OPENAI_API_KEY",
    ),
    # Real network calls (OpenAI extraction + embeddings); generous budget.
    pytest.mark.timeout(300),
]

USER_ID = "mem0-e2e-user"
FACT = "My favorite beverage is green tea."


class EchoBlueprint(BlueprintBase):
    """Minimal concrete blueprint that records the messages run() receives."""

    def __init__(self, *args, **kwargs):
        self.seen_messages = None
        super().__init__(*args, **kwargs)

    async def run(self, messages, **kwargs):
        self.seen_messages = messages
        yield {"messages": [{"role": "assistant", "content": "Noted: your favorite beverage is green tea."}]}

    @property
    def metadata(self):
        return {"title": "Mem0 E2E Echo", "description": "e2e test blueprint"}


def make_blueprint(tmp_path):
    """Blueprint configured with a real, local-mode mem0 backend."""
    pytest.importorskip("mem0", reason="mem0ai not installed (pip install open-swarm[memory])")
    mem0_config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "swarm_mem0_e2e",
                "path": str(tmp_path / "qdrant"),
                "on_disk": True,
                "embedding_model_dims": 1536,
            },
        },
        "history_db_path": str(tmp_path / "history.db"),
    }
    cfg = {
        "llm": {"default": {"provider": "openai", "model": "gpt-mock", "api_key": "unused"}},
        "settings": {"default_llm_profile": "default", "default_markdown_output": True},
        "blueprints": {},
        "memory": {"backend": "mem0", "user_id": USER_ID, "config": mem0_config},
    }
    return EchoBlueprint("mem0_e2e_bp", config=cfg)


async def test_mem0_store_and_retrieve_through_blueprint_seam(tmp_path):
    bp = make_blueprint(tmp_path)
    # A real Mem0Memory must be attached — silent degradation would make this
    # test pass vacuously, so fail loudly instead.
    assert bp.memory_backend is not None, "mem0 backend failed to initialize (see warning logs)"
    assert type(bp.memory_backend).__name__ == "Mem0Memory"

    # --- Run 1: state a fact; the wrapped run() stores the conversation. ---
    first = [{"role": "user", "content": f"Please remember this: {FACT}"}]
    chunks = [chunk async for chunk in bp.run(first)]
    assert chunks, "wrapped run() yielded nothing"

    # --- Direct retrieval through the backend: the fact must surface. ---
    snippets = bp.memory_backend.search("What is my favorite beverage?", user_id=USER_ID)
    assert snippets, "mem0 returned no memories after a store cycle"
    assert any("green tea" in s.lower() for s in snippets), (
        f"stored fact not surfaced by mem0 search; got: {snippets!r}"
    )

    # --- Run 2: the seam injects retrieved memories as a system message. ---
    second = [{"role": "user", "content": "What is my favorite beverage?"}]
    [chunk async for chunk in bp.run(second)]
    injected = bp.seen_messages[0]
    assert injected["role"] == "system"
    assert "Relevant memories" in injected["content"]
    assert "green tea" in injected["content"].lower()
    # Original user message preserved after the injected context.
    assert bp.seen_messages[1:] == second
