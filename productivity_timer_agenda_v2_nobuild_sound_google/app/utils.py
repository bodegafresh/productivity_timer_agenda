from __future__ import annotations
import datetime as dt

ISO_FMT = "%Y-%m-%d %H:%M"

def parse_datetime(s: str) -> dt.datetime | None:
    try:
        return dt.datetime.strptime(s.strip(), ISO_FMT)
    except Exception:
        return None

def now() -> dt.datetime:
    return dt.datetime.now()
