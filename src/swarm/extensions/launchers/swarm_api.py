"""DEPRECATED shim: use ``swarm.core.swarm_api:main`` (pyproject entry point).

Kept so ``python -m swarm.extensions.launchers.swarm_api`` and old imports
still resolve. Do not add new callers.
"""

from __future__ import annotations

import warnings

from swarm.core.swarm_api import main

warnings.warn(
    "swarm.extensions.launchers.swarm_api is deprecated; "
    "use swarm.core.swarm_api:main (see ROADMAP.md Theme 3 CLI consolidation).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["main"]


if __name__ == "__main__":
    main()
