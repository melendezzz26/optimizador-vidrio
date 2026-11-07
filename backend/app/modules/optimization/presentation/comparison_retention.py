"""Single retained comparison window across v1/v2 in the one-web-process scope."""
from threading import RLock

from ..application.errors import WorkersNotStopped


class ComparisonRetention:
    def __init__(self):
        self.lock = RLock()
        self.owner = None

    def replace(self, job):
        # Called only after acquiring the shared exclusive comparison admission.
        with self.lock:
            previous = self.owner
            if previous is not None and previous is not job:
                thread = previous.thread
                if (not getattr(previous, "finished", False)
                    and not getattr(previous, "safe_to_retire", False)
                    or thread is not None and thread.is_alive()):
                    raise WorkersNotStopped("Previous comparison retention still has a live owner")
                previous.dispose()
            self.owner = job

    def clear(self, job):
        with self.lock:
            if self.owner is job:
                self.owner = None


COMPARISON_RETENTION = ComparisonRetention()
