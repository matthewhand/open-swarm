"""One-shot default-LLM helpers: quickstarts and BlueprintBase class drafts."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from swarm.core.blueprint_spec import BLUEPRINT_AGENT_BRIEF, BLUEPRINT_INTERFACE
from swarm.core.model_text import sanitize_model_text

QUICKSTART_KEYS = ("A", "B", "C", "D")


def fallback_quickstarts(name: str) -> list[dict[str, str]]:
    agent = (name or "this agent").strip() or "this agent"
    return [
        {
            "key": "A",
            "label": f"Explain {agent}",
            "prompt": (
                f"Explain who you are as {agent}, how Open Swarm uses you, "
                "and how I should talk to you."
            ),
        },
        {
            "key": "B",
            "label": "Customise experience",
            "prompt": (
                f"Help me customise {agent}: hide extra agents, pick CLI vs API "
                "vs remote, and set a default LLM."
            ),
        },
        {
            "key": "C",
            "label": "Install CLI",
            "prompt": (
                f"Does {agent} need a host CLI (grok/agy)? How do I install and "
                "select it from this sidebar?"
            ),
        },
        {
            "key": "D",
            "label": "Connect remote",
            "prompt": (
                f"How do I connect {agent} to a remote team like Hermes, "
                "OpenMausBot, or DeepSeek Harness?"
            ),
        },
    ]


def parse_quickstarts_payload(text: str, *, name: str = "") -> list[dict[str, str]]:
    """Accept a JSON list or {quickstarts: [...]} from an LLM reply."""
    cleaned = sanitize_model_text(text or "")
    blob = _extract_json(cleaned)
    items: list[Any] = []
    if isinstance(blob, list):
        items = blob
    elif isinstance(blob, dict):
        raw = blob.get("quickstarts") or blob.get("prompts") or blob.get("items")
        if isinstance(raw, list):
            items = raw
    out: list[dict[str, str]] = []
    for idx, item in enumerate(items[:4]):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("title") or "").strip()[:80]
        prompt = str(item.get("prompt") or item.get("text") or "").strip()[:500]
        if not label or not prompt:
            continue
        key = str(item.get("key") or QUICKSTART_KEYS[idx])[:1].upper()
        out.append({"key": key or QUICKSTART_KEYS[idx], "label": label, "prompt": prompt})
    if len(out) == 4:
        return out
    return fallback_quickstarts(name)


def generate_quickstarts(name: str, system_prompt: str) -> list[dict[str, str]]:
    """Rewrite the four onboarding pills for this agent via the default LLM."""
    fallback = fallback_quickstarts(name)
    if os.getenv("PYTEST_CURRENT_TEST") and os.getenv("SWARM_LLM_ASSIST") != "1":
        return fallback
    user = (
        "Rewrite these four onboarding quickstarts for the agent below. "
        "Return ONLY JSON: {\"quickstarts\": [{\"key\":\"A\",\"label\":\"...\",\"prompt\":\"...\"}, ...]}\n"
        "Exactly four items. Labels ≤ 40 chars. Prompts are first-person questions I type to the agent.\n"
        f"Agent name: {name}\n"
        f"System prompt / purpose:\n{system_prompt or '(none)'}\n"
        "Themes to keep, rewritten for this agent: "
        "(A) explain the product/agent, (B) customise the experience, "
        "(C) install/use a CLI, (D) connect a remote like Hermes."
    )
    try:
        text = default_chat(
            [
                {"role": "system", "content": "You write short JSON UI copy. No markdown."},
                {"role": "user", "content": user},
            ],
            max_tokens=700,
        )
    except Exception:
        return fallback
    return parse_quickstarts_payload(text, name=name)


def generate_blueprint_class(
    *,
    name: str,
    description: str,
    requirements: str,
    category: str = "ai_assistants",
    tags: list[str] | None = None,
) -> str | None:
    """Ask the default LLM for a BlueprintBase subclass. None if it cannot."""
    if os.getenv("PYTEST_CURRENT_TEST") and os.getenv("SWARM_LLM_ASSIST") != "1":
        return None
    tag_list = tags or []
    user = (
        f"{BLUEPRINT_AGENT_BRIEF}\n\n"
        "Interface spec (must follow):\n"
        f"{BLUEPRINT_INTERFACE}\n\n"
        "Author a complete Python module for this team. Return ONLY Python "
        "(no markdown fences if possible).\n"
        f"Name: {name}\n"
        f"Description: {description}\n"
        f"Category: {category}\n"
        f"Tags: {', '.join(tag_list)}\n"
        f"Requirements:\n{requirements or '(none)'}\n"
        "Must: subclass ApiKindBase (default) or CliKindBase / RemoteKindBase "
        "(BlueprintBase only if you must), class-level metadata with name/title/"
        "description/version, async def run(self, messages, **kwargs) that yields "
        '{"messages": [{"role": "assistant", "content": "..."}]}. '
        "Use get_llm_profile / AsyncOpenAI if you need a model. No asyncio.run, "
        "no if __name__ == '__main__'."
    )
    try:
        text = default_chat(
            [
                {"role": "system", "content": "You write production Python for Open Swarm blueprints."},
                {"role": "user", "content": user},
            ],
            max_tokens=1800,
        )
    except Exception:
        return None
    code = extract_python(text)
    if not code or "async def run" not in code:
        return None
    if not any(
        name in code
        for name in ("ApiKindBase", "CliKindBase", "RemoteKindBase", "BlueprintBase")
    ):
        return None
    return code


def extract_python(text: str) -> str:
    cleaned = sanitize_model_text(text or "")
    fence = re.search(r"```(?:python)?\s*([\s\S]*?)```", cleaned, re.I)
    if fence:
        cleaned = fence.group(1)
    return cleaned.strip()


def default_chat(
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 800,
    timeout: float = 45.0,
) -> str:
    """Sync chat.completions against the operator default LiteLLM/OpenAI profile."""
    from openai import OpenAI

    from swarm.utils.env_utils import get_llm_base_url

    base_url = get_llm_base_url() or os.getenv("OPENAI_BASE_URL") or ""
    api_key = (
        os.getenv("LITELLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or "ollama"
    )
    model = (
        os.getenv("LITELLM_MODEL")
        or os.getenv("DEFAULT_LLM")
        or os.getenv("OPENAI_MODEL")
        or "auxiliary"
    )
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout}
    if base_url:
        kwargs["base_url"] = base_url
    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.4,
    )
    content = (resp.choices[0].message.content or "") if resp.choices else ""
    return sanitize_model_text(content)


def _extract_json(text: str) -> Any:
    blob = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", blob, re.I)
    if fence:
        blob = fence.group(1).strip()
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        start = blob.find("{")
        start_list = blob.find("[")
        if start_list != -1 and (start == -1 or start_list < start):
            start = start_list
        if start == -1:
            return None
        try:
            return json.loads(blob[start:])
        except json.JSONDecodeError:
            return None
