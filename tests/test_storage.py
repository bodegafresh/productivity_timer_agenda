import datetime as dt
from app import storage
from app.models import Task

def test_add_and_list_tasks(tmp_path, monkeypatch):
    # use temp DB
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.sqlite", raising=False)
    t0 = Task(id=None, title="Test", description="", scheduled_at=dt.datetime.now().replace(second=0, microsecond=0), repeat="none", enabled=True)
    tid = storage.add_task(t0)
    assert isinstance(tid, int)
    items = storage.list_tasks()
    assert len(items) == 1
    assert items[0].title == "Test"
