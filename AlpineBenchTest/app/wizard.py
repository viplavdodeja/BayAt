"""Cross-platform guided bench test interface."""
import copy
import time
import tkinter as tk
from tkinter import font as tkfont
from datetime import date, datetime
from tkinter import messagebox, ttk
from typing import Any

from .calculations import evaluate
from .storage import Store, load_config, now, validate_identifier

# Set False for workflow testing without waiting. Restore True for bench tests.
LOCK_FINAL_READINGS_UNTIL_TIMER_FINISHES = False


class Wizard(tk.Tk):
    def __init__(self):
        super().__init__()
        # Scale Tk's named fonts so themed controls and dialogs share the change.
        for name in tkfont.names(self):
            named_font = tkfont.nametofont(name, root=self)
            size = int(named_font.cget("size"))
            if size:
                named_font.configure(size=(1 if size > 0 else -1) * max(1, round(abs(size) * 1.2)))
        self.title("Alpine Assembly Bench Test")
        self.geometry("1000x820")
        self.minsize(760, 640)
        self.steps = load_config("test_steps.json")
        self.limits = load_config("acceptance_limits.json")
        self.store = Store()
        # Records come from JSON and contain mixed values (text, lists, flags,
        # measurements). Empty dictionaries represent no selected job/run yet.
        self.data: dict[str, Any] = {}
        self.run: dict[str, Any] = {}
        self.timer_token = None
        self.bind("<MouseWheel>", self.scroll_window)
        self.bind("<Button-4>", self.scroll_window)
        self.bind("<Button-5>", self.scroll_window)
        self.scroll_tag = f"AlpineScroll{id(self)}"
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_class(self.scroll_tag, sequence, self.scroll_window)
        if tk.TkVersion >= 8.7:
            self.bind_class(self.scroll_tag, "<TouchpadScroll>", self.scroll_touchpad)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.home()

    def clear(self, title, subtitle=""):
        if self.timer_token:
            self.after_cancel(self.timer_token)
            self.timer_token = None
        self.entry_step = None
        self.unbind("<Return>")
        self.unbind("<KP_Enter>")
        for child in self.winfo_children():
            child.destroy()
        ttk.Label(self, text=title, font=("Arial", 24, "bold")).pack(anchor="w", padx=24, pady=(20, 8))
        ttk.Label(self, text=subtitle, wraplength=920).pack(anchor="w", padx=24, pady=(0, 10))
        canvas = tk.Canvas(self, highlightthickness=0, yscrollincrement=12)
        self.canvas = canvas
        self.wheel_remainder = 0
        self.touchpad_remainder = 0
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        self.body = ttk.Frame(canvas, padding=24)
        window = canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        self.after_idle(self.install_scroll_bindings)

    def install_scroll_bindings(self):
        # Handle scrolling before widget-class bindings can consume the gesture.
        def install(widget):
            tags = widget.bindtags()
            if self.scroll_tag not in tags:
                widget.bindtags((self.scroll_tag, *tags))
            for child in widget.winfo_children():
                install(child)
        install(self.canvas)

    def scroll_touchpad(self, event):
        if event.widget.winfo_toplevel() != self:
            return
        bounds = self.canvas.bbox("all")
        if not bounds or bounds[3] - bounds[1] <= self.canvas.winfo_height():
            return
        # Tk 9 packs signed X/Y deltas into the high/low 16 bits, respectively.
        delta_y = int(event.delta) & 0xffff
        if delta_y >= 0x8000:
            delta_y -= 0x10000
        self.touchpad_remainder -= delta_y
        units = int(self.touchpad_remainder / 12)
        self.touchpad_remainder -= units * 12
        if units:
            self.canvas.yview_scroll(units, "units")
        return "break"

    def scroll_window(self, event):
        # Root bindings include child entries and labels, but ignore popup dialogs.
        if event.widget.winfo_toplevel() != self:
            return
        bounds = self.canvas.bbox("all")
        if not bounds or bounds[3] - bounds[1] <= self.canvas.winfo_height():
            return
        if getattr(event, "num", None) in (4, 5):
            units = -3 if event.num == 4 else 3
        else:
            delta = event.delta
            if self.tk.call("tk", "windowingsystem") == "aqua":
                units = -int(delta)
            else:
                self.wheel_remainder += delta
                notches = int(self.wheel_remainder / 120)
                self.wheel_remainder -= notches * 120
                units = -notches * 3
        if units:
            self.canvas.yview_scroll(units, "units")
        return "break"

    def button(self, text, action):
        def guarded():
            try:
                action()
            except (ValueError, OSError, KeyError) as error:
                messagebox.showerror("Unable to continue", str(error), parent=self)
        button = ttk.Button(self.body, text=text, command=guarded)
        button.pack(anchor="w", pady=8)
        return button

    def text(self, text):
        ttk.Label(self.body, text=text, wraplength=860, justify="left").pack(anchor="w", pady=5)

    def set_continue(self, button):
        self.continue_button = button
        self.bind("<Return>", self.continue_from_keyboard)
        self.bind("<KP_Enter>", self.continue_from_keyboard)

    def continue_from_keyboard(self, event):
        if event.widget.winfo_toplevel() != self:
            return
        button = self.continue_button
        if button.winfo_exists() and not button.instate(["disabled"]):
            button.invoke()
        return "break"

    def entry(self, label, value=""):
        self.text(label)
        variable = tk.StringVar(value=value)
        widget = ttk.Entry(self.body, textvariable=variable, width=42)
        widget.pack(anchor="w", pady=(0, 8))
        return variable

    def persist(self):
        self.store.save(self.data)
        self.warn_export()

    def warn_export(self):
        if self.store.export_error:
            messagebox.showwarning("Records saved; Excel not updated",
                "Test records were saved, but the analytics workbook could not be updated. "
                "Close the workbook in Excel and save again, or regenerate it later.\n\n" + self.store.export_error, parent=self)

    def mutate(self, action):
        previous = copy.deepcopy(self.run)
        try:
            action()
            self.persist()
        except Exception:
            self.run.clear()
            self.run.update(previous)
            raise

    def home(self):
        self.clear("Start a bench test", "Test records and analytics update after each completed screen.")
        self.text("Results destination: " + str(self.store.root))
        self.job = self.entry("Job number")
        self.serial = self.entry("Unit serial number")
        self.test_date = self.entry("Test date (YYYY-MM-DD)", date.today().isoformat())
        self.set_continue(self.button("Start / resume", self.start))

    def start(self):
        job = validate_identifier(self.job.get(), "Job number")
        serial = validate_identifier(self.serial.get(), "Serial number")
        selected_date = datetime.strptime(self.test_date.get().strip(), "%Y-%m-%d").date().isoformat()
        data = self.store.load(job)
        active = [r for r in data["runs"] if r["status"] == "In progress"]
        if active:
            candidate = active[-1]
            if candidate["serial"].casefold() != serial.casefold():
                raise ValueError("An unfinished run exists for serial " + candidate["serial"] + ". Resume that serial and complete or yellow-tag it before starting another unit.")
            if not messagebox.askyesno("Resume test", "Resume the unfinished test for this unit? Its original date and run ID will be retained."):
                return
            self.data, self.run = data, candidate
        else:
            previous = [r for r in data["runs"] if r["serial"].casefold() == serial.casefold()]
            if previous and not messagebox.askyesno("Confirm re-test", f"This unit has {len(previous)} previous test run(s) under this job. Create test {len(previous) + 1}? Previous records will be preserved."):
                return
            self.run = self.store.new_run(data, serial, selected_date)
            self.data = data
            self.warn_export()
        self.show_current()

    def show_current(self):
        if self.run["pending_failure"]:
            self.failure()
        elif self.run.get("retry_needs_zero"):
            self.retry_confirmation()
        elif self.run.get("awaiting_zero"):
            self.zero_screen(self.steps[self.run["step_index"]])
        elif self.run["step_index"] >= len(self.steps):
            self.review()
        else:
            self.screen()

    def screen(self):
        step = self.steps[self.run["step_index"]]
        self.clear(step["title"], f"Job {self.data['job']} • Serial {self.run['serial']} • Test {self.run['test_number']} • {self.run['date']}")
        for index, instruction in enumerate(step["instructions"], 1):
            self.text(f"{index}. {instruction}")
        if step["kind"] == "decay":
            self.text("Decay limits: " + "; ".join(f"{s} < {self.limits['decay'][s]} {'psi' if s not in ['QDM5', 'QDF22', 'QDF3'] else 'mmHg'}/min" for s in step["sensors"]))
            self.setup_timer()
        self.variables = {}
        self.field_widgets = {}
        self.entry_step = step["id"]
        draft = self.run.get("draft", {})
        saved_fields = draft.get("values", {}) if draft.get("step") == step["id"] else {}
        for field in step["fields"]:
            if field["type"] == "check":
                variable = tk.BooleanVar(value=bool(saved_fields.get(field["id"], False)))
                ttk.Checkbutton(self.body, text=field["label"], variable=variable).pack(anchor="w", pady=6)
                self.variables[field["id"]] = variable
            else:
                self.text(field["label"])
                # Final decay readings must be taken again after a resumed timer.
                saved = "" if step["kind"] == "decay" and field["id"].endswith("_final") else saved_fields.get(field["id"], "")
                variable = tk.StringVar(value=saved)
                widget = ttk.Entry(self.body, textvariable=variable, width=30)
                widget.pack(anchor="w", pady=4)
                self.variables[field["id"]] = variable
                self.field_widgets[field["id"]] = widget
                if step["kind"] == "decay" and field["id"].endswith("_final") and LOCK_FINAL_READINGS_UNTIL_TIMER_FINISHES:
                    widget.configure(state="disabled")
        if step["kind"] == "decay":
            self.submit = self.button("Evaluate final readings", self.submit_step)
            if LOCK_FINAL_READINGS_UNTIL_TIMER_FINISHES:
                self.submit.configure(state="disabled")
            else:
                self.set_continue(self.submit)
        else:
            self.set_continue(self.button("Record and continue", self.submit_step))
        self.run_controls()

    def setup_timer(self):
        self.started = None
        self.timer_complete = not LOCK_FINAL_READINGS_UNTIL_TIMER_FINISHES
        label = "Timer ready — complete fill and settling first." if LOCK_FINAL_READINGS_UNTIL_TIMER_FINISHES else "Workflow testing — timer lock bypassed; calculations assume 60 seconds."
        self.timer_label = ttk.Label(self.body, text=label, font=("Arial", 14, "bold"))
        self.timer_label.pack(anchor="w", pady=8)
        if not LOCK_FINAL_READINGS_UNTIL_TIMER_FINISHES:
            return
        self.timer_button = self.button("Start 60-second measurement timer", self.start_timer)
        self.set_continue(self.timer_button)

    def start_timer(self):
        if self.started is not None:
            return
        self.started = time.monotonic()
        self.timer_button.configure(state="disabled")
        self.set_continue(self.submit)
        self.timer_tick()

    def timer_tick(self):
        started = self.started
        if started is None:
            return
        elapsed = time.monotonic() - started
        remaining = max(0, 60 - int(elapsed))
        if elapsed < 60:
            self.timer_label.configure(text=f"Measurement timer: {remaining} seconds remaining — enter initial readings.")
            self.timer_token = self.after(250, self.timer_tick)
            return
        self.timer_token = None
        self.timer_complete = True
        self.timer_label.configure(text="60 seconds complete — enter final readings. Initial readings remain editable.")
        for key, widget in self.field_widgets.items():
            if key.endswith("_final"):
                widget.configure(state="normal")
        self.submit.configure(state="normal")

    def submit_step(self):
        step = self.steps[self.run["step_index"]]
        values = {key: var.get() for key, var in self.variables.items()}
        if step["kind"] == "decay":
            if not self.timer_complete:
                raise ValueError("Start the measurement timer and wait for it to finish first.")
            values["elapsed_seconds"] = 60
        results, failures = evaluate(step, values, self.limits)
        attempt = {"step": step["id"], "title": step["title"], "recorded_at": now(),
                   "values": results, "failures": failures, "passed": not failures}
        if step["kind"] == "decay":
            attempt["timer_bypassed"] = not LOCK_FINAL_READINGS_UNTIL_TIMER_FINISHES
        def update():
            self.run.pop("draft", None)
            self.run["attempts"].append(attempt)
            self.run["pending_failure"] = bool(failures)
            if failures:
                self.run["notes"].append("Previous failure at " + step["title"] + ": " + "; ".join(failures))
            else:
                self.run["awaiting_zero"] = step["id"] != "prep"
                if step["id"] == "prep":
                    self.run["step_index"] += 1
        self.mutate(update)
        if failures:
            self.failure()
        elif step["id"] == "prep":
            self.show_current()
        else:
            self.zero_screen(step)

    def zero_screen(self, step):
        self.clear("Clear pressure and confirm zero")
        self.text(step["cleanup"] or "Clear air before continuing. Follow the ER1 reset instructions on the next screen.")
        self.text("Confirm the relevant sensor readings are zero before the next stage. For vacuum tests, confirm QDF3, QDM1 and QDF19 are all zero.")
        self.set_continue(self.button("Confirm zero — continue (Enter)", self.confirm_zero))
        self.run_controls()

    def confirm_zero(self):
        def update():
            self.run["zero_confirmations"].append({"after_step": self.steps[self.run["step_index"]]["id"], "at": now()})
            self.run["awaiting_zero"] = False
            self.run["step_index"] += 1
        try:
            self.mutate(update)
            self.show_current()
        except OSError as error:
            messagebox.showerror("Unable to save", str(error))

    def failure(self):
        attempt = self.run["attempts"][-1]
        self.clear("Test failed — troubleshoot before continuing", attempt["title"])
        for failure in attempt["failures"]:
            self.text("• " + failure)
        step = self.steps[self.run["step_index"]]
        self.text(step["cleanup"] or "Clear pressure before troubleshooting.")
        self.text("Check fixture connections, tubing, settings and the unit. Retry repeats this stage and retains the failed readings.")
        self.set_continue(self.button("Retry this stage", self.retry))
        self.run_controls()

    def retry(self):
        self.mutate(lambda: self.run.update(pending_failure=False, awaiting_zero=False, retry_needs_zero=True))
        self.retry_confirmation()

    def retry_confirmation(self):
        self.clear("Confirm zero before retry")
        self.text("Clear pressure and confirm the relevant sensors read zero before restarting the failed stage.")
        self.set_continue(self.button("Confirm zero — restart failed stage", self.retry_zero))
        self.run_controls()

    def retry_zero(self):
        def update():
            self.run["zero_confirmations"].append({"before_retry": self.steps[self.run["step_index"]]["id"], "at": now()})
            self.run["retry_needs_zero"] = False
        self.mutate(update)
        self.screen()

    def run_controls(self):
        self.button("Save / Quit", self.save_quit)
        self.button("Yellow-tag unit / close run as Fail", self.yellow_tag)

    def save_draft(self):
        if self.entry_step is not None:
            self.run["draft"] = {"step": self.entry_step,
                                 "values": {key: var.get() for key, var in self.variables.items()}}
        elif hasattr(self, "notes") and self.run["step_index"] >= len(self.steps):
            note = self.notes.get().strip()
            if note:
                self.run["notes"].append(note)
                self.notes.set("")

    def saved_exit_prompt(self):
        if messagebox.askyesno("Test run saved", "Test run has been saved. Do you want to exit?", parent=self):
            self.destroy()
            return True
        return False

    def save_quit(self):
        self.mutate(self.save_draft)
        self.saved_exit_prompt()

    def yellow_tag(self):
        if not messagebox.askyesno("Confirm yellow tag", "Have you yellow-tagged this unit? Close this run as Fail?", parent=self):
            return
        def update():
            self.save_draft()
            self.run.update(status="Complete", decision="Fail", completed_at=now(), pending_failure=False)
            index = self.run["step_index"]
            stage = self.steps[index]["title"] if index < len(self.steps) else "Final review"
            self.run["notes"].append("Unit yellow-tagged at " + stage + ".")
        self.mutate(update)
        if not self.saved_exit_prompt():
            self.home()

    def review(self):
        self.clear("Review and finish", "All required stages passed. Previous failures are retained in notes and attempt history.")
        for attempt in self.run["attempts"]:
            self.text(attempt["title"] + " — " + ("Pass" if attempt["passed"] else "Fail"))
            self.text("; ".join(f"{k}: {v}" for k, v in attempt["values"].items()))
        for note in self.run["notes"]:
            self.text(note)
        self.notes = self.entry("Additional notes (optional)")
        self.text("Add the part label sticker and Bench Test Pass post-it; approve this unit for console testing.")
        self.set_continue(self.button("Confirm labeling / finish as Pass", self.finish))
        self.run_controls()

    def finish(self):
        def update():
            if self.notes.get().strip():
                self.run["notes"].append(self.notes.get().strip())
            self.run.update(status="Complete", decision="Pass", completed_at=now())
        self.mutate(update)
        messagebox.showinfo("Run saved", "Run completed as Pass. Records saved to " + str(self.store.job_path(self.data["job"])) + "\nAnalytics is in the Analysis folder. Any export failure is reported separately.")
        self.home()

    def close(self):
        if self.run and self.run["status"] == "In progress":
            if not messagebox.askyesno("Close wizard", "Completed screens are saved. Unsubmitted readings on this screen will be discarded. Close?"):
                return
        self.destroy()
