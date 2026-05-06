"""Observability - Node tracing and metrics"""

import time
from contextlib import contextmanager
from typing import Dict, Generator, Optional


class NodeTracer:
    """Track node execution times and errors."""

    def __init__(self):
        self.timings: Dict[str, float] = {}
        self.errors: Dict[str, str] = {}
        self._start_times: Dict[str, float] = {}

    @contextmanager
    def trace(self, node_name: str) -> Generator[None, None, None]:
        start = time.time()
        error: Optional[str] = None
        try:
            yield
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            raise
        finally:
            elapsed = time.time() - start
            self.timings[node_name] = elapsed
            if error:
                self.errors[node_name] = error

    def get_summary(self) -> Dict:
        total = sum(self.timings.values())
        return {
            "total_time": round(total, 3),
            "node_timings": {k: round(v, 3) for k, v in self.timings.items()},
            "errors": self.errors.copy(),
            "slowest_node": max(self.timings, key=self.timings.get)
            if self.timings
            else None,
        }


# Global tracer instance
tracer = NodeTracer()
