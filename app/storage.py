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

def connect():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL;")
    con.row_factory = sqlite3.Row
    con.execute(DDL)
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

def due_tasks(now: dt.datetime, horizon_minutes: int = 1) -> List[Task]:
    """
    Return tasks enabled whose scheduled_at <= now and not already fired within horizon.
    """
    with connect() as con:
        cur = con.execute(
            """
            SELECT * FROM tasks
            WHERE enabled=1 AND datetime(scheduled_at) <= datetime(?)
            """,
            (now.isoformat(timespec="minutes"),),
        )
        tasks = [_row_to_task(r) for r in cur.fetchall()]
    # Simple horizon filter
    res = []
    horizon = now - dt.timedelta(minutes=horizon_minutes)
    for t in tasks:
        if t.last_fired_at is None or t.last_fired_at < horizon:
            res.append(t)
    return res
