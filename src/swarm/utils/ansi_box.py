"""DEPRECATED shim: use ``swarm.ux.ansi_box`` instead.

The legacy ``swarm.utils.ansi_box.ansi_box(text, color=..., emoji=..., width=...)``
helper had a single internal caller, which now uses
``swarm.core.output_utils.ansi_box``. This module re-exports the modern
``swarm.ux.ansi_box.ansi_box(title, content, ...)`` for backwards
compatibility and will be removed in a future release (see ROADMAP.md for the
sunset plan). Note the signature differs from the legacy helper.
"""

import warnings

from swarm.ux.ansi_box import ansi_box  # noqa: F401

warnings.warn(
    "swarm.utils.ansi_box is deprecated; "
    "use swarm.ux.ansi_box (or swarm.core.output_utils.ansi_box for a string-returning box) "
    "instead (see ROADMAP.md sunset notes).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ansi_box"]
