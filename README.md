# Productivity Timer & Agenda (Cross‑Platform, Python + Tkinter)

A simple, cross‑platform desktop app that combines a **customizable Pomodoro timer** with a **task agenda & reminders** using **system notifications**.

- GUI: Tkinter (built‑in in Python)
- Notifications: plyer (Windows/macOS/Linux)
- Storage: SQLite (built‑in `sqlite3`)
- Tests: `pytest`

> **Why this project?** Good time management improves mental and physical health. The app helps you focus (timer) and remember key tasks or micro‑breaks (agenda + notifications).

---

## ✨ Features

- **Pomodoro Timer**: custom work/break durations, start/pause/reset, cycles counter, desktop notifications.
- **Agenda / Reminders**: add tasks with date/time and recurrence (none/daily/weekly/weekdays). Enable/disable and delete.
- **System Notifications** via `plyer`, with Tk fallback bell.
- **Cross‑platform** (Windows, macOS, Linux).
- **No external DB**: uses local SQLite file in the app directory.

---

## 🛠️ Installation

**Requirements:** Python 3.9+ recommended.

```bash
# Create and activate a virtual env (recommended)
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install deps
pip install -r requirements.txt
```

> On Linux, some desktop environments may need a active notification service (e.g., `notify-osd`, `dunst`).

---

## ▶️ Run

```bash
python app/main.py
```

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

---

## 📦 Project Structure

```
app/
  main.py
  models.py
  storage.py
  scheduler.py
  notifications.py
  utils.py
requirements.txt
requirements-dev.txt
README.md
LICENSE
tests/
  test_storage.py
```

---

## 💡 Usage Tips

- **Timer Tab**: set your work/break durations and cycles. You’ll get a desktop notification at phase transitions.
- **Agenda Tab**:
  - Add a task with title, optional description, date/time and a recurrence rule.
  - Tasks trigger a notification at the scheduled time; recurring tasks automatically reschedule.
  - Use the toolbar to *enable/disable* or *delete* tasks.

### Example: Micro‑breaks for core (from your plan)
Create tasks at your preferred times with these titles (or add them to the built‑in templates in code):
- “Planchas frontales 3×45s”
- “Planchas laterales 3×30s”
- “Elevaciones de piernas 3×12”
- “Crunch inverso 3×15”

Set them to **weekdays** recurrence to pair with Pomodoro sessions.

---

## 🔧 Configuration

Basic settings are persisted in an SQLite DB (`app_data.sqlite`). You can safely move the project folder; the DB moves with it.

---

## 🐛 Troubleshooting

- **No notifications on Linux**: ensure a notification daemon is active (`dunst`, `notify-osd`, etc.).
- **macOS permission prompts**: grant notification permission when asked.
- **Windows Defender SmartScreen**: allow Python to show notifications.

---

## 📄 License

MIT
