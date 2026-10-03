import threading
from typing import Any

class MetricsTracker:
    """Thread-safe application metrics collector."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total_requests = 0
        self.jobs_found_by_source: dict[str, int] = {}
        self.error_count_by_source: dict[str, int] = {}

    def record_request(self) -> None:
        with self._lock:
            self.total_requests += 1

    def record_jobs(self, source: str, count: int) -> None:
        with self._lock:
            self.jobs_found_by_source[source] = self.jobs_found_by_source.get(source, 0) + count

    def record_error(self, source: str) -> None:
        with self._lock:
            self.error_count_by_source[source] = self.error_count_by_source.get(source, 0) + 1

    def get_summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_requests": self.total_requests,
                "jobs_found_by_source": self.jobs_found_by_source.copy(),
                "error_count_by_source": self.error_count_by_source.copy()
            }

METRICS = MetricsTracker()
