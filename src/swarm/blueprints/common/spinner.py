import os
import threading
import time

from rich.console import Console
from rich.style import Style
from rich.text import Text


class SwarmSpinner:
    FRAMES = [
        "Generating.",
        "Generating..",
        "Generating...",
        "Running..."
    ]
    SLOW_FRAME = "Generating... Taking longer than expected"
    INTERVAL = 0.12
    SLOW_THRESHOLD = 10  # seconds

    def __init__(self, enabled: bool = None):
        self._stop_event = threading.Event()
        self._thread = None
        self._start_time = None
        self.console = Console()
        # Feature flag: can be set via env or param
        if enabled is None:
            self.enabled = os.environ.get("SWARM_SPINNER_ENABLED", "1") == "1"
        else:
            self.enabled = enabled

    def start(self):
        if not self.enabled:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        self._start_time = time.time()

    def _spin(self):
        idx = 0
        while not self._stop_event.is_set():
            elapsed = time.time() - self._start_time if self._start_time else 0
            if elapsed > self.SLOW_THRESHOLD:
                txt = Text(self.SLOW_FRAME, style=Style(color="yellow", bold=True))
            else:
                frame = self.FRAMES[idx % len(self.FRAMES)]
                txt = Text(frame, style=Style(color="cyan", bold=True))
            self.console.print(txt, end="\r", soft_wrap=True, highlight=False)
            time.sleep(self.INTERVAL)
            idx += 1
        self.console.print(" " * 40, end="\r")  # Clear line

    def stop(self, final_message="Done!"):
        if not self.enabled:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self.console.print(Text(final_message, style=Style(color="green", bold=True)))
