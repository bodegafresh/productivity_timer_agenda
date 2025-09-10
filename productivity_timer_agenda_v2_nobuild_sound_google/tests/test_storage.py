import datetime as dt
from app import storage
from app.models import Task

def test_add_and_list_tasks(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.sqlite", raising=False)
    # Ensure schema
    _ = storage.connect()
    t0 = Task(id=None, title="Test", description="", scheduled_at=dt.datetime.now().replace(second=0, microsecond=0), repeat="none", enabled=True)
    tid = storage.add_task(t0)
    assert isinstance(tid, int)
    items = storage.list_tasks()
    assert len(items) == 1
    assert items[0].title == "Test"

def test_tabata_counter(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.sqlite", raising=False)
    _ = storage.connect()
    day = dt.date.today()
    assert storage.count_tabatas_on(day) == 0
    storage.add_tabata_session(dt.datetime.now(), 8, 20, 10, True)
    assert storage.count_tabatas_on(day) == 1
