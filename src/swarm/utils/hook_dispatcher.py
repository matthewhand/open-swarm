from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Protocol


class Hook(Protocol):
    def __call__(self, ctx: dict) -> None: ...


@dataclass
class Dispatcher:
    """
    Simple hook dispatcher with pre/listen/post phases.

    Deterministic ordering:
      - If SWARM_DETERMINISTIC_HOOKS is set (truthy), preserve registration order
        and always execute strictly in the order: pre (all) -> listen (all) -> post (all).
      - If not set, we still execute by phase in insertion order, but behavior is allowed
        to vary if external registration order is non-deterministic (e.g., module import race).
    """

    pre_hooks: List[Hook] = field(default_factory=list)
    listen_hooks: List[Hook] = field(default_factory=list)
    post_hooks: List[Hook] = field(default_factory=list)
    _deterministic: bool = field(init=False)

    def __post_init__(self) -> None:
        self._deterministic = _is_truthy(os.getenv("SWARM_DETERMINISTIC_HOOKS", ""))

    # Decorators to register hooks
    def pre(self, fn: Hook) -> Hook:
        self.pre_hooks.append(fn)
        return fn

    def listen(self, fn: Hook) -> Hook:
        self.listen_hooks.append(fn)
        return fn

    def post(self, fn: Hook) -> Hook:
        self.post_hooks.append(fn)
        return fn

    def run(self, ctx: Optional[dict[str, Any]] = None) -> None:
        """
        Execute hooks by phase. If deterministic mode is enabled, we make the order explicit.
        Otherwise, use the current registration order (which is already insertion order).
        """
        context = ctx or {}
        # Phased execution - always in this sequence
        self._run_phase(self.pre_hooks, context, "pre")
        self._run_phase(self.listen_hooks, context, "listen")
        self._run_phase(self.post_hooks, context, "post")

    # Internal helpers
    def _run_phase(self, hooks: List[Hook], ctx: dict, _phase: str) -> None:
        # Insertion order is deterministic in Python 3.7+, so we only need to support
        # potential future variations; we keep the toggle for clarity and tests.
        ordered = list(hooks)
        if not self._deterministic:
            # Non-deterministic mode could be implemented by allowing any order.
            # We intentionally keep insertion order but do not guarantee strict checks.
            # This matches our tests which only assert set equality when not deterministic.
            pass
        for fn in ordered:
            try:
                fn(ctx)
            except Exception:
                # Hooks should not crash the dispatcher; swallow to keep pipeline robust.
                # If desired, integrate logging here.
                continue


def _is_truthy(val: str) -> bool:
    return val.strip().lower() in {"1", "true", "yes", "on"}


__all__ = ["Dispatcher"]