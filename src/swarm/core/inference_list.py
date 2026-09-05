"""REQ-69: per-agent ordered inference list — pick, failover, classify errors."""

from __future__ import annotations

from typing import Any

LLM_PREFIX = "llm:"
CLI_PREFIX = "cli:"
REMOTE_PREFIX = "remote:"


def normalize_inference_list(raw: Any) -> list[str]:
    """Return unique non-empty seat ids, preserving order."""
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, dict):
            kind = str(item.get("kind") or "").strip().lower()
            ident = str(item.get("id") or "").strip()
            if not ident:
                continue
            if kind in {"llm", "cli", "remote"} and not ident.startswith(f"{kind}:"):
                ident = f"{kind}:{ident}"
            text = ident
        else:
            text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def seat_kind(seat: str) -> str:
    text = (seat or "").strip().lower()
    if text.startswith(CLI_PREFIX):
        return "cli"
    if text.startswith(REMOTE_PREFIX):
        return "remote"
    return "llm"


def seat_id(seat: str) -> str:
    text = (seat or "").strip()
    for prefix in (LLM_PREFIX, CLI_PREFIX, REMOTE_PREFIX):
        if text.lower().startswith(prefix):
            return text[len(prefix) :]
    return text


def pick_scale_out(options: list[str], index: int) -> str | None:
    """Round-robin: concurrent scale-out tasks land on different seats."""
    if not options:
        return None
    if index < 0:
        index = 0
    return options[index % len(options)]


def _status_code(exc: BaseException) -> int | None:
    code = getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    if isinstance(code, int):
        return code
    return None


def is_rate_limit(exc: BaseException) -> bool:
    """429 / rate-limit must not auto-failover (REQ-69 v1)."""
    if _status_code(exc) == 429:
        return True
    text = str(exc).lower()
    return "429" in text or "rate limit" in text or "rate_limit" in text


def is_config_failure(exc: BaseException) -> bool:
    """Missing key, bad URL, unknown model, provider 4xx that is not 429."""
    if is_rate_limit(exc):
        return False
    code = _status_code(exc)
    if code in {400, 401, 403, 404}:
        return True
    text = str(exc).lower()
    needles = (
        "api key",
        "apikey",
        "api_key",
        "missing key",
        "invalid api",
        "authentication",
        "unauthorized",
        "unknown model",
        "model not found",
        "does not exist",
        "base_url",
        "connection refused",
        "name or service not known",
        "nodename nor servname",
        "failed to resolve",
        "config",
    )
    return any(n in text for n in needles)


def should_failover(exc: BaseException, remaining: list[str], *, scale_out: bool) -> bool:
    """Walk to the next seat only for config failures on a sequential list."""
    if scale_out or not remaining:
        return False
    return is_config_failure(exc) and not is_rate_limit(exc)


def retry_params(params: dict | None, rest: list[str]) -> dict:
    """Build WS params for the next seat after a config failure."""
    retry = dict(params or {})
    retry["inference_list"] = rest
    if not rest:
        return retry
    nxt = rest[0]
    if seat_kind(nxt) == "cli":
        retry["cli"] = seat_id(nxt)
    elif seat_kind(nxt) == "llm":
        retry["model"] = seat_id(nxt)
        retry["llm_profile"] = seat_id(nxt)
    elif seat_kind(nxt) == "remote":
        retry["remote_id"] = seat_id(nxt)
    return retry


def failover_notice(failed: str, nxt: str | None, *, exhausted: bool = False) -> str:
    if exhausted:
        return f"Inference list exhausted after {failed}. Stopped."
    if nxt:
        return f"Inference {failed} failed (config). Trying {nxt}."
    return f"Inference {failed} failed (config)."
