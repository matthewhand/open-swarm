import sys
import threading
import time


class Spinner:
    """
    Displays spinner states: Generating., Generating.., Generating..., Running...,
    and switches to 'Taking longer than expected' after a timeout.
    """
    def __init__(self, base_message: str = "Generating", long_wait_timeout: float = 8.0):
        self.base_message = base_message
        self.states = [".", "..", "...", "..", "."]
        self.running = False
        self.thread = None
        self.long_wait_timeout = long_wait_timeout
        self._long_wait = False

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()

    def _spin(self):
        idx = 0
        start_time = time.time()
        while self.running:
            if not self._long_wait and (time.time() - start_time > self.long_wait_timeout):
                self._long_wait = True
            if self._long_wait:
                msg = f"{self.base_message}... Taking longer than expected"
            else:
                msg = f"{self.base_message}{self.states[idx % len(self.states)]}"
            sys.stdout.write(f"\r{msg}")
            sys.stdout.flush()
            time.sleep(0.4)
            idx += 1

    def set_message(self, message):
        self.base_message = message
        self._long_wait = False

# Example usage:
# spinner = Spinner()
# spinner.start()
# ... do work ...
# spinner.stop()
