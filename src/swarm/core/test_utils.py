import time

class TestSubprocessSimulator:
    """
    Utility for simulating subprocess lifecycle in SWARM_TEST_MODE for blueprint testing.
    Usage:
        simulator = TestSubprocessSimulator()
        proc_id = simulator.launch('sleep 1')
        status = simulator.status(proc_id)
    """
    def __init__(self):
        self._proc_times = {}

    def launch(self, command: str) -> str:
        proc_id = f"test-proc-id-{abs(hash(command)) % 10000}"
        self._proc_times[proc_id] = time.monotonic()
        return proc_id

    def status(self, proc_id: str, finish_after: float = 1.0) -> dict:
        start_time = self._proc_times.get(proc_id, None)
        elapsed = (time.monotonic() - start_time) if start_time else 0
        if elapsed > finish_after:
            return {"status": "finished", "exit_code": 0, "stdout": "", "stderr": ""}
        else:
            return {"status": "running", "exit_code": 0, "stdout": "", "stderr": ""}
