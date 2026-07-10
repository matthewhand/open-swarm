"""Permission policy for MoA participants (read-only only)."""

from __future__ import annotations

from swarm.core.moa.types import PermissionMode

# Modes allowed for MoA participant consultations.
PARTICIPANT_PERMISSION_MODES: frozenset[str] = frozenset(
    {
        PermissionMode.APPROVE_READS.value,
        PermissionMode.DENY_ALL.value,
    }
)

DEFAULT_PARTICIPANT_PERMISSION = PermissionMode.APPROVE_READS


class WriteDeniedError(PermissionError):
    """Raised when a write-capable or impactful permission is requested for a participant."""


def _mode_value(permission: PermissionMode | str) -> str:
    if isinstance(permission, PermissionMode):
        return permission.value
    return str(permission)


def assert_participant_permission(permission: PermissionMode | str) -> str:
    """Validate and return a participant permission mode string.

    Raises
    ------
    WriteDeniedError
        If the mode would allow write / impactful auto-approval (e.g. approve-all).
    """
    value = _mode_value(permission)
    if value not in PARTICIPANT_PERMISSION_MODES:
        raise WriteDeniedError(
            f"MoA participants must be read-only; refused permission mode {value!r}. "
            f"Allowed: {sorted(PARTICIPANT_PERMISSION_MODES)}"
        )
    return value


def participant_acpx_flags(
    permission: PermissionMode | str = DEFAULT_PARTICIPANT_PERMISSION,
) -> list[str]:
    """Return acpx CLI flags for a read-only one-shot participant invocation.

    Always includes one-shot ``exec`` semantics via the caller placing ``exec``
    in the command; this helper returns the permission + format flags that must
    appear on the argv list. ``--approve-all`` is never returned.
    """
    mode = assert_participant_permission(permission)
    flags: list[str] = []
    if mode == PermissionMode.APPROVE_READS.value:
        flags.append("--approve-reads")
    elif mode == PermissionMode.DENY_ALL.value:
        flags.append("--deny-all")
    # Marker that callers should use one-shot exec (included for policy tests).
    flags.append("exec")
    return flags
