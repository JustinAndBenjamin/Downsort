import os
import json
import time
import threading
import queue
import tkinter as tk
from tkinter import ttk
import sorter

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.abspath(os.path.join(APP_DIR, "config.json"))
FOLDER_NAMES = {"image": "Bilder", "doc": "Dokumente",
                "music": "Musik", "video": "Videos", "app": "Anwendungen"}

def default_config():
    user = os.getenv("USERNAME", "Friedrich")
    dl = os.path.join("C:/Users", user, "Downloads").replace("\\", "/")
    return {"dl": dl, "min": 30, "iv": 1, "new": 1}

def load_config():
    cfg = default_config()
    try:
        with open(CFG, "r", encoding="utf-8") as fh:
            cfg.update(json.load(fh))
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
        self.root.configure(bg="#1e1e1e")

        self.build_ui()
        self.refresh_last()
        self.root.after(150, self.pump)
        threading.Thread(target=self.background, daemon=True).start()

    def build_ui(self):
        bg = "#1e1e1e"
        ttk.Label(self.root, text="Downsort - Download-Auto-Sorter",
                  font=("Segoe UI", 14, "bold"), background=bg,
                  foreground="#4fc3f7").pack(pady=8)
        ttk.Label(self.root, text="Download-Ordner:",
                  background=bg, foreground="#eeeeee").pack(anchor="w", padx=14)
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

        self.status = ttk.Label(self.root, text="Bereit.",
                                background=bg, foreground="#4caf50")
        self.status.pack(pady=4)

        body = ttk.Frame(self.root)
        body.pack(padx=14, pady=4, fill="both", expand=True)
        self.text = tk.Text(body, bg="#121212", fg="#dcdcdc",
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
        target = {key: os.path.join(dl, name) for key, name in FOLDER_NAMES.items()}
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
