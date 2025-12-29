

class DefaultMonitorService:
    def get_metrics(self, job_id: str) -> dict:
        return {"cpu": 25.0, "memory": 1024}
