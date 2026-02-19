import threading
import time

from rich.console import Console
from rich.style import Style
from rich.text import Text


class SwarmSpinner:
    """Spinner for CLI blueprints, producing standard frames."""
    FRAMES = ["Generating.", "Generating..", "Generating...", "Running..."]
    SLOW_FRAME = "Generating... Taking longer than expected"
    INTERVAL = 0.12
    SLOW_THRESHOLD = 10  # seconds

    def __init__(self, console: Console):
        self.console = console
        self._stop_event = threading.Event()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin)
        self._thread.daemon = True
        self._thread.start()

    def _spin(self):
        idx = 0
        while not self._stop_event.is_set():
            elapsed = time.time() - self._start_time
            if elapsed > self.SLOW_THRESHOLD:
                txt = Text(self.SLOW_FRAME, style=Style(color="yellow", bold=True))
            else:
                frame = self.FRAMES[idx % len(self.FRAMES)]
                txt = Text(frame, style=Style(color="cyan", bold=True))
            self.console.print(txt, end="\r", soft_wrap=True, highlight=False)
            time.sleep(self.INTERVAL)
            idx += 1
        # Clear line on stop
        self.console.print(" " * 40, end="\r")

    def stop(self):
        self._stop_event.set()
        self._thread.join()
