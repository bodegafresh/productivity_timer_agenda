from __future__ import annotations
import subprocess
import shutil
import threading
import sys

def _send_notify(title: str, message: str):
    # Intentar según el sistema operativo
    try:
        if sys.platform == "linux":
            if shutil.which("notify-send"):
                subprocess.run(["notify-send", title, message], check=False)
        
        elif sys.platform == "darwin": # macOS
            apple_script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", apple_script], check=False)
            
        elif sys.platform == "win32":
            # Requiere win10toast o similar, pero usamos un fallback simple 
            # para no añadir dependencias pesadas si no es necesario
            from tkinter import messagebox
            # Solo como fallback si no hay sistema de toast
            pass 
    except Exception:
        pass

def notify(title: str, message: str):
    """Lanza la notificación en un hilo separado para no congelar la UI"""
    threading.Thread(target=_send_notify, args=(title, message), daemon=True).start()