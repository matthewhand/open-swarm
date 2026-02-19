class AuditLogger:
    """Stub AuditLogger for CLI blueprint compatibility."""
    def __init__(self, enabled=False):
        self.enabled = enabled

    def log(self, message: str, *args, **kwargs):
        if self.enabled:
            print(message.format(*args), **kwargs)
