import sys
import threading
import time
import itertools
import os 
from typing import Optional, Dict, Any, Union, List 

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn, TimeElapsedColumn
from rich.markdown import Markdown
from rich.syntax import Syntax
import re 

RICH_AVAILABLE = True # Module level

SPINNER_MESSAGES = {
    "default": ["Generating.", "Generating..", "Generating...", "Running..."],
    "search": ["Searching.", "Searching..", "Searching...", "Analyzing..."],
    "code": ["Analyzing.", "Analyzing..", "Compiling...", "Executing..."],
    "creative": ["Thinking.", "Thinking..", "Creating...", "Polishing..."]
}
SLOW_THRESHOLD = 5.0
LONG_WAIT_MSG = "Taking longer than expected"

class JeevesSpinner:
    SPINNER_STATES = ["Polishing the silver", "Generating.", "Generating..", "Generating...", "Running..."]
    SLOW_THRESHOLD = 7.0
    LONG_WAIT_MSG = "This is taking a while, sir/madam."

    def __init__(self):
        self._running = False
        self._thread = None
        self._current_frame = 0
        self._start_time = None
        self.is_test_mode = bool(os.environ.get("SWARM_TEST_MODE"))

    def start(self):
        if self._running: return
        self._running = True
        self._start_time = time.time()
        if not self.is_test_mode:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        else: 
            print(f"[SPINNER] {self.SPINNER_STATES[0]}")
            sys.stdout.flush() 

    def _spin(self):
        while self._running:
            elapsed = time.time() - self._start_time if self._start_time else 0
            if elapsed > self.SLOW_THRESHOLD:
                frame = self.LONG_WAIT_MSG
            else:
                frame = self.SPINNER_STATES[self._current_frame % len(self.SPINNER_STATES)]
            
            if self.is_test_mode: 
                pass 
            else: 
                sys.stdout.write(f"\r{frame}  ") 
                sys.stdout.flush()
            
            self._current_frame += 1
            time.sleep(0.5)
        
        if not self.is_test_mode:
            sys.stdout.write("\r" + " " * (len(self.LONG_WAIT_MSG) + 5) + "\r") 
            sys.stdout.flush()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if not self.is_test_mode:
            sys.stdout.write("\r" + " " * (len(self.LONG_WAIT_MSG) + 5) + "\r")
            sys.stdout.flush()

    def current_spinner_state(self) -> str:
        if not self._start_time: return self.SPINNER_STATES[0]
        elapsed = time.time() - self._start_time
        if elapsed > self.SLOW_THRESHOLD:
            return self.LONG_WAIT_MSG
        idx = self._current_frame % len(self.SPINNER_STATES)
        return self.SPINNER_STATES[idx]

def get_spinner_state(start_time, interval=0.5, states=None, slow_threshold=None, long_wait_msg=None):
    states = states or SPINNER_MESSAGES["default"]
    slow_threshold = slow_threshold or SLOW_THRESHOLD
    long_wait_msg = long_wait_msg or LONG_WAIT_MSG
    elapsed = time.monotonic() - start_time
    if elapsed > slow_threshold:
        return long_wait_msg
    idx = int(elapsed / interval) % len(states)
    return states[idx]

def pretty_print_response(messages: List[Dict[str, str]], use_markdown: bool = True, console: Optional[Console] = None):
    print(f"DEBUG_PPRINT: Entered pretty_print_response. RICH_AVAILABLE={RICH_AVAILABLE}, use_markdown={use_markdown}", file=sys.stderr) # DEBUG
    _console = console or Console()
    print(f"DEBUG_PPRINT: _console type: {type(_console)}", file=sys.stderr) # DEBUG

    for message_idx, message in enumerate(messages): # Added index for debugging
        print(f"DEBUG_PPRINT: Processing message {message_idx + 1}/{len(messages)}: {message.get('sender')}", file=sys.stderr) # DEBUG
        role = message.get("role", "unknown").capitalize()
        sender = message.get("sender", role) 
        content_to_print = message.get("content", "")
        
        if not content_to_print: 
            print(f"DEBUG_PPRINT: Message {message_idx + 1} has empty content, skipping.", file=sys.stderr) # DEBUG
            continue
        
        print(f"DEBUG_PPRINT: Content for message {message_idx + 1}: {repr(content_to_print)}", file=sys.stderr) # DEBUG
        prefix = f"[{sender}]: "
        
        code_block_pattern = r"```(\w*)?\s*\n?(.*?)\s*\n?```"
        match = re.search(code_block_pattern, content_to_print, re.DOTALL | re.IGNORECASE)
        
        print(f"DEBUG_PPRINT: Regex match for message {message_idx + 1}: {match}", file=sys.stderr) # DEBUG

        if RICH_AVAILABLE and match: 
            print(f"DEBUG_PPRINT: Message {message_idx + 1} - Code block matched!", file=sys.stderr) # DEBUG
            text_before_match = content_to_print[:match.start()]
            lang_from_match = match.group(1)
            lang = lang_from_match.lower().strip() if lang_from_match else "text"
            
            code_in_block = match.group(2)
            code_in_block = code_in_block.strip() if code_in_block is not None else ""

            text_after_match = content_to_print[match.end():]

            printed_prefix = False
            if text_before_match.strip():
                print(f"DEBUG_PPRINT: Message {message_idx + 1} - Printing text_before_match.", file=sys.stderr) # DEBUG
                _console.print(prefix + text_before_match.strip(), end="\n" if code_in_block or text_after_match.strip() else "")
                printed_prefix = True
            
            if not printed_prefix:
                print(f"DEBUG_PPRINT: Message {message_idx + 1} - Printing prefix only.", file=sys.stderr) # DEBUG
                _console.print(prefix, end="")
            
            syntax_obj = Syntax(code_in_block, lang, theme="monokai", line_numbers=False, word_wrap=True)
            print(f"DEBUG_PPRINT: Message {message_idx + 1} - Printing Syntax object: lang='{lang}', code='{repr(code_in_block)}'", file=sys.stderr) # DEBUG
            _console.print(syntax_obj) 

            if text_after_match.strip():
                print(f"DEBUG_PPRINT: Message {message_idx + 1} - Printing text_after_match.", file=sys.stderr) # DEBUG
                if use_markdown:
                    _console.print(Markdown(text_after_match.strip()))
                else:
                    _console.print(text_after_match.strip())
        
        elif RICH_AVAILABLE and use_markdown:
            print(f"DEBUG_PPRINT: Message {message_idx + 1} - No code block, using Markdown.", file=sys.stderr) # DEBUG
            _console.print(prefix, end="")
            _console.print(Markdown(content_to_print))
        else: 
            print(f"DEBUG_PPRINT: Message {message_idx + 1} - Plain text printing.", file=sys.stderr) # DEBUG
            _console.print(prefix + content_to_print)


def print_operation_box(
    title: str,
    content: str, 
    summary: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    result_count: Optional[int] = None,
    op_type: Optional[str] = None, 
    progress_line: Optional[Union[str, int]] = None, 
    total_lines: Optional[int] = None,
    spinner_state: Optional[str] = None, 
    emoji: str = "💡", 
    style: str = "default", 
    console: Optional[Console] = None
):
    _console = console or Console()
    status_to_border_style = {
        "info": "blue", "success": "green", "warning": "yellow",
        "error": "red", "default": "dim" 
    }
    actual_border_style = status_to_border_style.get(style, status_to_border_style["default"])
    panel_content = Text()
    if op_type: panel_content.append(f"Operation: {op_type}\n", style="dim")
    if params:
        param_str = ", ".join(f"{k}={v}" for k, v in params.items())
        panel_content.append(f"Parameters: {param_str}\n", style="dim")
    panel_content.append(content if isinstance(content, (str, Text)) else str(content or "")) 
    if summary: panel_content.append(f"\nSummary: {summary}", style="italic")
    if result_count is not None: panel_content.append(f" | Results: {result_count}", style="italic")
    if progress_line is not None:
        prog_text = f"Progress: {progress_line}"
        if total_lines is not None : prog_text += f"/{total_lines}"
        panel_content.append(f"\n{prog_text}", style="magenta")
    if spinner_state: panel_content.append(f" [{spinner_state}]", style="yellow")
    box_title = f"{emoji} {title}"
    _console.print(Panel(panel_content, title=box_title, border_style=actual_border_style, expand=False))

display_operation_box = print_operation_box

def print_search_progress_box(op_type, results, params, result_type, summary, progress_line, spinner_state, operation_type, search_mode, total_lines, emoji="💡", border="─", console=None):
    _console = console or Console()
    status_to_border_style = {
        "code": "cyan", "semantic": "magenta", "search": "blue",
        "jeeves": "green", "default": "dim"
    }
    actual_border_style = status_to_border_style.get(result_type, status_to_border_style["default"])
    title_str = f"{emoji} {op_type}"
    if operation_type: title_str += f" | {operation_type}"
    if search_mode: title_str += f" ({search_mode})"
    content_text = Text()
    if summary: content_text.append(summary + "\n", style="italic")
    if params:
        param_str = ", ".join(f"{k}={v!r}" for k,v in params.items())
        content_text.append(f"Params: {param_str}\n", style="dim")
    if isinstance(results, list):
        for res_line in results: content_text.append(str(res_line) + "\n")
    else: content_text.append(str(results or "") + "\n") 
    if progress_line is not None:
        prog_display = str(progress_line)
        if total_lines: prog_display += f"/{total_lines}"
        content_text.append(f"Progress: {prog_display}", style="magenta")
    if spinner_state: content_text.append(f" [{spinner_state}]", style="yellow")
    _console.print(Panel(content_text, title=title_str, border_style=actual_border_style, expand=False))

def create_rich_progress_bar() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        console=Console(), 
        transient=True 
    )
