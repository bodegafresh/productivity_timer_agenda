from __future__ import annotations
from plyer import notification

def notify(title: str, message: str, timeout: int = 8) -> None:
    """
    Cross-platform desktop notification via plyer.
    """
    try:
        notification.notify(title=title, message=message, timeout=timeout)
    except Exception as e:
        # Best-effort: plyer handles most cases; fallback is no-op to avoid crashes.
        print(f"[notify:fallback] {title}: {message} ({e})")
