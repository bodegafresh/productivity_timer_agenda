from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import datetime as dt

@dataclass
class Task:
    id: Optional[int]
    title: str
    description: str
    scheduled_at: dt.datetime
    repeat: str  # 'none' | 'daily' | 'weekly' | 'weekdays'
    enabled: bool = True
    last_fired_at: Optional[dt.datetime] = None

    def next_occurrence(self) -> dt.datetime | None:
        if self.repeat == "none":
            return None
        d = self.scheduled_at
        if self.repeat == "daily":
            return d + dt.timedelta(days=1)
        if self.repeat == "weekly":
            return d + dt.timedelta(weeks=1)
        if self.repeat == "weekdays":
            d = d + dt.timedelta(days=1)
            while d.weekday() >= 5:
                d += dt.timedelta(days=1)
            return d
        return None
