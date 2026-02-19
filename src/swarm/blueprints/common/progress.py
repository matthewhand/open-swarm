
from swarm.core.output_utils import get_spinner_state, print_search_progress_box


class ProgressRenderer:
    """Renders progress boxes with consistent styling across blueprints."""

    def __init__(
        self,
        default_emoji: str = "✨",
        default_border: str = "╔",
        default_spinner_states: list[str] | None = None
    ):
        self.default_emoji = default_emoji
        self.default_border = default_border
        self.default_spinner_states = default_spinner_states or [
            "Generating.", "Generating..", "Generating...", "Running..."
        ]

    def render_progress_box(
        self,
        op_type: str,
        results: list[str],
        summary: str,
        search_mode: str | None = None,
        emoji: str | None = None,
        border: str | None = None,
        spinner_state: str | float | None = None,
        total_lines: int | None = None
    ) -> None:
        """Render a standardized progress box with optional customizations."""
        if isinstance(spinner_state, float):
            spinner_state = get_spinner_state(spinner_state)
        print_search_progress_box(
            op_type=op_type,
            results=results,
            params=None,
            result_type="operation",
            summary=summary,
            progress_line=None,
            spinner_state=spinner_state or self.default_spinner_states[0],
            operation_type=op_type,
            search_mode=search_mode,
            total_lines=total_lines,
            emoji=emoji or self.default_emoji,
            border=border or self.default_border
        )

