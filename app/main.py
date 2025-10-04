from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from tkcalendar import DateEntry
except ImportError:  # pragma: no cover
    DateEntry = None
import datetime as dt

from .storage import add_task, list_tasks, update_task, delete_task, get_task, add_tabata_session, count_tabatas_on
from .models import Task
from .scheduler import Scheduler
from .notifications import notify
from .sounds import play as play_sound
from .utils import parse_datetime, now
from .integrations.google_sync import export_local_task_to_google

APP_TITLE = "Productivity Timer & Agenda"

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

        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=5, pady=5)

        ttk.Label(grid, text="Título").grid(row=0, column=0, sticky="w")
        ttk.Entry(grid, textvariable=self.title_var, width=40).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(grid, text="Descripción").grid(row=0, column=2, sticky="w")
        ttk.Entry(grid, textvariable=self.desc_var, width=40).grid(row=0, column=3, sticky="w", padx=5)

        ttk.Label(grid, text="Fecha").grid(row=1, column=0, sticky="w", pady=(6,0))
        if DateEntry is None:
            self.date_entry = ttk.Entry(grid, textvariable=self.date_var, width=16)
        else:
            self.date_entry = DateEntry(grid, textvariable=self.date_var, date_pattern="yyyy-mm-dd", width=16, showweeknumbers=False)
        self.date_entry.grid(row=1, column=1, sticky="w", padx=5, pady=(6,0))
        ttk.Label(grid, text="Hora (HH:MM)").grid(row=1, column=2, sticky="w", pady=(6,0))
        ttk.Entry(grid, textvariable=self.time_var, width=10).grid(row=1, column=3, sticky="w", padx=5, pady=(6,0))

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
            windowing = self.tk.call("tk", "windowingsystem")
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
