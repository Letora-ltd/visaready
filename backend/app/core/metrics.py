from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class Metrics:
    """
    Simple in-memory metrics for the scraping engine (Sprint 3).
    """
    runs_started: int = 0
    runs_success: int = 0
    runs_failed: int = 0
    total_duration: float = 0.0
    
    def log_start(self):
        self.runs_started += 1

    def log_run(self, success: bool, duration: float):
        if success:
            self.runs_success += 1
        else:
            self.runs_failed += 1
        self.total_duration += duration

    def get_report(self) -> dict:
        avg_time = self.total_duration / self.runs_success if self.runs_success > 0 else 0
        return {
            "runs_started": self.runs_started,
            "runs_success": self.runs_success,
            "runs_failed": self.runs_failed,
            "avg_success_duration": round(avg_time, 2),
            "failure_rate": round((self.runs_failed / self.runs_started * 100), 2) if self.runs_started > 0 else 0
        }

# Global singleton
metrics = Metrics()
