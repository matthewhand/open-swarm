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
