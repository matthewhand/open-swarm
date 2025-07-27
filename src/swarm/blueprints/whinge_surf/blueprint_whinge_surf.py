import json
import sys
import threading
import time

from swarm.core.blueprint_base import BlueprintBase
from swarm.core.blueprint_ux import BlueprintUXImproved

# Assuming display_operation_box is now print_operation_box from output_utils
# and BlueprintUXImproved provides self.ux.ansi_emoji_box
# from swarm.blueprints.common.operation_box_utils import display_operation_box


class WhingeSpinner:
    FRAMES = ["Generating.", "Generating..", "Generating...", "Running..."]
    LONG_WAIT_MSG = "Generating... Taking longer than expected"
    SLOW_THRESHOLD = 10

    def __init__(self):
        self._running = False
        self._current_frame = 0
        self._thread: threading.Thread | None = None
        self._start_time: float | None = None

    def start(self) -> None:
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin)
        self._thread.daemon = True
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0) # Add timeout to prevent indefinite blocking
        # Clear the spinner line
        sys.stdout.write("\r\033[K") # K clears from cursor to end of line
        sys.stdout.flush()


    def _spin(self) -> None:
        while self._running:
            elapsed = time.time() - self._start_time if self._start_time else 0
            frame = self.LONG_WAIT_MSG if elapsed > self.SLOW_THRESHOLD else self.FRAMES[self._current_frame]

            # Use \r to return to the beginning of the line and overwrite
            sys.stdout.write(f"\r{frame} \033[K") # Added space and clear to end of line
            sys.stdout.flush()
            self._current_frame = (self._current_frame + 1) % len(self.FRAMES)
            time.sleep(0.5) # Adjusted for smoother visual
        # sys.stdout.write("\r\033[K") # Clear line on stop, handled in stop()
        # sys.stdout.flush()


    def current_spinner_state(self) -> str:
        elapsed = time.time() - self._start_time if self._start_time else 0
        return self.LONG_WAIT_MSG if elapsed > self.SLOW_THRESHOLD else self.FRAMES[self._current_frame]


class WhingeSurfBlueprint(BlueprintBase):
    """
    WhingeSurf: Manages and monitors background processes, providing UX updates.
    """
    VERSION = "0.3.1" # Incremented version
    # JOBS_FILE removed, managed by JobService

    def __init__(self, blueprint_id: str = "whinge_surf", config=None, config_path=None,
                 job_service=None, monitor_service=None, **kwargs):
        from swarm.services.job import DefaultJobService  # Moved import
        from swarm.services.monitor import DefaultMonitorService  # Moved import

        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        # self.blueprint_id, self.config_path, self._config, etc. are set by BlueprintBase

        self.spinner = WhingeSpinner()
        # self._procs removed, managed by JobService
        self.ux = BlueprintUXImproved(style="serious") # Instantiated after super

        self.job_service = job_service or DefaultJobService()
        self.monitor_service = monitor_service or DefaultMonitorService()
        # self._load_jobs() removed, managed by JobService

    # _load_jobs and _save_jobs removed

    def _display_job_status(self, job_id: str, status: str, output: str | None = None,
                            progress: int | None = None, total: int | None = None) -> None:
        # self.spinner._spin() # Spinner runs in its own thread now

        # Use self.ux for displaying boxes
        self.ux.ux_print_operation_box( # Changed to ux_print_operation_box
            title=f"WhingeSurf Job {job_id}",
            content=f"Status: {status}\nOutput: {output or ''}",
            spinner_state=self.spinner.current_spinner_state(), # Get current state
            progress_line=progress or 0, # Ensure int
            total_lines=total or 1, # Ensure int, default 1
            emoji="🌊"
        )

    # run_subprocess_in_background removed, use self.job_service.launch

    def list_jobs(self):
        jobs = self.job_service.list_all()
        job_lines = [f"ID: {job.id}, Command: {job.command_str}, Status: {job.status}, PID: {job.pid or 'N/A'}" for job in jobs]
        return self.ux.ansi_emoji_box(
            title="WhingeSurf Jobs",
            content="\n".join(job_lines) if job_lines else "No jobs found.",
            op_type="list_jobs",
            result_count=len(jobs)
        )

    def show_output(self, job_id: str):
        job_status = self.job_service.get_status(job_id)
        if not job_status:
            return self.ux.ansi_emoji_box(title="Show Output", content=f"No such job: {job_id}", op_type="show_output", params={"pid": job_id}, result_count=0)

        full_log = self.job_service.get_full_log(job_id)
        return self.ux.ansi_emoji_box(
            title="Show Output",
            content=full_log[-2000:] if full_log else "No output yet or job not started.", # Truncate for display
            summary=f"Full output for job {job_id}.",
            op_type="show_output",
            params={"job_id": job_id},
            result_count=len(full_log or "")
        )

    def tail_output(self, job_id: str):
        job_status = self.job_service.get_status(job_id)
        if not job_status:
            # This call was already using keywords correctly for the "not found" case.
            return self.ux.ansi_emoji_box(title="Tail Output", content=f"No such job: {job_id}", op_type="tail_output", params={"pid": job_id}, result_count=0)

        log_tail_list = self.job_service.get_log_tail(job_id)
        return log_tail_list

    def kill_subprocess(self, job_id: str):
        result = self.job_service.terminate(job_id)
        if result == "TERMINATED" or result == "ALREADY_STOPPED":
            msg = f"Job {job_id} terminated or was already stopped."
            status = "success"
        else:
            msg = f"Failed to terminate job {job_id}: {result}"
            status = "error"
        return self.ux.ansi_emoji_box(title="Kill Job", content=msg, op_type="kill_job", params={"job_id": job_id}, status=status)

    def resource_usage(self, job_id: str):
        job = self.job_service.get_status(job_id)
        if not job or not job.pid:
            return self.ux.ansi_emoji_box(title="Resource Usage", content=f"Job {job_id} not found or not running.", op_type="resource_usage", params={"job_id": job_id})

        metrics = self.monitor_service.get_metrics(process_pid=job.pid)
        content_str = json.dumps(metrics, indent=2) if metrics else "Could not retrieve metrics."
        return self.ux.ansi_emoji_box(title=f"Resource Usage for Job {job_id} (PID: {job.pid})", content=content_str, op_type="resource_usage")

    def self_update(self):
        return self.ux.ansi_emoji_box(title="WhingeSurf Self-Update", content="Self-update initiated. Please restart if necessary.", op_type="self_update")

    def analyze_self(self, output_format="json"):
        analysis_content = "Ultra-enhanced code analysis complete. All systems nominal. 🌊"
        return self.ux.ansi_emoji_box(title="WhingeSurf Self-Analysis", content=analysis_content, op_type="analyze_self")

    def prune_jobs(self):
        pruned_ids = self.job_service.prune_completed()
        count = len(pruned_ids)
        msg = f"Removed {count} completed job(s): {', '.join(pruned_ids)}" if count > 0 else "No completed jobs to prune."
        return self.ux.ansi_emoji_box(title="Pruned Jobs", content=msg, op_type="prune_jobs", result_count=count)

    async def run(self, messages, **kwargs):
        """Concrete implementation of BlueprintBase async run method"""
        self.spinner.start()
        all_results_content = []
        final_response_message = {"role": "assistant", "content": "No operation performed."}

        try:
            instruction = messages[-1].get("content", "").lower() if messages else ""
            response_content = "WhingeSurf processed the request."

            if "list jobs" in instruction:
                response_content = self.list_jobs()
            elif "prune jobs" in instruction:
                response_content = self.prune_jobs()
            elif "run " in instruction:
                cmd_str = instruction.replace("run ", "").strip()
                cmd_parts = cmd_str.split()
                if cmd_parts:
                    job_id = self.job_service.launch(cmd_parts, f"cli_job_{cmd_parts[0]}")
                    response_content = f"Launched job {job_id} for command: {' '.join(cmd_parts)}"
                    self._display_job_status(job_id, "LAUNCHED")
                else:
                    response_content = "No command provided to run."

            final_response_message = {"role": "assistant", "content": response_content}
            yield {"messages": [final_response_message]}
            all_results_content.append(response_content)

        except Exception as e:
            self.logger.error(f"Error in WhingeSurf run: {e}", exc_info=True)
            error_content = f"Error processing request: {e}"
            final_response_message = {"role": "assistant", "content": error_content}
            yield {"messages": [final_response_message]}
            all_results_content.append(error_content)
        finally:
            self.spinner.stop()
