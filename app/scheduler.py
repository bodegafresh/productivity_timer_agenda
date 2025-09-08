from __future__ import annotations
import threading, time, datetime as dt
from .storage import due_tasks, update_task
from .notifications import notify
from .models import Task

class Scheduler(threading.Thread):
    def __init__(self, poll_seconds: int = 20):
        super().__init__(daemon=True)
        self._stop = threading.Event()
        self.poll_seconds = poll_seconds

    def stop(self):
        self._stop.set()

    def run(self):
        while not self._stop.is_set():
            try:
                now = dt.datetime.now().replace(second=0, microsecond=0)
                for task in due_tasks(now):
                    self._fire(task)
            except Exception as e:
                print("[scheduler] error:", e)
            time.sleep(self.poll_seconds)

    def _fire(self, task: Task):
        # Notify
        notify("Recordatorio", f"{task.title}")
        # Update last fired time and reschedule if repeating
        task.last_fired_at = dt.datetime.now().replace(second=0, microsecond=0)
        nxt = task.next_occurrence()
        if nxt is not None:
            task.scheduled_at = nxt
        else:
            # one-shot: disable after firing
            task.enabled = False
        update_task(task)
