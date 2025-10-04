from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from tkcalendar import DateEntry, Calendar
except ImportError:  # pragma: no cover
    DateEntry = None
    Calendar = None
import datetime as dt

from .storage import add_task, list_tasks, update_task, delete_task, get_task, add_tabata_session, count_tabatas_on
from .models import Task
from .scheduler import Scheduler
from .notifications import notify
from .sounds import play as play_sound
from .utils import parse_datetime, now
from .integrations.google_sync import export_local_task_to_google

APP_TITLE = "Productivity Timer & Agenda"
WINDOWING_SYSTEM = None

class TimerTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.work_min = tk.IntVar(value=25)
        self.break_min = tk.IntVar(value=5)
        self.cycles = tk.IntVar(value=4)

        self.remaining = 0
        self.is_work = True
        self.running = False
        self.completed_cycles = 0
        self._timer_id = None

        self._build_ui()

    def _build_ui(self):
        row = 0
        ttk.Label(self, text="Trabajo (min)").grid(row=row, column=0, sticky="w")
        ttk.Spinbox(self, from_=1, to=180, textvariable=self.work_min, width=5).grid(row=row, column=1, sticky="w", padx=5)
        ttk.Label(self, text="Descanso (min)").grid(row=row, column=2, sticky="w", padx=(20,0))
        ttk.Spinbox(self, from_=1, to=60, textvariable=self.break_min, width=5).grid(row=row, column=3, sticky="w", padx=5)
        ttk.Label(self, text="Ciclos").grid(row=row, column=4, sticky="w", padx=(20,0))
        ttk.Spinbox(self, from_=1, to=12, textvariable=self.cycles, width=5).grid(row=row, column=5, sticky="w", padx=5)

        row += 1
        self.time_lbl = ttk.Label(self, text="00:00", font=("Segoe UI", 28, "bold"))
        self.time_lbl.grid(row=row, column=0, columnspan=6, pady=10)

        row += 1
        btns = ttk.Frame(self)
        btns.grid(row=row, column=0, columnspan=6, pady=5, sticky="w")
        ttk.Button(btns, text="Iniciar", command=self.start).grid(row=0, column=0, padx=2)
        ttk.Button(btns, text="Pausar", command=self.pause).grid(row=0, column=1, padx=2)
        ttk.Button(btns, text="Reiniciar", command=self.reset).grid(row=0, column=2, padx=2)
        ttk.Button(btns, text="Preset 50/10", command=lambda: self._apply_preset(50,10,3)).grid(row=0, column=3, padx=12)

        row += 1
        self.status_lbl = ttk.Label(self, text="Listo")
        self.status_lbl.grid(row=row, column=0, columnspan=6, sticky="w")

        for i in range(6):
            self.grid_columnconfigure(i, weight=1)

    def _apply_preset(self, w, b, c):
        if self.running:
            return
        self.work_min.set(w); self.break_min.set(b); self.cycles.set(c)

    def _tick(self):
        if not self.running:
            return
        if self.remaining <= 0:
            self._phase_change()
        else:
            self.remaining -= 1
            self._update_time_lbl()
            self._timer_id = self.after(1000, self._tick)

    def _update_time_lbl(self):
        m, s = divmod(self.remaining, 60)
        self.time_lbl.config(text=f"{m:02d}:{s:02d}")

    def _phase_change(self):
        try:
            self.bell()
        except Exception:
            pass
        phase = "Trabajo" if self.is_work else "Descanso"
        notify("Timer", f"Fin de {phase}")
        play_sound("end")
        if self.is_work:
            self.completed_cycles += 1
            if self.completed_cycles >= self.cycles.get():
                self.running = False
                self.status_lbl.config(text=f"Ciclos completados: {self.completed_cycles}")
                return
            self.is_work = False
            self.remaining = self.break_min.get() * 60
            self.status_lbl.config(text=f"Descanso #{self.completed_cycles}")
            play_sound("start")
        else:
            self.is_work = True
            self.remaining = self.work_min.get() * 60
            self.status_lbl.config(text=f"Trabajo #{self.completed_cycles+1}")
            play_sound("start")
        self._update_time_lbl()
        self._timer_id = self.after(1000, self._tick)

    def start(self):
        if self.running:
            return
        if self.remaining <= 0:
            self.is_work = True
            self.completed_cycles = 0
            self.remaining = self.work_min.get() * 60
            self.status_lbl.config(text="Trabajo #1")
            play_sound("start")
            self._update_time_lbl()
        self.running = True
        play_sound("start")
        self._tick()

    def pause(self):
        self.running = False
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        self.status_lbl.config(text="Pausado")

    def reset(self):
        self.pause()
        self.remaining = 0
        self.completed_cycles = 0
        self.is_work = True
        self._update_time_lbl()
        self.status_lbl.config(text="Listo")


class TabataTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.work_sec = tk.IntVar(value=20)
        self.rest_sec = tk.IntVar(value=10)
        self.rounds = tk.IntVar(value=8)

        self.remaining = 0
        self.is_work = True
        self.running = False
        self.current_round = 0
        self._timer_id = None
        self._session_start = None

        self._build_ui()
        self.refresh_today_count()

    def _build_ui(self):
        row = 0
        ttk.Label(self, text="Trabajo (seg)").grid(row=row, column=0, sticky="w")
        ttk.Spinbox(self, from_=5, to=300, textvariable=self.work_sec, width=6).grid(row=row, column=1, sticky="w", padx=5)
        ttk.Label(self, text="Descanso (seg)").grid(row=row, column=2, sticky="w", padx=(20,0))
        ttk.Spinbox(self, from_=5, to=300, textvariable=self.rest_sec, width=6).grid(row=row, column=3, sticky="w", padx=5)
        ttk.Label(self, text="Rondas").grid(row=row, column=4, sticky="w", padx=(20,0))
        ttk.Spinbox(self, from_=1, to=20, textvariable=self.rounds, width=6).grid(row=row, column=5, sticky="w", padx=5)

        row += 1
        self.time_lbl = ttk.Label(self, text="00:00", font=("Segoe UI", 28, "bold"))
        self.time_lbl.grid(row=row, column=0, columnspan=6, pady=10)

        row += 1
        self.status_lbl = ttk.Label(self, text="Listo (20/10×8)")
        self.status_lbl.grid(row=row, column=0, columnspan=6, sticky="w")

        row += 1
        btns = ttk.Frame(self)
        btns.grid(row=row, column=0, columnspan=6, pady=6, sticky="w")
        ttk.Button(btns, text="Iniciar", command=self.start).grid(row=0, column=0, padx=2)
        ttk.Button(btns, text="Pausar", command=self.pause).grid(row=0, column=1, padx=2)
        ttk.Button(btns, text="Reiniciar", command=self.reset).grid(row=0, column=2, padx=2)
        ttk.Button(btns, text="Preset 20/10×8", command=lambda: self._apply_preset(20,10,8)).grid(row=0, column=3, padx=12)
        ttk.Button(btns, text="Preset 40/20×6", command=lambda: self._apply_preset(40,20,6)).grid(row=0, column=4, padx=2)

        row += 1
        self.today_lbl = ttk.Label(self, text="Hoy: 0 tabatas")
        self.today_lbl.grid(row=row, column=0, columnspan=6, sticky="w", pady=(8,0))

        for i in range(6):
            self.grid_columnconfigure(i, weight=1)

    def _apply_preset(self, w, r, n):
        if self.running:
            return
        self.work_sec.set(w); self.rest_sec.set(r); self.rounds.set(n)
        self.status_lbl.config(text=f"Preset {w}/{r}×{n}")

    def _update_time_lbl(self):
        m, s = divmod(self.remaining, 60)
        self.time_lbl.config(text=f"{m:02d}:{s:02d}")

    def _tick(self):
        if not self.running:
            return
        if self.remaining <= 0:
            self._phase_change()
        else:
            self.remaining -= 1
            self._update_time_lbl()
            self._timer_id = self.after(1000, self._tick)

    def _phase_change(self):
        try:
            self.bell()
        except Exception:
            pass
        if self.is_work:
            self.current_round += 1
            notify("Tabata", f"Fin trabajo #{self.current_round}")
            play_sound("end")
            if self.current_round >= self.rounds.get():
                self._finish_session()
                return
            self.is_work = False
            self.remaining = self.rest_sec.get()
            self.status_lbl.config(text=f"Descanso (ronda {self.current_round}/{self.rounds.get()})")
        else:
            notify("Tabata", "Fin descanso")
            play_sound("end")
            self.is_work = True
            self.remaining = self.work_sec.get()
            self.status_lbl.config(text=f"Trabajo (ronda {self.current_round+1}/{self.rounds.get()})")
        self._update_time_lbl()
        self._timer_id = self.after(1000, self._tick)

    def _finish_session(self):
        self.running = False
        self.remaining = 0
        self._update_time_lbl()
        self.status_lbl.config(text=f"¡Completado! {self.rounds.get()} rondas")
        notify("Tabata", "Sesión completada 🎉")
        play_sound("alert")
        start = self._session_start or dt.datetime.now().replace(second=0, microsecond=0)
        add_tabata_session(start, self.rounds.get(), self.work_sec.get(), self.rest_sec.get(), True)
        self.refresh_today_count()

    def start(self):
        if self.running:
            return
        if self.remaining <= 0:
            self.is_work = True
            self.current_round = 0
            self.remaining = self.work_sec.get()
            self._session_start = dt.datetime.now().replace(second=0, microsecond=0)
            self.status_lbl.config(text=f"Trabajo (ronda 1/{self.rounds.get()})")
            self._update_time_lbl()
        self.running = True
        play_sound("start")
        self._tick()

    def pause(self):
        self.running = False
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        self.status_lbl.config(text="Pausado")

    def reset(self):
        self.pause()
        self.remaining = 0
        self.is_work = True
        self.current_round = 0
        self._session_start = None
        self._update_time_lbl()
        self.status_lbl.config(text="Listo")

    def refresh_today_count(self):
        try:
            c = count_tabatas_on(dt.date.today())
        except Exception:
            c = 0
        self.today_lbl.config(text=f"Hoy: {c} tabatas")


class AgendaTab(ttk.Frame):

    def export_to_google(self):
        tid = self._selected_task_id()
        if tid is None:
            messagebox.showinfo("Exportar a Google", "Selecciona una tarea de la lista.")
            return
        from .storage import get_task
        t = get_task(tid)
        if not t:
            return
        try:
            ids = export_local_task_to_google(t.title, t.scheduled_at, notes=t.description)
            ok_msg = "Exportado:\n"
            if "task_id" in ids: ok_msg += f"- Google Tasks: {ids['task_id']}\n"
            if "event_id" in ids: ok_msg += f"- Calendar: {ids['event_id']}\n"
            if "task_error" in ids or "event_error" in ids:
                ok_msg += "\n(Con errores)\n"
                if "task_error" in ids: ok_msg += f"Tasks error: {ids['task_error']}\n"
                if "event_error" in ids: ok_msg += f"Calendar error: {ids['event_error']}\n"
            messagebox.showinfo("Exportar a Google", ok_msg)
        except Exception as e:
            messagebox.showerror("Exportar a Google", f"No se pudo exportar: {e}\nColoca credentials.json en la carpeta app/ y vuelve a intentar.")

    def __init__(self, master):
        super().__init__(master)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        frm = ttk.LabelFrame(self, text="Nueva tarea / recordatorio")
        frm.pack(fill="x", padx=5, pady=5)

        self.title_var = tk.StringVar()
        self.desc_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.time_var = tk.StringVar()
        self.repeat_var = tk.StringVar(value="none")
        self._calendar_popup = None
        self._time_popup = None

        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=5, pady=5)

        ttk.Label(grid, text="Título").grid(row=0, column=0, sticky="w")
        ttk.Entry(grid, textvariable=self.title_var, width=40).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(grid, text="Descripción").grid(row=0, column=2, sticky="w")
        ttk.Entry(grid, textvariable=self.desc_var, width=40).grid(row=0, column=3, sticky="w", padx=5)

        ttk.Label(grid, text="Fecha").grid(row=1, column=0, sticky="w", pady=(6,0))
        today = dt.date.today()
        if DateEntry is None:
            self.date_entry = ttk.Entry(grid, textvariable=self.date_var, width=16)
        else:
            if WINDOWING_SYSTEM == "aqua":
                # macOS (Aqua) tiene problemas con el popup nativo de tkcalendar
                self.date_entry = ttk.Entry(grid, textvariable=self.date_var, width=16, state="readonly")
                self.date_entry.bind("<Button-1>", self._open_mac_calendar)
            else:
                self.date_entry = DateEntry(
                    grid,
                    textvariable=self.date_var,
                    date_pattern="yyyy-mm-dd",
                    width=16,
                    showweeknumbers=False,
                    state="readonly",
                    mindate=today,
                )
        self.date_entry.grid(row=1, column=1, sticky="w", padx=5, pady=(6,0))
        ttk.Label(grid, text="Hora (HH:MM)").grid(row=1, column=2, sticky="w", pady=(6,0))
        self.time_entry = ttk.Entry(grid, textvariable=self.time_var, width=10, state="readonly")
        self.time_entry.grid(row=1, column=3, sticky="w", padx=5, pady=(6,0))
        self.time_entry.bind("<Button-1>", self._open_time_picker)

        ttk.Label(grid, text="Repetir").grid(row=2, column=0, sticky="w", pady=(6,0))
        cb = ttk.Combobox(grid, textvariable=self.repeat_var, values=["none","daily","weekly","weekdays"], width=12, state="readonly")
        cb.grid(row=2, column=1, sticky="w", padx=5, pady=(6,0))

        btns = ttk.Frame(frm)
        btns.pack(fill="x", padx=5, pady=5)
        ttk.Button(btns, text="Ahora +10 min", command=lambda: self._preset_minutes(10)).pack(side="left", padx=2)
        ttk.Button(btns, text="Ahora +30 min", command=lambda: self._preset_minutes(30)).pack(side="left", padx=2)
        ttk.Button(btns, text="Agregar", command=self.add_task).pack(side="left", padx=10)

        # Table
        tbl_frame = ttk.LabelFrame(self, text="Tareas programadas")
        tbl_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(tbl_frame, columns=("when","title","repeat","enabled"), show="headings", height=10)
        self.tree.heading("when", text="Cuándo")
        self.tree.heading("title", text="Título")
        self.tree.heading("repeat", text="Repetir")
        self.tree.heading("enabled", text="Activa")
        self.tree.pack(fill="both", expand=True, side="left")

        vsb = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side="right", fill="y")

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=5, pady=5)
        ttk.Button(actions, text="Activar/Desactivar", command=self.toggle_task).pack(side="left", padx=2)
        ttk.Button(actions, text="Eliminar", command=self.delete_task).pack(side="left", padx=2)
        ttk.Button(actions, text="Refrescar", command=self.refresh).pack(side="left", padx=2)
        ttk.Button(actions, text="Exportar a Google", command=self.export_to_google).pack(side="left", padx=8)

    def _open_mac_calendar(self, _event=None):
        if Calendar is None:
            # Si tkcalendar no está disponible, no podemos mostrar popup personalizado
            return
        self._close_calendar_popup()

        top = tk.Toplevel(self)
        top.transient(self.winfo_toplevel())
        top.wm_overrideredirect(True)
        top.configure(borderwidth=1, relief="solid", background="#e5e5e5")

        entry_x = self.date_entry.winfo_rootx()
        entry_y = self.date_entry.winfo_rooty() + self.date_entry.winfo_height()
        top.geometry(f"220x210+{entry_x}+{entry_y}")

        try:
            current_date = dt.datetime.strptime(self.date_var.get(), "%Y-%m-%d").date()
        except Exception:
            current_date = dt.date.today()

        cal = Calendar(
            top,
            selectmode="day",
            year=current_date.year,
            month=current_date.month,
            day=current_date.day,
            date_pattern="yyyy-mm-dd",
            showweeknumbers=False,
            mindate=dt.date.today(),
        )
        cal.pack(fill="both", expand=True, padx=4, pady=4)

        cal.bind("<<CalendarSelected>>", lambda _e: self._on_calendar_selected(cal))
        top.bind("<FocusOut>", lambda _e: self._close_calendar_popup())
        top.bind("<Escape>", lambda _e: self._close_calendar_popup())

        self._calendar_popup = top
        top.focus_set()

    def _on_calendar_selected(self, cal: Calendar):
        value = cal.get_date()
        self.date_var.set(value)
        self._close_calendar_popup()

    def _close_calendar_popup(self):
        if self._calendar_popup is not None and self._calendar_popup.winfo_exists():
            self._calendar_popup.destroy()
        self._calendar_popup = None

    def _open_time_picker(self, _event=None):
        self._close_time_popup()

        top = tk.Toplevel(self)
        top.transient(self.winfo_toplevel())
        top.wm_overrideredirect(True)
        top.configure(borderwidth=1, relief="solid", background="#e5e5e5")

        entry_x = self.time_entry.winfo_rootx()
        entry_y = self.time_entry.winfo_rooty() + self.time_entry.winfo_height()
        top.geometry(f"+{entry_x}+{entry_y}")

        frame = ttk.Frame(top, padding=8)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Hora").grid(row=0, column=0, pady=(0,6))
        hour_var = tk.StringVar(value=(self.time_var.get()[:2] if len(self.time_var.get()) >= 2 else "00"))
        hour_list = tk.Listbox(frame, height=8, exportselection=False, width=3, activestyle="dotbox")
        for h in range(24):
            hour_list.insert("end", f"{h:02d}")
        try:
            idx = list(hour_list.get(0, "end")).index(hour_var.get())
            hour_list.selection_set(idx)
            hour_list.see(idx)
        except Exception:
            hour_list.selection_clear(0, "end")
            hour_list.selection_set(0)
        hour_list.grid(row=1, column=0, padx=(0,6))

        ttk.Label(frame, text="Min").grid(row=0, column=1, pady=(0,6))
        minute_var = tk.StringVar(value=(self.time_var.get()[3:5] if len(self.time_var.get()) >= 5 else "00"))
        minute_list = tk.Listbox(frame, height=8, exportselection=False, width=3, activestyle="dotbox")
        for m in range(60):
            minute_list.insert("end", f"{m:02d}")
        try:
            idx = list(minute_list.get(0, "end")).index(minute_var.get())
            minute_list.selection_set(idx)
            minute_list.see(idx)
        except Exception:
            minute_list.selection_clear(0, "end")
            minute_list.selection_set(0)
        minute_list.grid(row=1, column=1, padx=(0,6))

        btns = ttk.Frame(frame)
        btns.grid(row=2, column=0, columnspan=2, pady=(10,0))
        ttk.Button(btns, text="Cancelar", command=self._close_time_popup).pack(side="left", padx=4)
        ttk.Button(btns, text="Aceptar", command=lambda: self._set_time_and_close_from_lists(hour_list, minute_list)).pack(side="left", padx=4)

        hour_list.bind("<Double-Button-1>", lambda _e: self._set_time_and_close_from_lists(hour_list, minute_list))
        minute_list.bind("<Double-Button-1>", lambda _e: self._set_time_and_close_from_lists(hour_list, minute_list))

        top.bind("<FocusOut>", lambda _e: self._close_time_popup())
        top.bind("<Escape>", lambda _e: self._close_time_popup())
        top.focus_set()
        top.update_idletasks()
        width = max(top.winfo_reqwidth(), 220)
        height = max(top.winfo_reqheight(), 210)
        top.geometry(f"{width}x{height}+{entry_x}+{entry_y}")
        self._time_popup = top

    def _set_time_and_close_from_lists(self, hour_list: tk.Listbox, minute_list: tk.Listbox):
        try:
            sel = hour_list.curselection()
            hour = int(hour_list.get(sel[0])) if sel else int(hour_list.get(0))
        except Exception:
            hour = 0
        try:
            sel = minute_list.curselection()
            minute = int(minute_list.get(sel[0])) if sel else int(minute_list.get(0))
        except Exception:
            minute = 0
        self.time_var.set(f"{hour:02d}:{minute:02d}")
        self._close_time_popup()

    def _close_time_popup(self):
        if self._time_popup is not None and self._time_popup.winfo_exists():
            self._time_popup.destroy()
        self._time_popup = None

    def _preset_minutes(self, minutes: int):
        t = now() + dt.timedelta(minutes=minutes)
        self.date_var.set(t.strftime("%Y-%m-%d"))
        self.time_var.set(t.strftime("%H:%M"))
        if DateEntry is not None:
            try:
                self.date_entry.set_date(t.date())
            except Exception:
                pass

    def add_task(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("Validación", "El título es obligatorio.")
            return
        d = f"{self.date_var.get().strip()} {self.time_var.get().strip()}"
        when = parse_datetime(d)
        if not when:
            messagebox.showwarning("Validación", "Fecha y hora inválidas. Formato: YYYY-MM-DD HH:MM")
            return
        t = Task(id=None, title=title, description=self.desc_var.get().strip(), scheduled_at=when, repeat=self.repeat_var.get(), enabled=True)
        add_task(t)
        notify("Tarea creada", f"{title} → {when.strftime('%Y-%m-%d %H:%M')}")
        self.title_var.set(""); self.desc_var.set(""); self.date_var.set(""); self.time_var.set("")
        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for t in list_tasks():
            self.tree.insert("", "end", iid=str(t.id), values=(t.scheduled_at.strftime("%Y-%m-%d %H:%M"), t.title, t.repeat, "Sí" if t.enabled else "No"))

    def _selected_task_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def toggle_task(self):
        tid = self._selected_task_id()
        if tid is None:
            return
        t = get_task(tid)
        if not t:
            return
        t.enabled = not t.enabled
        update_task(t)
        self.refresh()

    def delete_task(self):
        tid = self._selected_task_id()
        if tid is None:
            return
        if messagebox.askyesno("Confirmar", "¿Eliminar tarea?"):
            delete_task(tid)
            self.refresh()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("860x580")
        try:
            self.iconbitmap("")
        except Exception:
            pass

        style = ttk.Style(self)
        try:
            global WINDOWING_SYSTEM
            windowing = self.tk.call("tk", "windowingsystem")
            WINDOWING_SYSTEM = windowing
            if windowing == "aqua" and DateEntry is not None:
                style.theme_use("clam")
            elif windowing == "aqua":
                style.theme_use("aqua")
            else:
                style.theme_use("clam")
        except Exception:
            pass

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.timer_tab = TimerTab(nb)
        self.tabata_tab = TabataTab(nb)
        self.agenda_tab = AgendaTab(nb)

        nb.add(self.timer_tab, text="Timer")
        nb.add(self.tabata_tab, text="Tabata")
        nb.add(self.agenda_tab, text="Agenda")

        self.scheduler = Scheduler(poll_seconds=20)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.scheduler.start()

    def on_close(self):
        try:
            self.scheduler.stop()
        except Exception:
            pass
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
