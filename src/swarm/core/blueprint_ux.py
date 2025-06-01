# UX utilities for Swarm blueprints
import time
import itertools
from swarm.core.blueprint_base import BlueprintBase # Import BlueprintBase

# Style presets
def get_style(style):
    if style == "serious":
        return {
            "border_top": "\033[1;34m╔" + "═"*50 + "╗\033[0m",
            "border_bottom": "\033[1;34m╚" + "═"*50 + "╝\033[0m",
            "border_side": "\033[1;34m║\033[0m",
            "emoji": "🛠️",
            "spinner": ['Generating.', 'Generating..', 'Generating...', 'Running...'],
            "fallback": 'Generating... Taking longer than expected',
        }
    elif style == "silly":
        return {
            "border_top": "\033[1;35m(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧" + "~"*40 + "✧ﾟ･: *ヽ(◕ヮ◕ヽ)\033[0m",
            "border_bottom": "\033[1;35m(づ｡◕‿‿◕｡)づ" + "~"*40 + "づ(｡◕‿‿◕｡)づ\033[0m",
            "border_side": "\033[1;35m~\033[0m",
            "emoji": "🦆", # Changed for fun, was 💡
            "spinner": ['Quacking.', 'Quacking..', 'Quacking...', 'Flapping...'],
            "fallback": 'Quacking... Taking longer than expected',
        }
    else: # Default to serious
        return get_style("serious")

class BlueprintUXImproved(BlueprintBase): # Inherit from BlueprintBase
    def __init__(self, blueprint_id: str, config_path=None, style="serious", **kwargs):
        # Initialize BlueprintBase part first
        super().__init__(blueprint_id, config_path=config_path, **kwargs)
        
        # Then initialize BlueprintUXImproved specific attributes
        self.style = style
        self._style_conf = get_style(style)
        self._spinner_cycle = itertools.cycle(self._style_conf["spinner"])
        self._spinner_start = None
        # Ensure console is available, potentially from BlueprintBase or set here
        if not hasattr(self, 'console'):
            from rich.console import Console
            self.console = Console()


    def update_spinner(self, state: str, duration: float) -> str: # Added method for tests
        """Provides spinner state based on duration."""
        if duration > 5.0: # Example threshold
            return self._style_conf.get("fallback", "Generating... Taking longer than expected")
        return state


    def spinner(self, state_idx, taking_long=False):
        if taking_long:
            return self._style_conf["fallback"]
        spinner_states = self._style_conf["spinner"]
        return spinner_states[state_idx % len(spinner_states)]

    def summary(self, op_type, result_count, params):
        param_str = ', '.join(f'{k}={v!r}' for k, v in (params or {}).items()) if params else 'None'
        return f"{op_type} | Results: {result_count} | Params: {param_str}"

    def progress(self, current, total=None):
        if total:
            return f"Processed {current}/{total} lines..."
        return f"Processed {current} lines..."

    def code_vs_semantic(self, result_type, results):
        # ... (implementation as before)
        header = f"[{result_type.capitalize()} Results]"
        divider = "\n" + ("=" * 40) + "\n"
        return f"{header}{divider}" + "\n".join(results)


    def ux_print_operation_box(self, title, content, emoji=None, summary=None, params=None, result_count=None, op_type=None, style=None, color=None, status=None):
        """
        Prints an operation box using the instance's console.
        This replaces the direct call to the static ansi_emoji_box for better testability and instance-specific styling.
        """
        # Use self.ansi_emoji_box or a similar method that uses self.console
        # For simplicity, let's assume self.ansi_emoji_box is available and works with self.console
        # If not, this method would construct the box string and then self.console.print(box_string)
        box_string = self.ansi_emoji_box(
            title=title, content=content, summary=summary, params=params,
            result_count=result_count, op_type=op_type, style=(style or self.style), # Use instance style if not overridden
            color=color, status=status, emoji=emoji
        )
        if hasattr(self, 'console') and self.console:
            self.console.print(box_string)
        else:
            print(box_string) # Fallback if console is not set up


    def ansi_emoji_box(self, title, content, summary=None, params=None, result_count=None, op_type=None, style=None, color=None, status=None, emoji=None):
        style_conf = get_style(style or self.style)
        current_emoji = emoji or style_conf['emoji']
        color_map = {
            "success": "92", "info": "94", "warning": "93", "error": "91", None: "94",
        }
        ansi_color = color_map.get(status, color_map[None])
        
        box_lines = []
        box_lines.append(f"\033[{ansi_color}m" + style_conf["border_top"] + "\033[0m")
        
        header_line = f"\033[{ansi_color}m{style_conf['border_side']} {current_emoji} {title}"
        if op_type: header_line += f" | {op_type}"
        if result_count is not None: header_line += f" | Results: {result_count}"
        box_lines.append(header_line + "\033[0m")

        if params: box_lines.append(f"\033[{ansi_color}m{style_conf['border_side']} Params: {params}\033[0m")
        if summary: box_lines.append(f"\033[{ansi_color}m{style_conf['border_side']} {summary}\033[0m")
        
        content_lines = content.split('\n') if isinstance(content, str) else []
        for line in content_lines:
            box_lines.append(f"\033[{ansi_color}m{style_conf['border_side']} {line}\033[0m")
        
        box_lines.append(f"\033[{ansi_color}m" + style_conf["border_bottom"] + "\033[0m")
        return "\n".join(box_lines)

# Legacy BlueprintUX for compatibility if some tests directly import it
class BlueprintUX(BlueprintUXImproved):
    def __init__(self, style=None): # Does not take blueprint_id
        super().__init__(blueprint_id="ux_legacy_placeholder", style=style or "default") # Provide a placeholder ID

    def box(self, title, content, summary=None, params=None):
        # This is a simplified version for legacy calls, uses the improved ansi_emoji_box
        return self.ansi_emoji_box(title=title, content=content, summary=summary, params=params)
