import os
import json
import time
import threading
import queue
import tkinter as tk
from tkinter import ttk, colorchooser
import sorter

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.abspath(os.path.join(APP_DIR, "config.json"))
FOLDER_NAMES = {"image": "Bilder", "doc": "Dokumente",
                "music": "Musik", "video": "Videos", "app": "Anwendungen"}

DEFAULT_COLORS = {
    "bg": "#1e1e1e",
    "fg": "#eeeeee",
    "accent": "#4fc3f7",
    "log_bg": "#121212",
    "log_fg": "#dcdcdc",
    "status_ok": "#4caf50",
}


def default_config():
    user = os.getenv("USERNAME", "Friedrich")
    dl = os.path.join("C:/Users", user, "Downloads").replace("\\", "/")
    return {"dl": dl, "min": 30, "iv": 1, "new": 1,
            "paths": {}, "colors": dict(DEFAULT_COLORS)}


def load_config():
    cfg = default_config()
    try:
        with open(CFG, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
        cfg.update(saved)
        cfg.setdefault("paths", {})
        merged = dict(DEFAULT_COLORS)
        merged.update(cfg.get("colors", {}))
        cfg["colors"] = merged
    except Exception:
        pass
    return cfg


def save_config(cfg):
    with open(CFG, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)


class App:
    def __init__(self, cfg):
        self.cfg = cfg
        self.jobs = queue.Queue()
        self.dl = cfg["dl"]
        self.last = []
        self.last_poll = time.time()

        self.root = tk.Tk()
        self.root.title("Downsort - Download-Auto-Sorter")
        self.root.geometry("560x520")
        self.apply_colors(self.cfg["colors"])

        self.build_ui()
        self.apply_colors(self.cfg["colors"])
        self.refresh_last()
        self.root.after(150, self.pump)
        threading.Thread(target=self.background, daemon=True).start()

    def apply_colors(self, c):
        self.root.configure(bg=c["bg"])
        self.recolor_tree(self.root, c)

    def recolor_tree(self, widget, c):
        for child in widget.winfo_children():
            try:
                if isinstance(child, tk.Text):
                    child.configure(bg=c["log_bg"], fg=c["log_fg"])
                elif isinstance(child, ttk.Label):
                    cur = child.cget("text")
                    if cur.startswith("Downsort"):
                        fg = c["accent"]
                    elif cur == "Bereit.":
                        fg = c["status_ok"]
                    else:
                        fg = c["fg"]
                    child.configure(background=c["bg"], foreground=fg)
                else:
                    try:
                        child.configure(background=c["bg"])
                    except tk.TclError:
                        pass
                self.recolor_tree(child, c)
            except tk.TclError:
                pass

    def build_ui(self):
        c = self.cfg["colors"]
        bg = c["bg"]
        ttk.Label(self.root, text="Downsort - Download-Auto-Sorter",
                  font=("Segoe UI", 14, "bold"), background=bg,
                  foreground=c["accent"]).pack(pady=8)
        ttk.Label(self.root, text="Download-Ordner:",
                  background=bg, foreground=c["fg"]).pack(anchor="w", padx=14)
        self.e_dl = ttk.Entry(self.root, width=64)
        self.e_dl.insert(0, self.dl)
        self.e_dl.pack(padx=14, pady=2, fill="x")

        self.v_iv = tk.BooleanVar(value=bool(self.cfg["iv"]))
        self.v_new = tk.BooleanVar(value=bool(self.cfg["new"]))
        self.v_min = tk.StringVar(value=str(self.cfg["min"]))

        opts = ttk.Frame(self.root)
        opts.pack(padx=14, pady=6, anchor="w")
        ttk.Checkbutton(opts, text="Automatisch sortieren (Intervall):",
                        variable=self.v_iv).grid(row=0, column=0, sticky="w")
        ttk.Spinbox(opts, from_=1, to=1440, width=5,
                    textvariable=self.v_min).grid(row=0, column=1, padx=4)
        ttk.Label(opts, text="Minuten", background=bg,
                  foreground="#cccccc").grid(row=0, column=2, sticky="w")
        ttk.Checkbutton(opts, text="Sortieren bei neuen Dateien",
                        variable=self.v_new).grid(row=1, column=0, columnspan=3, sticky="w")

        head = ttk.Frame(self.root)
        head.pack(pady=6)
        ttk.Button(head, text="Jetzt sortieren",
                   command=self.now).pack(side="left", padx=4)
        ttk.Button(head, text="Einstellungen speichern",
                   command=self.save_settings).pack(side="left", padx=4)
        ttk.Button(head, text="Einstellungen (Erweitert)...",
                   command=self.open_preferences).pack(side="left", padx=4)

        self.status = ttk.Label(self.root, text="Bereit.",
                                background=bg, foreground=c["status_ok"])
        self.status.pack(pady=4)

        body = ttk.Frame(self.root)
        body.pack(padx=14, pady=4, fill="both", expand=True)
        self.text = tk.Text(body, bg=c["log_bg"], fg=c["log_fg"],
                            insertbackground="#ffffff", wrap="word",
                            height=14, borderwidth=0)
        self.text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(body, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log("Downsort startklar. Die App laeuft im Hintergrund.")

    def now(self):
        self.jobs.put("now")

    def save_settings(self):
        path = self.e_dl.get().strip().replace("\\", "/")
        if path:
            self.cfg["dl"] = path
        try:
            self.cfg["min"] = int(self.v_min.get() or 30)
        except ValueError:
            self.cfg["min"] = 30
        self.cfg["iv"] = int(self.v_iv.get())
        self.cfg["new"] = int(self.v_new.get())
        save_config(self.cfg)
        self.status.config(text="Einstellungen gespeichert.")
        self.dl = self.cfg["dl"]

    # ---- Preferences dialog ----
    def open_preferences(self):
        win = tk.Toplevel(self.root)
        win.title("Einstellungen (Erweitert)")
        win.configure(bg=self.cfg["colors"]["bg"])
        win.transient(self.root)
        win.geometry("460x460")

        box = ttk.Labelframe(win, text="Ziel-Ordner pro Kategorie (leer = Standard in Downloads)")
        box.pack(fill="x", padx=12, pady=8)

        paths_vars = {}
        for cat, label in FOLDER_NAMES.items():
            row = ttk.Frame(box)
            row.pack(fill="x", padx=6, pady=2)
            ttk.Label(row, text=label, width=12).pack(side="left")
            var = tk.StringVar(value=self.cfg["paths"].get(cat, ""))
            paths_vars[cat] = var
            ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=2)
            ttk.Button(row, text="...",
                       command=lambda v=var: self.browse_dir(v)).pack(side="left", padx=2)

        col_box = ttk.Labelframe(win, text="Farben")
        col_box.pack(fill="x", padx=12, pady=8)
        color_names = {
            "bg": "Hintergrund",
            "fg": "Text",
            "accent": "Akzent (Titel)",
            "log_bg": "Log-Hintergrund",
            "log_fg": "Log-Text",
            "status_ok": "Status-Text",
        }
        col_vars = {}
        for key, label in color_names.items():
            row = ttk.Frame(col_box)
            row.pack(fill="x", padx=6, pady=2)
            var = tk.StringVar(value=self.cfg["colors"].get(key, DEFAULT_COLORS[key]))
            col_vars[key] = var
            swatch = tk.Label(row, text="      ", bg=var.get(), width=6)
            swatch.pack(side="left", padx=2)
            ttk.Label(row, text=label, width=14).pack(side="left")
            ttk.Entry(row, textvariable=var, width=10).pack(side="left", padx=2)
            ttk.Button(row, text="Wählen...",
                       command=lambda k=key, v=var, s=swatch: self.pick_color(v, s)).pack(side="left", padx=2)

        hint = "Standard-Analyse: ohne Auswahl wird der Standard in Downloads benutzt,\n" \
               "z.B. C:/Users/<Name>/Downloads/Bilder. Tragen Sie hier einen festen Ordner ein."
        ttk.Label(win, text=hint, foreground="#999999").pack(pady=4, padx=12)

        btns = ttk.Frame(win)
        btns.pack(pady=10)
        ttk.Button(btns, text="Speichern & Schließen",
                   command=lambda: self.save_preferences(win, paths_vars, col_vars)).pack(side="left", padx=4)
        ttk.Button(btns, text="Abbrechen",
                   command=win.destroy).pack(side="left", padx=4)

    def browse_dir(self, var):
        from tkinter import filedialog
        start = var.get() or os.path.expanduser("~")
        chosen = filedialog.askdirectory(parent=None, initialdir=start,
                                         title="Ordner auswählen")
        if chosen:
            var.set(chosen.replace("\\", "/"))

    def pick_color(self, var, swatch):
        _, hexcol = colorchooser.askcolor(color=var.get(), title="Farbe wählen")
        if hexcol:
            var.set(hexcol)
            swatch.config(bg=hexcol)

    def save_preferences(self, win, paths_vars, col_vars):
        paths = {}
        for cat, v in paths_vars.items():
            p = v.get().strip().replace("\\", "/")
            paths[cat] = p
        self.cfg["paths"] = paths

        colors = dict(self.cfg["colors"])
        for key, v in col_vars.items():
            val = v.get().strip()
            if val:
                colors[key] = val
        self.cfg["colors"] = colors
        save_config(self.cfg)
        self.apply_colors(colors)
        win.destroy()
        self.status.config(text="Einstellungen (Erweitert) gespeichert.")

    # ---- sorting ----
    def refresh_last(self):
        if self.dl and os.path.isdir(self.dl):
            self.last = os.listdir(self.dl)
        else:
            self.last = []

    def pump(self):
        try:
            while True:
                job = self.jobs.get_nowait()
                if job == "now":
                    self.do_sort()
        except queue.Empty:
            pass
        self.root.after(150, self.pump)

    def do_sort(self):
        try:
            count = self.run_sort()
            self.status.config(text="Zuletzt sortiert: %d Datei(en)" % count)
            if count > 0:
                stamp = time.strftime("%H:%M:%S")
                self.log("%s: %d Datei(en) einsortiert." % (stamp, count))
        except Exception as exc:
            self.status.config(text="Fehler: %s" % exc)
            self.log(str(exc))
        self.refresh_last()

    def run_sort(self):
        dl = self.e_dl.get().strip().replace("\\", "/")
        if not dl or not os.path.isdir(dl):
            raise FileNotFoundError("Ordner nicht gefunden: %s" % dl)
        target = {}
        for key, name in FOLDER_NAMES.items():
            custom = self.cfg.get("paths", {}).get(key, "").strip()
            if custom:
                target[key] = custom.replace("\\", "/")
            else:
                target[key] = os.path.join(dl, name)
        count = 0
        for item in sorter.sort_downloads(dl, target):
            self.log("  %s  %s  %s" % (item["category"], item["name"], item["size"]))
            count += 1
        if count:
            self.text.see("end")
        return count

    def log(self, msg):
        self.text.insert("end", msg + "\n")
        self.text.see("end")

    def check_auto(self):
        if not self.dl or not os.path.isdir(self.dl):
            return
        try:
            now = os.listdir(self.dl)
        except OSError:
            return
        if self.v_new.get() and set(now) - set(self.last):
            self.jobs.put("now")
        self.last = now
        interval = int(self.v_min.get() or 30) * 60
        if self.v_iv.get() and time.time() - self.last_poll >= interval:
            self.last_poll = time.time()
            self.jobs.put("now")

    def background(self):
        while True:
            self.check_auto()
            time.sleep(2)


def main():
    app = App(load_config())
    app.root.mainloop()


if __name__ == "__main__":
    main()