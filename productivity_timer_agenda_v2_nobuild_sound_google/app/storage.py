from __future__ import annotations
import sqlite3, pathlib, datetime as dt
from typing import Optional, List
from .models import Task

DB_PATH = pathlib.Path(__file__).resolve().parent / "app_data.sqlite"

DDL = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    scheduled_at TEXT NOT NULL,
    repeat TEXT NOT NULL DEFAULT 'none',
    enabled INTEGER NOT NULL DEFAULT 1,
    last_fired_at TEXT DEFAULT NULL
);
"""

DDL_TABATA = """
CREATE TABLE IF NOT EXISTS tabata_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    rounds INTEGER NOT NULL,
    work_sec INTEGER NOT NULL,
    rest_sec INTEGER NOT NULL,
    completed INTEGER NOT NULL DEFAULT 1
);
"""

def connect():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL;")
    con.row_factory = sqlite3.Row
    con.execute(DDL)
    con.execute(DDL_TABATA)
    return con

def _row_to_task(row) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"] or "",
        scheduled_at=dt.datetime.fromisoformat(row["scheduled_at"]),
        repeat=row["repeat"],
        enabled=bool(row["enabled"]),
        last_fired_at=dt.datetime.fromisoformat(row["last_fired_at"]) if row["last_fired_at"] else None,
    )

def add_task(task: Task) -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO tasks(title, description, scheduled_at, repeat, enabled, last_fired_at) VALUES (?,?,?,?,?,?)",
            (
                task.title,
                task.description,
                task.scheduled_at.isoformat(timespec="minutes"),
                task.repeat,
                1 if task.enabled else 0,
                task.last_fired_at.isoformat(timespec="minutes") if task.last_fired_at else None,
            ),
        )
        return cur.lastrowid

def list_tasks() -> List[Task]:
    with connect() as con:
        cur = con.execute("SELECT * FROM tasks ORDER BY datetime(scheduled_at) ASC")
        return [_row_to_task(r) for r in cur.fetchall()]

def get_task(task_id: int) -> Optional[Task]:
    with connect() as con:
        cur = con.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        row = cur.fetchone()
        return _row_to_task(row) if row else None

def update_task(task: Task) -> None:
    with connect() as con:
        con.execute(
            "UPDATE tasks SET title=?, description=?, scheduled_at=?, repeat=?, enabled=?, last_fired_at=? WHERE id=?",
            (
                task.title,
                task.description,
                task.scheduled_at.isoformat(timespec="minutes"),
                task.repeat,
                1 if task.enabled else 0,
                task.last_fired_at.isoformat(timespec="minutes") if task.last_fired_at else None,
                task.id,
            ),
        )

def delete_task(task_id: int) -> None:
    with connect() as con:
        con.execute("DELETE FROM tasks WHERE id=?", (task_id,))

def due_tasks(now: dt.datetime, horizon_minutes: int = 1):
    with connect() as con:
        cur = con.execute(
            "SELECT * FROM tasks WHERE enabled=1 AND datetime(scheduled_at) <= datetime(?)",
            (now.isoformat(timespec="minutes"),),
        )
        tasks = [_row_to_task(r) for r in cur.fetchall()]
    res = []
    horizon = now - dt.timedelta(minutes=horizon_minutes)
    for t in tasks:
        if t.last_fired_at is None or t.last_fired_at < horizon:
            res.append(t)
    return res

# --- Tabata helpers ---
def add_tabata_session(started_at: dt.datetime, rounds: int, work_sec: int, rest_sec: int, completed: bool = True) -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO tabata_sessions(started_at, rounds, work_sec, rest_sec, completed) VALUES (?,?,?,?,?)",
            (started_at.isoformat(timespec="minutes"), rounds, work_sec, rest_sec, 1 if completed else 0),
        )
        return cur.lastrowid

def count_tabatas_on(day: dt.date) -> int:
    day_str = day.strftime("%Y-%m-%d")
    with connect() as con:
        cur = con.execute(
            "SELECT COUNT(*) AS c FROM tabata_sessions WHERE date(started_at)=date(?) AND completed=1",
            (day_str,),
        )
        row = cur.fetchone()
        return int(row["c"] if row else 0)
