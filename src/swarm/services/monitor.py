from typing import Dict

class DefaultMonitorService:
    def get_metrics(self, job_id: str) -> Dict:
        return {"cpu": 25.0, "memory": 1024}