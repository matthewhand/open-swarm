import queue
import sys
import threading


class AsyncInputHandler:
    """
    Handles asynchronous CLI input during streaming output.
    On first Enter: warns the user.
    On second Enter: interrupts the operation and collects new input.
    """
    def __init__(self):
        self.input_queue = queue.Queue()
        self.interrupt_event = threading.Event()
        self._warned = False
        self._input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self._input_thread.start()

    def _input_loop(self):
        buffer = ''
        while True:
            c = sys.stdin.read(1)
            if c == '\n':
                if not self._warned:
                    self.input_queue.put('warn')
                    self._warned = True
                else:
                    self.input_queue.put(buffer)
                    buffer = ''
                    self.interrupt_event.set()
                    self._warned = False
            else:
                buffer += c

    def get_input(self, timeout=0.1):
        try:
            return self.input_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def reset(self):
        self.interrupt_event.clear()
        self._warned = False

    def interrupted(self):
        return self.interrupt_event.is_set()
