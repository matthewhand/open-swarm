"""DEPRECATED shim package: use ``swarm.core`` instead.

This package previously held a stale, import-broken copy of the blueprint
framework (its ``__init__`` failed with a circular import, so nothing could
import it). The live implementations are in ``swarm.core``:

- ``swarm.core.blueprint_base.BlueprintBase``
- ``swarm.core.blueprint_discovery.discover_blueprints``
- ``swarm.core.blueprint_utils.filter_blueprints``
- ``swarm.core.spinner`` / ``swarm.core.slash_commands``

This shim re-exports those symbols for backwards compatibility and will be
removed in a future release (see ROADMAP.md for the sunset plan).
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
