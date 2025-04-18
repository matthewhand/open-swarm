# UX utilities for Swarm blueprints (stub for legacy/test compatibility)

class BlueprintUX:
    def __init__(self, style=None):
        self.style = style or "default"
    def box(self, title, content, summary=None, params=None):
        # Minimal ANSI/emoji box for test compatibility
        box = f"\033[1;36m┏━ {title} ━\033[0m\n"
        if params:
            box += f"\033[1;34m┃ Params: {params}\033[0m\n"
        if summary:
            box += f"\033[1;33m┃ {summary}\033[0m\n"
        for line in content.split('\n'):
            box += f"┃ {line}\n"
        box += "┗"+"━"*20
        return box

# Integrate unique improvements from the feature branch
import time
import itertools

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
            "emoji": "🦆",
            "spinner": ['Quacking.', 'Quacking..', 'Quacking...', 'Flapping...'],
            "fallback": 'Quacking... Taking longer than expected',
        }
    else:
        return get_style("serious")

class BlueprintUXImproved:
    def __init__(self, style="serious"):
        self.style = style
        self._style_conf = get_style(style)
        self._spinner_cycle = itertools.cycle(self._style_conf["spinner"])
        self._spinner_start = None

    def spinner(self, state_idx, taking_long=False):
        if taking_long:
            return self._style_conf["fallback"]
        spinner_states = self._style_conf["spinner"]
        return spinner_states[state_idx % len(spinner_states)]

    def summary(self, op_type, result_count, params):
        return f"{op_type} | Results: {result_count} | Params: {params}"

    def progress(self, current, total=None):
        if total:
            return f"Processed {current}/{total} lines..."
        return f"Processed {current} lines..."

    def code_vs_semantic(self, result_type, results):
        if result_type == "code":
            header = "[Code Search Results]"
        elif result_type == "semantic":
            header = "[Semantic Search Results]"
        else:
            header = "[Results]"
        return f"{header}\n" + "\n".join(results)
