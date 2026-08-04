"""DEPRECATED shim: use ``swarm.core.spinner`` instead.

The legacy ``swarm.ux.spinner.Spinner`` (base_message/set_message API) had no
production importers and has been retired in favour of the canonical
``swarm.core.spinner.Spinner``. This module re-exports the core spinner for
backwards compatibility and will be removed in a future release (see
ROADMAP.md for the sunset plan).
"""

import warnings

from swarm.core.spinner import Spinner, SwarmSpinner  # noqa: F401

warnings.warn(
    "swarm.ux.spinner is deprecated; "
    "import Spinner from swarm.core.spinner instead (see ROADMAP.md sunset notes).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["Spinner", "SwarmSpinner"]
