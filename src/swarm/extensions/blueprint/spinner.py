"""
Simple terminal spinner for interactive feedback during long operations.
"""

import os
import sys
import threading
import time

class Spinner:
    """Simple terminal spinner for interactive feedback."""
    # Define spinner characters (can be customized)
    SPINNER_CHARS = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    # SPINNER_CHARS = ['|', '/', '-', '\\'] # Simpler alternative

    def __init__(self, interactive: bool):
        """
        Initialize the spinner.

        Args:
            interactive (bool): Hint whether the environment is interactive.
                                Spinner is disabled if False or if output is not a TTY.
        """
        self.interactive = interactive
        # Check if output is a TTY (terminal) and interactive flag is True
        self.is_tty = sys.stdout.isatty()
        self.enabled = self.interactive and self.is_tty
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.status = ""
        self.index = 0

    def start(self, status: str = "Processing..."):
        """Start the spinner with an optional status message."""
        if not self.enabled or self.running:
            return # Do nothing if disabled or already running
        self.status = status
        self.running = True
        # Run the spinner animation in a separate daemon thread
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the spinner and clear the line."""
        if not self.enabled or not self.running:
            return # Do nothing if disabled or not running
        self.running = False
        if self.thread is not None:
            self.thread.join() # Wait for the thread to finish
        # Clear the spinner line using ANSI escape codes
        # \r: Carriage return (move cursor to beginning of line)
        # \033[K: Clear line from cursor to end
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        self.thread = None # Reset thread

    def _spin(self):
        """Internal method running in the spinner thread to animate."""
        while self.running:
            # Get the next spinner character
            char = self.SPINNER_CHARS[self.index % len(self.SPINNER_CHARS)]
            # Write spinner char and status, overwrite previous line content
            try:
                # \r moves cursor to beginning, \033[K clears the rest of the line
                sys.stdout.write(f"\r{char} {self.status}\033[K")
                sys.stdout.flush()
            except BlockingIOError:
                 # Handle potential issues if stdout is blocked (less likely for TTY)
                 time.sleep(0.1)
                 continue
            self.index += 1
            # Pause for animation effect
            time.sleep(0.1)

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

