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

    # Aliases for legacy spinner compat (JeevesSpinner, CodeySpinner, etc. attrs)
    SPINNER_STATES = FRAMES
    LONG_WAIT_MSG = SLOW_FRAME

    def __init__(self, console: Console = None, auto_start: bool = True):
        if console is None:
            console = Console()
        self.console = console
        self._stop_event = threading.Event()
        self._start_time = time.time()
        self._thread = None
        if auto_start:
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
        if self._thread:
            self._thread.join()

    def start(self):
        """Compat no-op or restart (thread already started in init)."""
        # Thread auto starts; support legacy explicit start()
        pass

    def current_spinner_state(self):
        """Legacy compat: return current frame or long wait based on elapsed."""
        if not hasattr(self, '_start_time') or self._start_time is None:
            self._start_time = time.time()
        elapsed = time.time() - self._start_time
        if elapsed > self.SLOW_THRESHOLD:
            return self.SLOW_FRAME
        idx = int((time.time() - self._start_time) / self.INTERVAL) % len(self.FRAMES)
        return self.FRAMES[idx]

    def _manual_spin(self):
        """Legacy alias for _spin step."""
        pass
