import json
import logging
import os
import shlex
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Setup logger for this module
logger = logging.getLogger(__name__)

# Define a path for storing job metadata and outputs
# Consider making this configurable
SWARM_JOB_DATA_DIR = Path(os.path.expanduser("~/.swarm/jobs_data"))
JOBS_METADATA_FILE = SWARM_JOB_DATA_DIR / "jobs_metadata.json"
JOB_OUTPUTS_DIR = SWARM_JOB_DATA_DIR / "outputs"

# Ensure directories exist
SWARM_JOB_DATA_DIR.mkdir(parents=True, exist_ok=True)
JOB_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class Job:
    """
    Represents a job managed by the DefaultJobService.
    """
    id: str
    command_list: list[str] # The command and its arguments as a list
    command_str: str = "" # User-friendly string representation of the command
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, TERMINATED
    pid: int | None = None
    exit_code: int | None = None
    output_file_path: Path | None = None # Path to the file storing stdout/stderr
    tracking_label: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # This field is for the Popen object, not for serialization.
    # It's managed by the service during the job's lifecycle.
    _process_handle: subprocess.Popen | None = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        # Ensure command_str is populated if not provided
        if not self.command_str and self.command_list:
            self.command_str = shlex.join(self.command_list)
        # Ensure output_file_path is set based on id
        if not self.output_file_path:
            self.output_file_path = JOB_OUTPUTS_DIR / f"{self.id}.log"

    def to_dict(self) -> dict[str, Any]:
        """Serializes the job to a dictionary for persistence, excluding runtime handles."""
        return {
            "id": self.id,
            "command_list": self.command_list,
            "command_str": self.command_str,
            "status": self.status,
            "pid": self.pid,
            "exit_code": self.exit_code,
            "output_file_path": str(self.output_file_path) if self.output_file_path else None,
            "tracking_label": self.tracking_label,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Job':
        """Deserializes a job from a dictionary."""
        output_file_path_str = data.get("output_file_path")
        return cls(
            id=data["id"],
            command_list=data.get("command_list", []),
            command_str=data.get("command_str", ""),
            status=data.get("status", "UNKNOWN"),
            pid=data.get("pid"),
            exit_code=data.get("exit_code"),
            output_file_path=Path(output_file_path_str) if output_file_path_str else None,
            tracking_label=data.get("tracking_label"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


class DefaultJobService:
    """
    A default implementation of a job service that manages background processes.
    This service handles launching, monitoring, and retrieving information about jobs.
    Output for jobs is streamed to individual log files.
    """
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock() # For thread-safe access to _jobs
        self._load_jobs_from_disk()
        logger.info(f"DefaultJobService initialized. Loaded {len(self._jobs)} jobs from disk.")

    def _generate_job_id(self, base_name: str | None = None) -> str:
        """Generates a unique job ID."""
        timestamp_ms = int(time.time() * 1000)
        base = base_name or "job"
        # Sanitize base_name for use in ID
        safe_base = "".join(c if c.isalnum() else "_" for c in base)
        return f"{safe_base}_{timestamp_ms}"

    def _save_jobs_to_disk(self):
        """Persists the metadata of all current jobs to a JSON file."""
        with self._lock:
            try:
                serializable_jobs = {job_id: job.to_dict() for job_id, job in self._jobs.items()}
                with JOBS_METADATA_FILE.open("w") as f:
                    json.dump(serializable_jobs, f, indent=2)
                logger.debug(f"Saved {len(serializable_jobs)} jobs to disk at {JOBS_METADATA_FILE}")
            except Exception as e:
                logger.error(f"Error saving jobs to disk: {e}", exc_info=True)

    def _load_jobs_from_disk(self):
        """Loads job metadata from disk on initialization."""
        if JOBS_METADATA_FILE.exists():
            with self._lock:
                try:
                    with JOBS_METADATA_FILE.open("r") as f:
                        loaded_data = json.load(f)
                        for job_id, job_data in loaded_data.items():
                            job = Job.from_dict(job_data)
                            # Jobs loaded from disk are not actively running unless re-monitored.
                            # If status was RUNNING, it's likely stale. Mark as UNKNOWN or check.
                            if job.status == "RUNNING":
                                logger.warning(f"Job {job_id} was RUNNING on disk; actual status unknown without re-check.")
                                # For simplicity, we might mark as UNKNOWN or COMPLETED if PID is old.
                                # A more robust system would try to re-attach or verify.
                                job.status = "UNKNOWN_STALE"
                            self._jobs[job_id] = job
                    logger.info(f"Loaded {len(self._jobs)} job metadata entries from {JOBS_METADATA_FILE}")
                except json.JSONDecodeError:
                    logger.error(f"Error decoding JSON from {JOBS_METADATA_FILE}. Starting with empty job list.", exc_info=True)
                except Exception as e:
                    logger.error(f"Error loading jobs from disk: {e}", exc_info=True)

    def _monitor_job_process(self, job: Job):
        """
        Internal method to run in a thread, monitoring a subprocess.
        Streams stdout/stderr to the job's output file and updates job status.
        """
        if not job._process_handle or job.output_file_path is None:
            logger.error(f"Job {job.id} cannot be monitored: process handle or output file path is missing.")
            job.status = "FAILED"
            job.exit_code = -1 # Indicate internal error
            job.updated_at = time.time()
            self._save_jobs_to_disk()
            return

        logger.info(f"Monitoring job {job.id} (PID: {job.pid}) output to {job.output_file_path}")
        try:
            with job.output_file_path.open("w", encoding="utf-8", errors="replace") as f_out:
                # Stream stdout (which includes stderr due to Popen config)
                if job._process_handle.stdout:
                    for line in iter(job._process_handle.stdout.readline, ''):
                        f_out.write(line)
                        f_out.flush() # Ensure output is written promptly
                        # Optionally, could store recent lines in memory in Job object if needed
                    job._process_handle.stdout.close()

            job._process_handle.wait() # Wait for the process to complete
            job.exit_code = job._process_handle.returncode
            job.status = "COMPLETED" if job.exit_code == 0 else "FAILED"
            logger.info(f"Job {job.id} (PID: {job.pid}) finished with exit code {job.exit_code}. Status: {job.status}")

        except Exception as e:
            logger.error(f"Exception while monitoring job {job.id} (PID: {job.pid}): {e}", exc_info=True)
            job.status = "FAILED"
            job.exit_code = -1 # Indicate monitoring error
        finally:
            job.pid = None # Process has ended
            job._process_handle = None # Clear the handle
            job.updated_at = time.time()
            with self._lock:
                self._jobs[job.id] = job # Ensure the main dict has the updated job
            self._save_jobs_to_disk()
            if job.id in self._threads:
                del self._threads[job.id]


    def launch(self, command: list[str], tracking_label: str | None = None) -> str:
        """
        Launches a command as a background job.
        Args:
            command: The command and its arguments as a list.
            tracking_label: An optional label for the job.
        Returns:
            The unique ID of the launched job.
        """
        if not command:
            logger.error("Cannot launch job: command list is empty.")
            raise ValueError("Command list cannot be empty.")

        job_id_base = tracking_label or command[0]
        job_id = self._generate_job_id(job_id_base)

        job = Job(id=job_id, command_list=command, tracking_label=tracking_label)
        logger.info(f"Launching job {job.id}: {' '.join(job.command_list)}")

        try:
            # Start the subprocess
            process = subprocess.Popen(
                job.command_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Redirect stderr to stdout
                text=True, # Decode output as text
                bufsize=1, # Line-buffered
                universal_newlines=True, # Ensure consistent newline handling
                encoding='utf-8', errors='replace' # Handle potential encoding issues
            )
            job.pid = process.pid
            job._process_handle = process
            job.status = "RUNNING"
            job.updated_at = time.time()

            with self._lock:
                self._jobs[job_id] = job

            # Start a thread to monitor the process and stream its output
            monitor_thread = threading.Thread(target=self._monitor_job_process, args=(job,))
            monitor_thread.daemon = True # Allow main program to exit even if threads are running
            self._threads[job_id] = monitor_thread
            monitor_thread.start()

            self._save_jobs_to_disk()
            logger.info(f"Job {job.id} (PID: {job.pid}) launched successfully and is being monitored.")
            return job_id
        except FileNotFoundError:
            logger.error(f"Command not found for job {job.id}: {job.command_list[0]}", exc_info=True)
            job.status = "FAILED"
            job.exit_code = -1 # Indicate command not found
            with self._lock:
                 self._jobs[job_id] = job # Still record the failed attempt
            self._save_jobs_to_disk()
            raise
        except Exception as e:
            logger.error(f"Failed to launch job {job.id} with command '{job.command_str}': {e}", exc_info=True)
            job.status = "FAILED"
            job.exit_code = -1 # Indicate launch error
            with self._lock:
                 self._jobs[job_id] = job
            self._save_jobs_to_disk()
            raise

    def get_status(self, job_id: str) -> Job | None:
        """Retrieves the current status of a job."""
        with self._lock:
            job = self._jobs.get(job_id)
        if job:
            logger.debug(f"Status for job {job_id}: {job.status}, PID: {job.pid}, Exit: {job.exit_code}")
            # If job was RUNNING but process handle is gone (e.g. after restart), update status
            if job.status == "RUNNING" and job._process_handle is None and job.pid is not None:
                 # This indicates a stale "RUNNING" status, process might have finished externally
                 # or service restarted. A more robust check would involve OS-level PID check.
                 logger.warning(f"Job {job_id} (PID: {job.pid}) has status RUNNING but no active process handle. Consider it UNKNOWN_STALE.")
                 # job.status = "UNKNOWN_STALE" # Or try to determine actual status
                 # For now, we rely on the monitor thread to update status.
        else:
            logger.warning(f"Job ID {job_id} not found.")
        return job

    def get_full_log(self, job_id: str, max_chars: int | None = None) -> str:
        """
        Retrieves the full captured output (stdout/stderr) for a job.
        Args:
            job_id: The ID of the job.
            max_chars: Optional maximum number of characters to return from the end of the log.
        Returns:
            The full log content as a string, or an empty string if not found/no output.
        """
        job = self.get_status(job_id)
        if job and job.output_file_path and job.output_file_path.exists():
            try:
                with job.output_file_path.open("r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if max_chars is not None and len(content) > max_chars:
                    return content[-max_chars:]
                return content
            except Exception as e:
                logger.error(f"Error reading output file for job {job_id}: {e}", exc_info=True)
                return f"[Error reading output file: {e}]"
        elif job:
            return "[No output file found or job not started/completed]"
        logger.warning(f"Full log requested for non-existent job ID {job_id}")
        return "[Job not found]"

    def get_log_tail(self, job_id: str, n_lines: int = 20) -> list[str]:
        """
        Retrieves the last N lines of captured output for a job.
        Args:
            job_id: The ID of the job.
            n_lines: The number of lines to retrieve from the tail of the log.
        Returns:
            A list of strings, each representing a line from the log tail.
        """
        full_log = self.get_full_log(job_id)
        if full_log.startswith("[Job not found]") or full_log.startswith("[Error reading output file"):
            return [full_log] # Return the error message as the only line
        lines = full_log.splitlines()
        return lines[-n_lines:]

    def list_all(self) -> list[Job]:
        """Lists all jobs currently managed by the service."""
        with self._lock:
            # Return copies to prevent external modification of internal state
            jobs_list = [Job.from_dict(job.to_dict()) for job in self._jobs.values()]
        logger.debug(f"Listing {len(jobs_list)} jobs.")
        return jobs_list

    def terminate(self, job_id: str) -> str:
        """
        Terminates a running job.
        Returns:
            A status string: "TERMINATED", "ALREADY_STOPPED", "NOT_FOUND", "ERROR".
        """
        job = self.get_status(job_id)
        if not job:
            logger.warning(f"Attempted to terminate non-existent job ID {job_id}")
            return "NOT_FOUND"

        if job.status not in ["RUNNING", "PENDING"]: # PENDING jobs might not have a process handle yet
            logger.info(f"Job {job_id} is already stopped (status: {job.status}).")
            return "ALREADY_STOPPED"

        if job._process_handle and job.pid:
            try:
                logger.info(f"Attempting to terminate job {job.id} (PID: {job.pid}).")
                job._process_handle.terminate() # Send SIGTERM
                try:
                    job._process_handle.wait(timeout=2) # Wait for graceful termination
                except subprocess.TimeoutExpired:
                    logger.warning(f"Job {job.id} (PID: {job.pid}) did not terminate gracefully, sending SIGKILL.")
                    job._process_handle.kill() # Force kill
                    job._process_handle.wait(timeout=1) # Wait for kill

                job.status = "TERMINATED"
                job.exit_code = job._process_handle.returncode if hasattr(job._process_handle, 'returncode') else -9 # SIGKILL often -9
                job.updated_at = time.time()
                job._process_handle = None # Clear handle
                job.pid = None
                self._save_jobs_to_disk()
                logger.info(f"Job {job.id} terminated with exit code {job.exit_code}.")
                return "TERMINATED"
            except Exception as e:
                logger.error(f"Error terminating job {job.id} (PID: {job.pid}): {e}", exc_info=True)
                job.status = "FAILED_TERMINATION" # A special status
                job.updated_at = time.time()
                self._save_jobs_to_disk()
                return "ERROR"
        else:
            logger.warning(f"Job {job.id} is {job.status} but has no process handle to terminate.")
            # If it was PENDING and never started, or RUNNING but handle lost (e.g. restart)
            job.status = "TERMINATED" # Assume it should be stopped
            job.exit_code = -1 # Indicate abnormal stop
            job.updated_at = time.time()
            self._save_jobs_to_disk()
            return "TERMINATED" # Or "UNKNOWN_STATE_STOPPED"

    def prune_completed(self) -> list[str]:
        """Removes all jobs that are in a terminal state (COMPLETED, FAILED, TERMINATED)."""
        pruned_ids: list[str] = []
        with self._lock:
            job_ids_to_prune = [
                job_id for job_id, job in self._jobs.items()
                if job.status in ["COMPLETED", "FAILED", "TERMINATED", "FAILED_TERMINATION", "UNKNOWN_STALE"]
            ]
            for job_id in job_ids_to_prune:
                job = self._jobs.pop(job_id, None)
                if job and job.output_file_path and job.output_file_path.exists():
                    try:
                        job.output_file_path.unlink() # Delete associated log file
                        logger.debug(f"Deleted output file for pruned job {job_id}: {job.output_file_path}")
                    except OSError as e:
                        logger.error(f"Error deleting output file for pruned job {job_id}: {e}", exc_info=True)
                if job:
                    pruned_ids.append(job_id)
                    logger.info(f"Pruned job {job_id} with status {job.status}.")

        if pruned_ids:
            self._save_jobs_to_disk() # Save changes after pruning
        logger.info(f"Pruned {len(pruned_ids)} jobs: {pruned_ids}")
        return pruned_ids

    def get_output(self, job_id: str) -> str: # Kept for compatibility if some tests used it
        """Alias for get_full_log for basic compatibility."""
        logger.warning("get_output is deprecated, use get_full_log or get_log_tail.")
        return self.get_full_log(job_id)

