# Minimal slash_commands.py to restore compatibility

class SlashCommandRegistry:
    def __init__(self):
        self.commands = {}
    def register(self, command, func=None):
        if func is None:
            def decorator(f):
                self.commands[command] = f
                return f
            return decorator
        self.commands[command] = func
        return func
    def get(self, command):
        return self.commands.get(command)

slash_registry = SlashCommandRegistry()
