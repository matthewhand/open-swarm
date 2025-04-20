import subprocess
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
    INTERVAL = 0.12
    SLOW_THRESHOLD = 10

    def __init__(self):
        self._idx = 0
        self._start_time = None
        self._last_frame = self.FRAMES[0]

    def start(self):
        self._start_time = time.time()
        self._idx = 0
        self._last_frame = self.FRAMES[0]

    def _spin(self):
        self._idx = (self._idx + 1) % len(self.FRAMES)
        self._last_frame = self.FRAMES[self._idx]

    def current_spinner_state(self):
        if self._start_time and (time.time() - self._start_time) > self.SLOW_THRESHOLD:
            return self.LONG_WAIT_MSG
        return self._last_frame

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

    def __init__(self, blueprint_id: str = "whinge_surf", config=None, config_path=None, **kwargs):
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

    def _display_job_status(self, job_id, status, output=None, progress=None, total=None):
        self.spinner._spin()
        display_operation_box(
            title=f"WhingeSurf Job {job_id}",
            content=f"Status: {status}\nOutput: {output if output else ''}",
            spinner_state=self.spinner.current_spinner_state(),
            progress_line=progress,
            total_lines=total,
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
                proc.stdout.close()
            except Exception:
                pass
            self._jobs[str(proc.pid)]["output"] = ''.join(output)
            self._save_jobs()
        self._display_job_status(proc.pid, "Started")
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
        out = job.get("output")
        if out is None:
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
            job = self._jobs.get(str(pid))
            out = job.get("output")
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
            if job["status"] == "finished":
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

    async def run_and_print(self, messages):
        spinner = WhingeSpinner()
        spinner.start()
        try:
            all_results = []
            async for response in self.run(messages):
                content = response["messages"][0]["content"] if (isinstance(response, dict) and "messages" in response and response["messages"]) else str(response)
                all_results.append(content)
                # Enhanced progressive output
                if isinstance(response, dict) and (response.get("progress") or response.get("matches")):
                    display_operation_box(
                        title="Progressive Operation",
                        content="\n".join(response.get("matches", [])),
                        style="bold cyan" if response.get("type") == "code_search" else "bold magenta",
                        result_count=len(response.get("matches", [])) if response.get("matches") is not None else None,
                        params={k: v for k, v in response.items() if k not in {'matches', 'progress', 'total', 'truncated', 'done'}},
                        progress_line=response.get('progress'),
                        total_lines=response.get('total'),
                        spinner_state=spinner.current_spinner_state() if hasattr(spinner, 'current_spinner_state') else None,
                        op_type=response.get("type", "search"),
                        emoji="🔍" if response.get("type") == "code_search" else "🧠"
                    )
        finally:
            spinner.stop()
        display_operation_box(
            title="WhingeSurf Output",
            content="\n".join(all_results),
            style="bold green",
            result_count=len(all_results),
            params={"prompt": messages[0]["content"]},
            op_type="whinge_surf"
        )

# SELF-IMPROVEMENT: add a proof of self-improvement (2025-04-19 05:17:27)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:20:22)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:22:57)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:24:30)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:26:19)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:28:02)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:30:18)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:31:26)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:32:37)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:35:24)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:36:26)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:39:09)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:40:10)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:43:04)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 20:44:05)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 21:34:27)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 21:36:05)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 21:36:58)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 21:38:09)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 21:39:00)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 21:41:18)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 21:42:13)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 21:44:26)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 21:45:29)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 21:54:16)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 21:59:18)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:00:25)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:02:11)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:04:15)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:05:25)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:06:26)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:07:26)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:09:13)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:10:29)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:13:18)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:13:42)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:16:03)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:18:39)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:20:36)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:25:35)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:26:31)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:30:05)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:33:27)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:33:50)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:35:57)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:37:40)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:40:29)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:42:50)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:52:23)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:53:37)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:54:56)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:58:00)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 22:59:01)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 23:00:03)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 23:01:06)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 23:02:36)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 23:09:42)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 23:10:42)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 23:17:37)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 23:32:39)

# SELF-IMPROVEMENT: Add a test comment (2025-04-19 23:36:00)
