from __future__ import annotations
from plyer import notification

def notify(title: str, message: str, timeout: int = 8) -> None:
    try:
        notification.notify(title=title, message=message, timeout=timeout)
    except Exception as e:
        print(f"[notify:fallback] {title}: {message} ({e})")
