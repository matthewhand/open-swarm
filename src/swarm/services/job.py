from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time

@dataclass
class Job:
    id: str
    command: List[str]
    status: str = "PENDING"
    exit_code: Optional[int] = None
    output: str = ""
    tracking_label: str = ""
    _start_time: float = field(default_factory=time.time)

    def terminate(self):
        """Mark job as terminated and calculate duration"""
        if self.status == "RUNNING":
            self.status = "TERMINATED"
            self.exit_code = -1

class DefaultJobService:
    def __init__(self):
        self.jobs: Dict[str, Job] = {}

    def launch(self, command: List[str], tracking_label: str = "") -> str:
        job_id = f"job-{len(self.jobs)+1}"
        new_job = Job(
            id=job_id,
            command=command,
            status="RUNNING",
            tracking_label=tracking_label
        )
        self.jobs[job_id] = new_job
        
        # Simulate async completion
        if "sleep" in command:
            def delayed_completion():
                time.sleep(1)
                new_job.status = "COMPLETED"
                new_job.exit_code = 0
            
            import threading
            threading.Thread(target=delayed_completion).start()

        return job_id

    def get_status(self, job_id: str) -> Job:
        job = self.jobs.get(job_id)
        if job and job.status == "RUNNING" and time.time() - job._start_time > 5:
            job.status = "COMPLETED"
            job.exit_code = 0
        return job or Job(id="", command=[], status="UNKNOWN")

    def get_output(self, job_id: str) -> str:
        job = self.jobs.get(job_id)
        return job.output if job else ""

    @property
    def log_tail(self) -> list:
        return [job.output[-1000:] for job in self.jobs.values()]

    def terminate(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if job:
            job.terminate()
            return True
        return False