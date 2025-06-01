import subprocess
import sys
import threading
import os
import signal
from typing import Optional, Dict
from swarm.core.blueprint_ux import BlueprintUXImproved
from swarm.core.blueprint_base import BlueprintBase
import json
import time
import psutil  # For resource usage
from swarm.blueprints.common.operation_box_utils import display_operation_box

class WhingeSpinner:
    FRAMES = ["Generating.", "Generating..", "Generating...", "Running..."]
    LONG_WAIT_MSG = "Generating... Taking longer than expected"
    SLOW_THRESHOLD = 10

    def __init__(self):
        self._running = False
        self._current_frame = 0
        self._thread: Optional[threading.Thread] = None
        self._start_time: Optional[float] = None

    def start(self) -> None:
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin)
        self._thread.daemon = True
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join()

    def _spin(self) -> None:
        while self._running:
            elapsed = time.time() - self._start_time if self._start_time else 0
            frame = self.LONG_WAIT_MSG if elapsed > self.SLOW_THRESHOLD else self.FRAMES[self._current_frame]

            sys.stdout.write(f"\r{frame}")
            sys.stdout.flush()
            self._current_frame = (self._current_frame + 1) % len(self.FRAMES)
            time.sleep(0.5)
        sys.stdout.write("\r")
        sys.stdout.flush()

    def current_spinner_state(self) -> str:
        elapsed = time.time() - self._start_time if self._start_time else 0
        return self.LONG_WAIT_MSG if elapsed > self.SLOW_THRESHOLD else self.FRAMES[self._current_frame]

class WhingeSurfBlueprint(BlueprintBase):
    """
    Blueprint to run subprocesses in the background and check on their status/output.
    Now supports self-update via prompt (LLM/agent required for code generation).
    """
    NAME = "whinge_surf"
    CLI_NAME = "whinge_surf"
    DESCRIPTION = "Background subprocess manager: run, check, view output, cancel, and self-update."
    VERSION = "0.3.0"
    JOBS_FILE = os.path.expanduser("~/.whinge_surf_jobs.json")

    def __init__(self, blueprint_id: str = "whinge_surf", config=None, config_path=None,
                 job_service=None, monitor_service=None, **kwargs):
        from swarm.services.job import DefaultJobService
        from swarm.services.monitor import DefaultMonitorService
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self.blueprint_id = blueprint_id
        self.config_path = config_path
        self._config = config if config is not None else None
        self._llm_profile_name = None
        self._llm_profile_data = None
        self._markdown_output = None
        self.spinner = WhingeSpinner()
        self._procs: Dict[int, Dict] = {}  # pid -> {proc, output, thread, status}
        self.ux = BlueprintUXImproved(style="serious")
        self.job_service = job_service or DefaultJobService()
        self.monitor_service = monitor_service or DefaultMonitorService()
        self._load_jobs()

    def _load_jobs(self):
        if os.path.exists(self.JOBS_FILE):
            try:
                with open(self.JOBS_FILE, "r") as f:
                    self._jobs = json.load(f)
            except Exception:
                self._jobs = {}
        else:
            self._jobs = {}

    def _save_jobs(self):
        with open(self.JOBS_FILE, "w") as f:
            json.dump(self._jobs, f, indent=2)

    def _display_job_status(self, job_id: str, status: str, output: Optional[str] = None,
                            progress: Optional[int] = None, total: Optional[int] = None) -> None:
        self.spinner._spin()
        display_operation_box(
            title=f"WhingeSurf Job {job_id}",
            content=f"Status: {status}\nOutput: {output or ''}",
            spinner_state=self.spinner.current_spinner_state(),
            progress_line=progress or 0,
            total_lines=total or 1,
            emoji="🌊"
        )

    def run_subprocess_in_background(self, cmd) -> int:
        """Start a subprocess in the background. Returns the PID."""
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        output = []
        status = {'finished': False, 'exit_code': None}
        start_time = time.time()
        # --- PATCH: Ensure instant jobs finalize output and status ---
        def reader():
            try:
                if proc.stdout:
                    for line in proc.stdout:
                        output.append(line)
                    proc.stdout.close()
                proc.wait()
            finally:
                status['finished'] = True
                status['exit_code'] = proc.returncode
                self._jobs[str(proc.pid)]["end_time"] = time.time()
                self._jobs[str(proc.pid)]["exit_code"] = proc.returncode
                self._jobs[str(proc.pid)]["status"] = "finished"
                self._jobs[str(proc.pid)]["output"] = ''.join(output)
                self._save_jobs()
        t = threading.Thread(target=reader, daemon=True)
        t.start()
        self._procs[proc.pid] = {'proc': proc, 'output': output, 'thread': t, 'status': status}
        # Add to job table
        self._jobs[str(proc.pid)] = {
            "pid": proc.pid,
            "cmd": cmd,
            "start_time": start_time,
            "status": "running",
            "output": None,
            "exit_code": None,
            "end_time": None
        }
        self._save_jobs()
        # --- If process already finished, finalize immediately ---
        if proc.poll() is not None:
            status['finished'] = True
            status['exit_code'] = proc.returncode
            self._jobs[str(proc.pid)]["end_time"] = time.time()
            self._jobs[str(proc.pid)]["exit_code"] = proc.returncode
            self._jobs[str(proc.pid)]["status"] = "finished"
            try:
                if proc.stdout:
                    proc.stdout.close()
            except Exception:
                pass
            self._jobs[str(proc.pid)]["output"] = ''.join(output)
            self._save_jobs()
        self._display_job_status(str(proc.pid), "Started")
        return proc.pid

    def list_jobs(self):
        jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j["start_time"] or 0)
        lines = []
        for job in jobs:
            dur = (job["end_time"] or time.time()) - job["start_time"] if job["start_time"] else 0
            lines.append(f"PID: {job['pid']} | Status: {job['status']} | Exit: {job['exit_code']} | Duration: {dur:.1f}s | Cmd: {' '.join(job['cmd'])}")
        return self.ux.ansi_emoji_box(
            "Job List",
            '\n'.join(lines) or 'No jobs found.',
            summary="All subprocess jobs.",
            op_type="list_jobs",
            params={},
            result_count=len(jobs)
        )

    def show_output(self, pid: int) -> str:
        job = self._jobs.get(str(pid))
        if not job:
            return self.ux.ansi_emoji_box("Show Output", f"No such job: {pid}", op_type="show_output", params={"pid": pid}, result_count=0)
        out = job.output
        if not out:
            return self.ux.ansi_emoji_box("Show Output", f"Job {pid} still running.", op_type="show_output", params={"pid": pid}, result_count=0)
        return self.ux.ansi_emoji_box("Show Output", out[-1000:], summary="Last 1000 chars of output.", op_type="show_output", params={"pid": pid}, result_count=len(out))

    def tail_output(self, pid: int) -> str:
        import time
        import itertools
        job = self._jobs.get(str(pid))
        if not job:
            return self.ux.ansi_emoji_box("Tail Output", f"No such job: {pid}", op_type="tail_output", params={"pid": pid}, result_count=0)
        spinner_cycle = itertools.cycle([
            "Generating.", "Generating..", "Generating...", "Running..."
        ])
        start = time.time()
        last_len = 0
        spinner_message = next(spinner_cycle)
        while True:
            job = self.job_service.get_status(str(pid))
            out = job.output
            lines = out.splitlines()[-10:] if out else []
            elapsed = int(time.time() - start)
            # Spinner escalation if taking long
            if elapsed > 10:
                spinner_message = "Generating... Taking longer than expected"
            else:
                spinner_message = next(spinner_cycle)
            print(self.ux.ansi_emoji_box(
                f"Tail Output | {spinner_message}",
                '\n'.join(f"{i+1}: {line}" for i, line in enumerate(lines)),
                op_type="tail_output",
                params={"pid": pid, "elapsed": elapsed},
                result_count=len(lines)
            ))
            if job.status == "finished":
                break
            time.sleep(1)
        return "[Tail finished]"

    def check_subprocess_status(self, pid: int) -> Optional[Dict]:
        entry = self._procs.get(pid)
        if not entry:
            # Check persistent job table
            job = self._jobs.get(str(pid))
            if job:
                return {"finished": job["status"] == "finished", "exit_code": job["exit_code"]}
            return None
        return entry['status']

    def get_subprocess_output(self, pid: int) -> Optional[str]:
        entry = self._procs.get(pid)
        if not entry:
            # Check persistent job table
            job = self._jobs.get(str(pid))
            if job:
                return job.get("output")
            return None
        return ''.join(entry['output'])

    def kill_subprocess(self, pid: int) -> str:
        entry = self._procs.get(pid)
        if not entry:
            # Try to kill by pid if not tracked
            try:
                os.kill(pid, signal.SIGTERM)
                return f"Sent SIGTERM to {pid}."
            except Exception as e:
                return f"No such subprocess: {pid} ({e})"
        proc = entry['proc']
        if entry['status']['finished']:
            return f"Process {pid} already finished."
        try:
            proc.terminate()
            proc.wait(timeout=5)
            entry['status']['finished'] = True
            entry['status']['exit_code'] = proc.returncode
            self._jobs[str(pid)]["status"] = "finished"
            self._jobs[str(pid)]["exit_code"] = proc.returncode
            self._jobs[str(pid)]["end_time"] = time.time()
            self._save_jobs()
            return f"Process {pid} killed."
        except Exception as e:
            return f"Error killing process {pid}: {e}"

    def resource_usage(self, pid: int) -> str:
        try:
            p = psutil.Process(pid)
            cpu = p.cpu_percent(interval=0.1)
            mem = p.memory_info().rss // 1024
            return self.ux.ansi_emoji_box("Resource Usage", f"CPU: {cpu}% | Mem: {mem} KB", op_type="resource_usage", params={"pid": pid}, result_count=1)
        except Exception as e:
            return self.ux.ansi_emoji_box("Resource Usage", f"Error: {e}", op_type="resource_usage", params={"pid": pid}, result_count=0)

    def self_update_from_prompt(self, prompt: str, test: bool = True) -> str:
        """
        Update the blueprint's own code based on a user prompt. This version will append a comment with the prompt to prove self-modification.
        """
        import shutil, os, time
        src_file = os.path.abspath(__file__)
        backup_file = src_file + ".bak"
        # Step 1: Backup current file
        shutil.copy2(src_file, backup_file)
        # Step 2: Read current code
        with open(src_file, "r") as f:
            code = f.read()
        # Step 3: Apply improvement (append a comment with the prompt)
        new_code = code + f"\n# SELF-IMPROVEMENT: {prompt} ({time.strftime('%Y-%m-%d %H:%M:%S')})\n"
        with open(src_file, "w") as f:
            f.write(new_code)
        # Step 4: Optionally test (skip for proof)
        return self.ux.ansi_emoji_box(
            "Self-Update",
            f"Appended self-improvement comment: {prompt}",
            summary="Self-update completed.",
            op_type="self_update",
            params={"prompt": prompt},
            result_count=1
        )

    def analyze_self(self, output_format: str = "ansi") -> str:
        """
        Ultra-enhanced: Analyze the whinge_surf blueprint's own code and return a concise, actionable summary.
        - Classes/functions/lines, coverage, imports
        - TODOs/FIXMEs with line numbers
        - Longest/most complex function with code snippet
        - Suggestions if code smells detected
        - Output as ANSI box (default), plain text, or JSON
        """
        import inspect, ast, re, json
        src_file = inspect.getfile(self.__class__)
        with open(src_file, 'r') as f:
            code = f.read()
        tree = ast.parse(code, filename=src_file)
        lines = code.splitlines()
        num_lines = len(lines)
        # Classes & functions
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        class_names = [c.name for c in classes]
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        func_names = [f.name for f in functions]
        # TODOs/FIXMEs with line numbers
        todos = [(i+1, l.strip()) for i,l in enumerate(lines) if 'TODO' in l or 'FIXME' in l]
        # Docstring/type hint coverage
        docstring_count = sum(1 for f in functions if ast.get_docstring(f))
        typehint_count = sum(1 for f in functions if f.returns or any(a.annotation for a in f.args.args))
        doc_cov = f"{docstring_count}/{len(functions)} ({int(100*docstring_count/max(1,len(functions)))}%)"
        hint_cov = f"{typehint_count}/{len(functions)} ({int(100*typehint_count/max(1,len(functions)))}%)"
        # Function length stats
        func_lens = []
        for f in functions:
            start = f.lineno-1
            end = max([getattr(f, 'end_lineno', start+1), start+1])
            func_lens.append(end-start)
        avg_len = int(sum(func_lens)/max(1,len(func_lens))) if func_lens else 0
        max_len = max(func_lens) if func_lens else 0
        longest_func = func_names[func_lens.index(max_len)] if func_lens else 'N/A'
        # Code snippet for longest function
        if func_lens:
            f = functions[func_lens.index(max_len)]
            snippet = '\n'.join(lines[f.lineno-1:getattr(f, 'end_lineno', f.lineno)])
        else:
            snippet = ''
        # Imports
        stdlib = set()
        third_party = set()
        import_lines = [line for line in lines if line.strip().startswith('import') or line.strip().startswith('from')]
        for line in import_lines:
            match = re.match(r'(?:from|import)\s+([\w_\.]+)', line)
            if match:
                mod = match.group(1).split('.')[0]
                if mod in ('os','sys','threading','subprocess','signal','inspect','ast','re','shutil','time','typing','logging'): stdlib.add(mod)
                else: third_party.add(mod)
        # Suggestions
        suggestions = []
        if docstring_count < len(functions)//2: suggestions.append('Add more docstrings for clarity.')
        if max_len > 50: suggestions.append(f'Split function {longest_func} ({max_len} lines) into smaller parts.')
        if todos: suggestions.append('Resolve TODOs/FIXMEs for production readiness.')
        # Output construction
        summary_table = (
            f"File: {src_file}\n"
            f"Classes: {class_names}\n"
            f"Functions: {func_names}\n"
            f"Lines: {num_lines}\n"
            f"Docstring/typehint coverage: {doc_cov} / {hint_cov}\n"
            f"Function avg/max length: {avg_len}/{max_len}\n"
            f"Stdlib imports: {sorted(stdlib)}\n"
            f"Third-party imports: {sorted(third_party)}\n"
        )
        todos_section = '\n'.join([f"Line {ln}: {txt}" for ln,txt in todos]) or 'None'
        snippet_section = f"Longest function: {longest_func} ({max_len} lines)\n---\n{snippet}\n---" if snippet else ''
        suggest_section = '\n'.join(suggestions) or 'No major issues detected.'
        docstring = ast.get_docstring(tree)
        if output_format == 'json':
            return json.dumps({
                'file': src_file,
                'classes': class_names,
                'functions': func_names,
                'lines': num_lines,
                'docstring_coverage': doc_cov,
                'typehint_coverage': hint_cov,
                'todos': todos,
                'longest_func': longest_func,
                'longest_func_len': max_len,
                'longest_func_snippet': snippet,
                'suggestions': suggestions,
                'imports': {'stdlib': sorted(stdlib), 'third_party': sorted(third_party)},
                'docstring': docstring,
            }, indent=2)
        text = (
            summary_table +
            f"\nTODOs/FIXMEs:\n{todos_section}\n" +
            (f"\n{snippet_section}\n" if snippet else '') +
            f"\nSuggestions:\n{suggest_section}\n" +
            (f"\nTop-level docstring: {docstring}\n" if docstring else '')
        )
        if output_format == 'text':
            return text
        # Default: ANSI/emoji box
        return self.ux.ansi_emoji_box(
            "Self Analysis",
            text,
            summary="Ultra-enhanced code analysis.",
            op_type="analyze_self",
            params={"file": src_file},
            result_count=len(func_names) + len(class_names)
        )

    def _generate_code_from_prompt(self, prompt: str, src_file: str) -> str:
        """
        Placeholder for LLM/agent call. Should return the full new code for src_file based on prompt.
        """
        # TODO: Integrate with your LLM/agent backend.
        # For now, just return the current code (no-op)
        with open(src_file, "r") as f:
            return f.read()

    def prune_jobs(self, keep_running=True):
        """Remove jobs that are finished (unless keep_running=False, then clear all)."""
        to_remove = []
        for pid, job in self._jobs.items():
            if job["status"] == "finished" or not keep_running:
                to_remove.append(pid)
        for pid in to_remove:
            del self._jobs[pid]
        self._save_jobs()
        return self.ux.ansi_emoji_box(
            "Prune Jobs",
            f"Removed {len(to_remove)} finished jobs.",
            summary="Job table pruned.",
            op_type="prune_jobs",
            params={"keep_running": keep_running},
            result_count=len(to_remove)
        )

    async def run(self, messages, **kwargs):
        """Concrete implementation of BlueprintBase async run method"""
        spinner = WhingeSpinner()
        spinner.start()
        all_results = []

        try:
            async for response in self._process_messages(messages):
                # Process response content
                content = ""
                if isinstance(response, dict):
                    if "messages" in response and response["messages"]:
                        content = response["messages"][0].get("content", "")
                    # Display progressive output
                    if response.get("progress") or response.get("matches"):
                        display_operation_box(
                            title="Progressive Operation",
                            content="\n".join(response.get("matches", [])),
                            style="bold cyan" if response.get("type") == "code_search" else "bold magenta",
                            result_count=len(response.get("matches", [])),
                            params={k: v for k, v in response.items()
                                  if k not in {'matches', 'progress', 'total', 'truncated', 'done'}},
                            progress_line=response.get('progress', 0),
                            total_lines=response.get('total', 1),
                            spinner_state=spinner.current_spinner_state(),
                            op_type=response.get("type", "search"),
                            emoji="🔍" if response.get("type") == "code_search" else "🧠"
                        )
                else:
                    content = str(response)

                all_results.append(content)
                yield response

        finally:
            spinner.stop()

        # Display final output after processing completes
        prompt_content_for_display = "N/A"
        if messages and isinstance(messages, list) and len(messages) > 0 and isinstance(messages[0], dict):
            prompt_content_for_display = messages[0].get("content", "N/A")

        display_operation_box(
            title="WhingeSurf Output",
            content="\n".join(all_results),
            style="bold green",
            result_count=len(all_results),
            params={"prompt": prompt_content_for_display},
            op_type="whinge_surf"
        )

    async def _process_messages(self, messages):
        """Core message processing logic with proper error handling"""
        try:
            if not hasattr(self, 'llm_client') or self.llm_client is None:
                # Attempt to get llm_client from config if not present
                if self._config and 'llm_profile' in self._config:
                    from swarm.core.llm_client_factory import LLMClientFactory
                    self.llm_client = LLMClientFactory.create_llm_client(
                        self._config['llm_profile'], self._config
                    )
                if not hasattr(self, 'llm_client') or self.llm_client is None: # Recheck after attempt
                    self.logger.error("llm_client is not initialized and could not be created from config in WhingeSurfBlueprint.")
                    yield {"error": "LLM client not available", "status": "failed"}
                    return

            async for llm_response_item in self.llm_client.stream_chat(messages):
                if not llm_response_item:
                    continue

                content_text = ""
                if hasattr(llm_response_item, 'content'):
                    content_text = llm_response_item.content
                elif isinstance(llm_response_item, str):
                    content_text = llm_response_item
                else:
                    content_text = str(llm_response_item)

                yield {
                    "messages": [{"content": content_text}],
                    "matches": [],
                    "progress": 0,
                    "total": 1,
                    "type": "llm_chunk"
                }

        except Exception as e:
            self.logger.error(f"Error during LLM stream processing in _process_messages: {str(e)}", exc_info=True)
            yield {"error": f"LLM stream processing error: {str(e)}", "status": "failed"}

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 07:56:41)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 07:58:47)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 08:01:01)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 08:20:21)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 08:22:15)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 08:24:44)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 08:27:41)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 08:30:53)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 08:33:17)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 08:41:39)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 08:46:34)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 08:51:31)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 08:54:19)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 08:57:54)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 09:19:17)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 09:23:35)

# SELF-IMPROVEMENT: Add a test comment (2025-06-01 09:32:18)
