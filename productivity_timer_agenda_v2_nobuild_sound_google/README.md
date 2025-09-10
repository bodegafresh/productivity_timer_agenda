# Productivity Timer & Agenda (Python + Tkinter)

Cross-platform desktop app that combines:
- **Pomodoro Timer**
- **Tabata Timer** with **daily counter**
- **Agenda & Reminders** with **system notifications**

**Stack:** Tkinter GUI · SQLite · `plyer` notifications · `pytest` tests.

## Install
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python app/main.py
```

## Features
- **Timer**: configurable work/break/cycles + notifications.
- **Tabata**: configurable work/rest seconds and rounds; logs completed sessions and shows **“Hoy: N tabatas”**.
- **Agenda**: schedule tasks (date/time + recurrence none/daily/weekly/weekdays), notifications, enable/disable, delete.
- **SQLite** storage, no external DB.

## Tests
```bash
pip install -r requirements-dev.txt
pytest -q
```

## Notes
- On Linux, ensure a notification daemon is running (`dunst`, `notify-osd`, etc.).
- DB: `app/app_data.sqlite` (portable with the folder).


## 🔔 Sounds
- Sonidos al **inicio/fin** de bloques (Timer y Tabata) y en **alertas** de Agenda.
- Implementación: `app/sounds.py`. Usa `winsound` (Windows), `NSBeep` (macOS) o `simpleaudio` como fallback.

## ☁️ Google Tasks & Calendar (opcional)
1. Crea un proyecto en [Google Cloud Console] y habilita **Tasks API** y **Calendar API**.
2. Crea credenciales **OAuth client ID** (Desktop) y descarga `credentials.json`.
3. Coloca `credentials.json` dentro de la carpeta `app/` (al lado de `main.py`).
4. La primera vez, se abrirá el navegador para autorizar. Se guardará `token.json` en `app/`.
5. En la pestaña **Agenda**, selecciona una tarea y pulsa **“Exportar a Google”** para crear:
   - Una **tarea** en Google Tasks (con due date)
   - Un **evento** en Google Calendar

> Dependencias: `google-api-python-client`, `google-auth`, `google-auth-oauthlib`.

