import os
import json
import time
import threading
import queue
import customtkinter as ctk
import sorter

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.abspath(os.path.join(APP_DIR, "config.json"))
FOLDER_NAMES = {"image": "Bilder", "doc": "Dokumente",
                "music": "Musik", "video": "Videos", "app": "Anwendungen"}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


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


class App(ctk.CTk):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.jobs = queue.Queue()
        self.dl = cfg["dl"]
        self.last = []
        self.last_poll = time.time()
        self.tray = None

        self.title("Downsort - Download-Auto-Sorter")
        self.geometry("600x560")
        self.minsize(520, 460)
        self.configure(fg_color="#121212")
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        self.build_ui()
        self.refresh_last()
        self.after(150, self.pump)
        self._start_tray()
        threading.Thread(target=self.background, daemon=True).start()

        self.log("Downsort startklar - App laeuft im Hintergrund (Tray).")

    # ---------- UI ----------
    def build_ui(self):
        ctk.CTkLabel(self, text="Downsort - Download-Auto-Sorter",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#4fc3f7").pack(pady=(18, 6))

        ctk.CTkLabel(self, text="Download-Ordner:",
                     anchor="w").pack(fill="x", padx=20)
        self.e_dl = ctk.CTkEntry(self, placeholder_text="Pfad zum Download-Ordner")
        self.e_dl.insert(0, self.dl)
        self.e_dl.pack(fill="x", padx=20, pady=(2, 8))

        # options card
        card = ctk.CTkFrame(self, fg_color="#1b1b1b", corner_radius=12)
        card.pack(fill="x", padx=20, pady=(0, 8))

        self.v_iv = ctk.BooleanVar(value=bool(self.cfg["iv"]))
        self.v_new = ctk.BooleanVar(value=bool(self.cfg["new"]))

        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkCheckBox(row1, text="Automatisch sortieren (Intervall):",
                        variable=self.v_iv).pack(side="left")
        self.e_min = ctk.CTkEntry(row1, width=70, justify="center")
        self.e_min.insert(0, str(self.cfg["min"]))
        self.e_min.pack(side="left", padx=(10, 4))
        ctk.CTkLabel(row1, text="Minuten",
                     text_color="#888888").pack(side="left")

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkCheckBox(row2, text="Sortieren bei neuen Dateien",
                        variable=self.v_new).pack(side="left")

        # action bar
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(4, 6))
        ctk.CTkButton(bar, text="Jetzt sortieren", command=self.now,
                      fg_color="#2e7d32", hover_color="#388e3c").pack(side="left")
        ctk.CTkButton(bar, text="Einstellungen speichern",
                      command=self.save_settings).pack(side="left", padx=10)
        ctk.CTkButton(bar, text="In Tray minimieren",
                      command=self.hide_to_tray,
                      fg_color="#37474f", hover_color="#455a64").pack(side="left")

        self.status = ctk.CTkLabel(self, text="Bereit.",
                                   text_color="#66bb6a", anchor="w")
        self.status.pack(fill="x", padx=20)

        # log area
        body = ctk.CTkFrame(self, fg_color="#0e0e0e", corner_radius=10)
        body.pack(fill="both", expand=True, padx=20, pady=(6, 16))
        self.text = ctk.CTkTextbox(body, fg_color="#0e0e0e",
                                   text_color="#dcdcdc", wrap="word",
                                   font=ctk.CTkFont(family="Consolas", size=12),
                                   border_width=0)
        self.text.pack(fill="both", expand=True, padx=6, pady=6)

    # ---------- actions ----------
    def now(self):
        self.jobs.put("now")

    def save_settings(self):
        path = self.e_dl.get().strip().replace("\\", "/")
        if path:
            self.cfg["dl"] = path
        try:
            self.cfg["min"] = int(self.e_min.get().strip() or 30)
        except ValueError:
            self.cfg["min"] = 30
        self.cfg["iv"] = int(self.v_iv.get())
        self.cfg["new"] = int(self.v_new.get())
        save_config(self.cfg)
        self.status.configure(text="Einstellungen gespeichert.")
        self.dl = self.cfg["dl"]
        self.refresh_last()
        self._tray_menu()  # refresh tray

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
                elif job == "quit":
                    self._quit()
                    return
        except queue.Empty:
            pass
        self.after(200, self.pump)

    def do_sort(self):
        try:
            count = self.run_sort()
            self.status.configure(text="Zuletzt sortiert: %d Datei(en)" % count)
            if count > 0:
                stamp = time.strftime("%H:%M:%S")
                self.log("%s: %d Datei(en) einsortiert." % (stamp, count))
        except Exception as exc:
            self.status.configure(text="Fehler: %s" % exc)
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
        return count

    def log(self, msg):
        self.text.insert("end", msg + "\n")
        self.text.see("end")

    # ---------- background ----------
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
        interval = int(self.e_min.get().strip() or 30) * 60
        if self.v_iv.get() and time.time() - self.last_poll >= interval:
            self.last_poll = time.time()
            self.jobs.put("now")

    def background(self):
        while True:
            self.check_auto()
            time.sleep(2)

    # ---------- tray ----------
    def _start_tray(self):
        import pystray
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (64, 64), "#121212")
        d = ImageDraw.Draw(img)
        d.ellipse([8, 8, 56, 56], fill="#4fc3f7")
        d.text((20, 20), "D", fill="#121212")
        self._tray_img = img
        self.tray = pystray.Icon("downsort", img, "Downsort", menu=self._tray_menu())
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _tray_menu(self):
        import pystray
        from pystray import MenuItem as Item
        def _show():
            self.after(0, self._show_from_tray)
        def _now():
            self.after(0, self.now)
        def _quit():
            self.after(0, lambda: self.jobs.put("quit"))
        return pystray.Menu(
            Item("Downsort", None, enabled=False),
            Item("Fenster zeigen", _show),
            Item("Jetzt sortieren", _now),
            Item("Beenden", _quit),
        )

    def hide_to_tray(self):
        self.withdraw()
        self.status.configure(text="Im Hintergrund aktiv (Tray).")

    def _show_from_tray(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _quit(self):
        if self.tray:
            self.tray.stop()
        self.destroy()
        self.quit()


def main():
    app = App(load_config())
    app.mainloop()


if __name__ == "__main__":
    main()