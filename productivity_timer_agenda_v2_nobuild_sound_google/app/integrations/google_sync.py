from __future__ import annotations
import os, datetime as dt, pathlib, json
from typing import Optional, List, Dict

# Google API imports (lazy)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

DATA_DIR = pathlib.Path(__file__).resolve().parents[1]  # .../app
TOKEN_PATH = DATA_DIR / "token.json"
CLIENT_SECRET_PATH = DATA_DIR / "credentials.json"  # Downloaded from Google Cloud Console

# Scopes: read/write Tasks and Calendar
SCOPES = [
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/calendar"
]

def _get_creds():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET_PATH.exists():
                raise FileNotFoundError("Falta credentials.json en la carpeta app/ para autenticar con Google.")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return creds

# -------------------- Google Tasks --------------------
def tasks_service():
    creds = _get_creds()
    return build('tasks', 'v1', credentials=creds, cache_discovery=False)

def calendar_service():
    creds = _get_creds()
    return build('calendar', 'v3', credentials=creds, cache_discovery=False)

def add_google_task(title: str, notes: str = "", due: Optional[dt.datetime] = None, tasklist_id: Optional[str] = None) -> str:
    svc = tasks_service()
    if not tasklist_id:
        # default tasklist (first one)
        tasklists = svc.tasklists().list(maxResults=1).execute()
        tasklist_id = tasklists['items'][0]['id']
    body = {"title": title}
    if notes:
        body["notes"] = notes
    if due:
        body["due"] = due.astimezone(dt.timezone.utc).isoformat()
    res = svc.tasks().insert(tasklist=tasklist_id, body=body).execute()
    return res["id"]

def list_google_tasks(max_results: int = 50, tasklist_id: Optional[str] = None):
    svc = tasks_service()
    if not tasklist_id:
        tasklists = svc.tasklists().list(maxResults=1).execute()
        tasklist_id = tasklists['items'][0]['id']
    res = svc.tasks().list(tasklist=tasklist_id, maxResults=max_results, showCompleted=True).execute()
    return res.get("items", [])

# -------------------- Google Calendar --------------------
def add_calendar_event(title: str, start: dt.datetime, end: Optional[dt.datetime] = None, description: str = "", calendar_id: str = "primary") -> str:
    svc = calendar_service()
    if end is None:
        end = start + dt.timedelta(minutes=30)
    event = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
    }
    created = svc.events().insert(calendarId=calendar_id, body=event).execute()
    return created["id"]

def list_calendar_events(time_min: Optional[dt.datetime] = None, time_max: Optional[dt.datetime] = None, calendar_id: str = "primary", max_results: int = 50):
    svc = calendar_service()
    import datetime as _dt
    if time_min is None:
        time_min = _dt.datetime.now().astimezone()
    if time_max is None:
        time_max = time_min + _dt.timedelta(days=7)
    res = svc.events().list(calendarId=calendar_id, timeMin=time_min.isoformat(), timeMax=time_max.isoformat(), singleEvents=True, orderBy="startTime", maxResults=max_results).execute()
    return res.get("items", [])

# Convenience: export a local agenda task to both services
def export_local_task_to_google(title: str, when: dt.datetime, notes: str = "") -> Dict[str, str]:
    ids = {}
    try:
        ids["task_id"] = add_google_task(title, notes=notes, due=when)
    except Exception as e:
        ids["task_error"] = str(e)
    try:
        ids["event_id"] = add_calendar_event(title, when, description=notes)
    except Exception as e:
        ids["event_error"] = str(e)
    return ids
