import asyncio
import threading
from collections.abc import Callable


class AsyncInputHandler:
    """
    Async input handler supporting double-Enter interrupt and warning.
    Usage:
        handler = AsyncInputHandler(on_interrupt=callback)
        await handler.get_input(prompt="You: ")
    """
    def __init__(self, on_interrupt: Callable[[str], None] | None = None):
        self.on_interrupt = on_interrupt
        self._input_event = threading.Event()
        self._interrupt_event = threading.Event()
        self._input_result = None
        self._warned = False
        self._input_thread = None

    def _input_loop(self, prompt):
        buffer = ""
        while True:
            try:
                line = input(prompt if not buffer else "")
            except EOFError:
                break
            if line == "":
                if self._warned:
                    self._interrupt_event.set()
                    break
                else:
                    print("[!] Press Enter again to interrupt and send a new message.")
                    self._warned = True
                    continue
            else:
                buffer = line
                self._input_result = buffer
                self._input_event.set()
                break

    async def get_input(self, prompt="You: "):
        self._warned = False
        self._input_event.clear()
        self._interrupt_event.clear()
        self._input_result = None
        loop = asyncio.get_event_loop()
        self._input_thread = threading.Thread(target=self._input_loop, args=(prompt,))
        self._input_thread.start()
        while not self._input_event.is_set() and not self._interrupt_event.is_set():
            await asyncio.sleep(0.05)
        if self._interrupt_event.is_set():
            if self.on_interrupt:
                self.on_interrupt("")
            return None
        return self._input_result

    def interrupt(self):
        self._interrupt_event.set()
        if self._input_thread and self._input_thread.is_alive():
            try:
                import ctypes
                ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(self._input_thread.ident), ctypes.py_object(KeyboardInterrupt))
            except Exception:
                pass
