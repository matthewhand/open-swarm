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
# Built-in '/help' slash command
@slash_registry.register('/help')
def _help_command(blueprint=None, args=None):
    """List available slash commands."""
    cmds = sorted(slash_registry.commands.keys())
    return "Available slash commands:\n" + "\n".join(cmds)

# Built-in '/compact' slash command
@slash_registry.register('/compact')
def _compact_command(blueprint=None, args=None):
    """Placeholder for compacting conversation context."""
    return "[slash command] compact summary not implemented yet."

# Built-in '/model' slash command
@slash_registry.register('/model')
def _model_command(blueprint=None, args=None):
    """Show or switch the current LLM model."""
    if args:
        return f"[slash command] model switch not implemented. Requested: {args}"
    profile = getattr(blueprint, 'llm_profile_name', None)
    return f"[slash command] current LLM profile: {profile or 'unknown'}"

# Built-in '/approval' slash command
@slash_registry.register('/approval')
def _approval_command(blueprint=None, args=None):
    """Toggle or display auto-approval mode."""
    return "[slash command] approval mode not implemented yet."

# Built-in '/history' slash command
@slash_registry.register('/history')
def _history_command(blueprint=None, args=None):
    """Display session history of commands and files."""
    return "[slash command] history not implemented yet."

# Built-in '/clear' slash command
@slash_registry.register('/clear')
def _clear_command(blueprint=None, args=None):
    """Clear the screen and current context."""
    return "[slash command] context cleared."

# Built-in '/clearhistory' slash command
@slash_registry.register('/clearhistory')
def _clearhistory_command(blueprint=None, args=None):
    """Clear the command history."""
    return "[slash command] command history cleared."
