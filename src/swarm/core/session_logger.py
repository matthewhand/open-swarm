import os
import datetime
from typing import Optional, List, Dict

class SessionLogger:
    def __init__(self, blueprint_name: str, log_dir: Optional[str] = None):
        if log_dir is None:
            base_dir = os.path.dirname(__file__)
            log_dir = os.path.join(base_dir, f"../blueprints/{blueprint_name}/session_logs")
        os.makedirs(log_dir, exist_ok=True)
        self.log_dir = log_dir
        self.session_time = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        self.log_path = os.path.join(log_dir, f"session_{self.session_time}.md")
        self._open_log()

    def _open_log(self):
        self.log_file = open(self.log_path, "w")
        self.log_file.write(f"# Session Log\n\nStarted: {self.session_time}\n\n")
        self.log_file.flush()

    def log_instructions(self, global_instructions: Optional[str], project_instructions: Optional[str]):
        self.log_file.write("## Instructions\n")
        if global_instructions:
            self.log_file.write("### Global Instructions\n" + global_instructions + "\n\n")
        if project_instructions:
            self.log_file.write("### Project Instructions\n" + project_instructions + "\n\n")
        self.log_file.write("## Messages\n")
        self.log_file.flush()

    def log_message(self, role: str, content: str, agent_name: str = None):
        # Log agent name if provided, else fallback to role
        display_name = agent_name or role
        self.log_file.write(f"- **{display_name}**: {content}\n")
        self.log_file.flush()

    def log_tool_call(self, tool_name: str, result: str):
        self.log_file.write(f"- **assistant (tool:{tool_name})**: {result}\n")
        self.log_file.flush()

    def close(self):
        self.log_file.write(f"\nEnded: {datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}\n")
        self.log_file.close()
