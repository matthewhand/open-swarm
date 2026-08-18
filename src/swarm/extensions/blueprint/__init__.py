"""TOMBSTONE / DEPRECATED shim: use ``swarm.core`` instead.

The old import-broken duplicate of the blueprint framework under this path is
gone. This package is a compatibility re-export only (emits
``DeprecationWarning``). Live implementations:

- ``swarm.core.blueprint_base.BlueprintBase``
- ``swarm.core.blueprint_discovery.discover_blueprints``
- ``swarm.core.blueprint_utils.filter_blueprints``
- ``swarm.core.spinner`` / ``swarm.core.slash_commands``

Remove in a future release (ROADMAP.md §2.1 shim sunset). Do not add new
callers or restore deleted ``blueprint_base.py`` internals here.
"""

import warnings

from swarm.core.blueprint_base import BlueprintBase  # noqa: F401
from swarm.core.blueprint_discovery import discover_blueprints  # noqa: F401
from swarm.core.blueprint_utils import filter_blueprints  # noqa: F401
from swarm.utils.context_utils import truncate_message_history  # noqa: F401
from swarm.utils.message_sequence import (  # noqa: F401
    repair_message_payload,
    validate_message_sequence,
)

warnings.warn(
    "swarm.extensions.blueprint is deprecated; "
    "import from swarm.core instead (see ROADMAP.md sunset notes).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "BlueprintBase",
    "discover_blueprints",
    "filter_blueprints",
    "repair_message_payload",
    "validate_message_sequence",
    "truncate_message_history",
]
