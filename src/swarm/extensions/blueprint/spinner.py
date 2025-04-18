"""
Simple terminal spinner for interactive feedback during long operations.
"""

import os
import sys
import threading
import time
from typing import Optional

class Spinner:
    """Simple terminal spinner for interactive feedback."""
    # Define spinner characters (can be customized)
    SPINNER_CHARS = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    # Custom status sequences for special cases
    STATUS_SEQUENCES = {
        'generating': ['Generating.', 'Generating..', 'Generating...'],
        'running': ['Running...']
    }

    def __init__(self, interactive: bool, custom_sequence: str = None):
        """
        Initialize the spinner.

        Args:
            interactive (bool): Hint whether the environment is interactive.
                                Spinner is disabled if False or if output is not a TTY.
            custom_sequence (str): Optional name for a custom status sequence (e.g., 'generating', 'running').
        """
        self.interactive = interactive
        self.is_tty = sys.stdout.isatty()
        self.enabled = self.interactive and self.is_tty
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.status = ""
        self.index = 0
        self.custom_sequence = custom_sequence
        self.sequence_idx = 0

    def start(self, status: str = "Processing..."):
        """Start the spinner with an optional status message."""
        if not self.enabled or self.running:
            return # Do nothing if disabled or already running
        self.status = status
        self.running = True
        self.sequence_idx = 0
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the spinner and clear the line."""
        if not self.enabled or not self.running:
            return # Do nothing if disabled or not running
        self.running = False
        if self.thread is not None:
            self.thread.join() # Wait for the thread to finish
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        self.thread = None

    def _spin(self):
        """Internal method running in the spinner thread to animate."""
        start_time = time.time()
        warned = False
        while self.running:
            elapsed = time.time() - start_time
            if self.custom_sequence and self.custom_sequence in self.STATUS_SEQUENCES:
                seq = self.STATUS_SEQUENCES[self.custom_sequence]
                # If taking longer than 10s, show special message
                if elapsed > 10 and not warned:
                    msg = f"{seq[-1]} Taking longer than expected"
                    warned = True
                else:
                    msg = seq[self.sequence_idx % len(seq)]
                sys.stdout.write(f"\r{msg}\033[K")
                sys.stdout.flush()
                self.sequence_idx += 1
            else:
                char = self.SPINNER_CHARS[self.index % len(self.SPINNER_CHARS)]
                sys.stdout.write(f"\r{char} {self.status}\033[K")
                sys.stdout.flush()
                self.index += 1
            time.sleep(0.4 if self.custom_sequence else 0.1)

# Example usage (if run directly)
if __name__ == "__main__":
    print("Starting spinner test...")
    s = Spinner(interactive=True) # Assume interactive for testing
    s.start("Doing something cool")
    try:
        time.sleep(5) # Simulate work
        s.stop()
        print("Spinner stopped.")
        s.start("Doing another thing")
        time.sleep(3)
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        s.stop() # Ensure spinner stops on exit/error
        print("Test finished.")
