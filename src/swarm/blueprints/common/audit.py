import datetime
import json
import os
import threading


class AuditLogger:
    def __init__(self, enabled: bool = False, file_path: str = None):
        self.enabled = enabled
        self.file_path = file_path or os.environ.get("SWARM_AUDIT_FILE", "swarm_audit.jsonl")
        self._lock = threading.Lock()

    def log_event(self, event_type: str, data: dict):
        if not self.enabled:
            return
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "data": data
        }
        with self._lock:
            with open(self.file_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
