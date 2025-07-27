import itertools
import sys
import threading
import time

from rich.console import Console
from rich.text import Text


class GeeseSpinner:
    """
    A simple CLI spinner for the Geese blueprint, using Rich Console.
    """
    def __init__(self, console: Console, message: str = "Working...", interval: float = 0.15):
        self.console = console
        self.message = message
        self.interval = interval
        self._spinner_cycle = itertools.cycle(['🦢', '🦆', '🐣', '🐥']) # Geese-themed!
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None # Type hint uses Optional
        self._live_display = None

    def _spin(self):
        """Internal method to update the spinner display."""
        with self.console.screen() as screen:
            while not self._stop_event.is_set():
                char = next(self._spinner_cycle)
                text = Text.assemble(
                    (f"{char} ", "bold magenta"),
                    (self.message, "cyan")
                )
                sys.stdout.write(f'\r{text}   ')
                sys.stdout.flush()
                time.sleep(self.interval)
            sys.stdout.write('\r' + ' ' * (len(self.message) + 5) + '\r')
            sys.stdout.flush()

    def start(self, message: str | None = None): # Type hint uses Optional
        """Starts the spinner in a separate thread."""
        if message:
            self.message = message
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        # For a simple threaded spinner, console.status is often easier with Rich.
        # self._thread = threading.Thread(target=self._spin_with_status, daemon=True)
        # self._thread.start()
        # The _spin method above is a basic attempt.
        self.console.print(f"[cyan] {next(self._spinner_cycle)} {self.message}... (Spinner Started - Placeholder for dynamic update)[/cyan]")

    def _spin_with_status(self):
        with self.console.status(self.message, spinner="dots") as status:
            while not self._stop_event.is_set():
                status.update(f"{next(self._spinner_cycle)} {self.message}")
                time.sleep(self.interval)

    def stop(self, final_message: str | None = None): # Type hint uses Optional
        """Stops the spinner and optionally prints a final message."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=self.interval * 2)
        self._thread = None

        if final_message:
            self.console.print(f"[green]✓ {final_message}[/green]")
        else:
            self.console.print(" " * (len(self.message) + 10) + "\r", end="")

    def update_message(self, new_message: str):
        """Updates the spinner's message."""
        self.message = new_message
        sys.stdout.write(f'\r{next(self._spinner_cycle)} {self.message}   ')
        sys.stdout.flush()
