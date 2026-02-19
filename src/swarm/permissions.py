"""
Backwards-compatible permission module.

Some tests and external callers import HasValidTokenOrSession from
`swarm.permissions`. The canonical implementation lives in `swarm.auth`.
Re-export here to maintain compatibility.
"""
from .auth import HasValidTokenOrSession  # noqa: F401

