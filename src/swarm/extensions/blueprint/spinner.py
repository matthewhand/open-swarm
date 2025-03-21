"""
Spinner utility for interactive feedback.
"""

import os
import sys
import time
import threading

class Spinner:
    """Simple terminal spinner for interactive feedback."""
    SPINNER_CHARS = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def __init__(self, interactive: bool):
        self.interactive = interactive
        self.term = os.environ.get("TERM", "dumb")
        self.enabled = interactive and self.term not in ["vt100", "dumb"]
        self.running = False
        self.thread = None
        self.status = ""
        self.index = 0

    def start(self, status: str = "Processing"):
        if not self.enabled or self.running:
            return
        self.status = status
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.enabled or not self.running:
            return
        self.running = False
        if self.thread is not None:
            self.thread.join()
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def _spin(self):
        while self.running:
            char = self.SPINNER_CHARS[self.index % len(self.SPINNER_CHARS)]
            sys.stdout.write(f"\r{char} {self.status}")
            sys.stdout.flush()
            self.index += 1
            time.sleep(0.1)