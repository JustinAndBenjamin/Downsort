"""Downsort - Download-Auto-Sorter.

Modern customtkinter GUI for keeping your Downloads folder tidy.
Sorts files into per-category folders (Bilder / Dokumente / Musik / Videos /
Anwendungen), optionally fully automatic (interval and/or on-new-file).
"""

import os
import json
import time
import queue
import threading
import tkinter as tk

import customtkinter as ctk

import sorter  # sorting logic lives here (no GUI)

# -------- paths & constants -------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CFG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Downsort")
os.makedirs(CFG_DIR, exist_ok=True)
CFG = os.path.join(CFG_DIR, "config.json")

FOLDER_NAMES = {
    "image": "Bilder",
    "doc": "Dokumente",
    "music": "Musik",
    "video": "Videos",
    "app": "Anwendungen",
}

# customtkinter ships these accent themes (see customtkinter/assets/themes/)
ACCENT_PRESETS = ["blue", "dark-blue", "green", "gold"]
ACCENT_LABELS = {
    "blue": "Blau",
    "dark-blue": "Dunkelblau",
    "green": "Grün",
    "gold": "Gold",
}
APPEARANCE_LABELS = {"dark": "Dunkel", "light": "Hell", "system": "System"}


# -------- config ------------------------------------------------------------
def default_config():
    dl = os.path.join(os.path.expanduser("~"), "Downloads").replace("\\", "/")
    return {"dl": dl, "min": 30, "iv": True, "new": True,
            "paths": {}, "appearance": "dark", "accent": "blue"}


def _migrate_from_legacy(cfg):
    """If a repo-adjacent config.json exists (old versions), import it once so
    the user's settings aren't lost after moving to %APPDATA%."""
    legacy = os.path.abspath(os.path.join(APP_DIR, "config.json"))
    if os.path.isfile(legacy) and not os.path.isfile(CFG):
        try:
            with open(legacy, "r", encoding="utf-8") as fh:
                cfg.update(json.load(fh))
        except Exception:
            pass


def load_config():
    cfg = default_config()
    _migrate_from_legacy(cfg)
    try:
        with open(CFG, "r", encoding="utf-8") as fh:
            cfg.update(json.load(fh))
    except Exception:
        pass
    cfg.setdefault("paths", {})
    # narrow appearance/accent to supported values
    if cfg.get("appearance") not in APPEARANCE_LABELS:
        cfg["appearance"] = "dark"
    return cfg


def save_config(cfg):
    with open(CFG, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)


# -------- custom accent theme ----------------------------------------------
def _hex_darken(hexcol, factor=0.55):
    hexcol = hexcol.lstrip("#")
    if len(hexcol) != 6:
        return hexcol
    r, g, b = (int(hexcol[i:i + 2], 16) for i in (0, 2, 4))
    return "#" + "".join("%02X" % max(0, int(ch * factor)) for ch in (r, g, b))


def write_custom_theme(hexcol):
    """Build a small customtkinter theme json from a custom accent color and
    return its path. set_default_color_theme() accepts that path."""
    base = os.path.join(os.path.dirname(ctk.__file__), "assets", "themes", "blue.json")
    with open(base, "r", encoding="utf-8") as fh:
        theme = json.load(fh)
    dark = _hex_darken(hexcol)

    def swap(obj):
        if isinstance(obj, dict):
            return {k: swap(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [swap(v) for v in obj]
        if obj == "#3B8ED0":
            return hexcol
        if obj == "#1F6AA5":
            return dark
        if obj == "#36719F":
            return _hex_darken(hexcol, 0.8)
        return obj

    theme = swap(theme)
    out = os.path.join(CFG_DIR, "accent.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(theme, fh)
    return out


def apply_ctk_theme(cfg):
    ctk.set_appearance_mode(cfg.get("appearance", "dark"))
    accent = cfg.get("accent", "blue")
    if accent and not accent.startswith("#"):
        ctk.set_default_color_theme(accent)  # built-in preset name
    else:
        ctk.set_default_color_theme(write_custom_theme(accent or "#3B8ED0"))


# -------- application -------------------------------------------------------
class App:
    def __init__(self, cfg):
        self.cfg = cfg
        self.jobs = queue.Queue()
        self._worker_state = {"dl": cfg["dl"], "min": int(cfg.get("min", 30)),
                              "iv": bool(cfg.get("iv", True)),
                              "new": bool(cfg.get("new", True))}
        self._last = []
        self._last_poll = time.time()
        self._settings_built = False

        self.root = ctk.CTk()
        self.root.title("Downsort - Download-Auto-Sorter")
        self.root.geometry("720x560")
        self.root.minsize(680, 520)

        self._build_sort_tab()
        threading.Thread(target=self._background, daemon=True).start()
        self.root.after(150, self._pump)

    # ---- shared helpers ----------------------------------------------------
    @staticmethod
    def _card(parent, title):
        card = ctk.CTkFrame(parent)
        card.pack(fill="x", padx=16, pady=(6, 8))
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=("gray20", "gray90")).pack(anchor="w", padx=12, pady=(8, 4))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=12, pady=(0, 8))
        return body

    def _sort_targets(self):
        dl = self._worker_state["dl"]
        target = {}
        for key, name in FOLDER_NAMES.items():
            custom = str(self.cfg.get("paths", {}).get(key, "") or "").strip()
            target[key] = custom.replace("\\", "/") if custom else os.path.join(dl, name)
        return dl, target

    # ---- tab 1: Sortieren (built on startup for a fast first paint) --------
    def _build_sort_tab(self):
        self.tabs = ctk.CTkTabview(self.root)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)
        self.t1 = self.tabs.add("Sortieren")
        self.tab_settings = self.tabs.add("Einstellungen")
        self.tabs.configure(command=self._on_tab_change)

        # source folder
        body = self._card(self.t1, "📥 Download-Ordner")
        self.e_dl = ctk.CTkEntry(body, placeholder_text="Pfad zum Download-Ordner")
        self.e_dl.insert(0, self.cfg["dl"])
        self.e_dl.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(body, text="Durchsuchen…", width=110,
                      command=self._browse_dl).pack(side="left")

        # auto-sort controls
        body = self._card(self.t1, "🤖 Automatisch sortieren")
        inner = ctk.CTkFrame(body, fg_color="transparent")
        inner.pack(fill="x")
        self.v_iv = tk.BooleanVar(value=bool(self.cfg.get("iv", True)))
        self.v_new = tk.BooleanVar(value=bool(self.cfg.get("new", True)))
        self.v_min = tk.StringVar(value=str(self.cfg.get("min", 30)))
        ctk.CTkSwitch(inner, text="Intervall aktivieren", variable=self.v_iv,
                      command=self._snapshot).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ctk.CTkEntry(inner, textvariable=self.v_min, width=70).grid(row=0, column=1, padx=4)
        ctk.CTkLabel(inner, text="Minuten").grid(row=0, column=2, sticky="w", padx=(4, 12))
        ctk.CTkSwitch(inner, text="Bei neuen Dateien sortieren", variable=self.v_new,
                      command=self._snapshot).grid(row=0, column=3, sticky="w")

        # actions
        bar = ctk.CTkFrame(self.t1, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkButton(bar, text="⚡ Jetzt sortieren", height=38,
                      corner_radius=10, command=self._now).pack(fill="x", padx=2)

        self.status = ctk.CTkLabel(self.t1, text="Bereit.", anchor="w",
                                   font=ctk.CTkFont(size=13), text_color=("gray30", "gray80"))
        self.status.pack(fill="x", padx=16, pady=(2, 4))

        # log
        self.text = ctk.CTkTextbox(self.t1, wrap="word", height=200,
                                   font=ctk.CTkFont(family="Consolas", size=12))
        self.text.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self._log("Downsort startklar. Die App läuft im Hintergrund.")

    def _build_settings_tab(self):
        # ---- per-category target folders ----
        body = self._card(self.tab_settings,
                          "📁 Ziel-Ordner pro Kategorie  (leer = Standard in Downloads)")
        self._path_vars = {}
        for key, label in FOLDER_NAMES.items():
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, width=110, anchor="w",
                         text_color=("gray20", "gray90")).pack(side="left", padx=(0, 6))
            var = tk.StringVar(value=str(self.cfg["paths"].get(key, "")))
            self._path_vars[key] = var
            ent = ctk.CTkEntry(row, textvariable=var, placeholder_text="Standard: Downloads\\" + label)
            ent.pack(side="left", fill="x", expand=True, padx=(0, 6))
            ctk.CTkButton(row, text="…", width=34,
                          command=lambda k=key: self._browse_path(k)).pack(side="left", padx=2)
            ctk.CTkButton(row, text="Standard", width=64,
                          command=lambda v=var: v.set("")).pack(side="left", padx=2)

        # ---- appearance ----
        body = self._card(self.tab_settings, "🎨 Aussehen")
        inner = ctk.CTkFrame(body, fg_color="transparent")
        inner.pack(fill="x")
        ctk.CTkLabel(inner, text="Modus", width=90, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.v_appearance = ctk.CTkOptionMenu(
            inner, width=120,
            values=list(APPEARANCE_LABELS.keys()),
            command=self._appearance_changed)
        self.v_appearance.set(self.cfg["appearance"])
        self.v_appearance.grid(row=0, column=1, sticky="e", padx=(0, 4))
        ctk.CTkButton(inner, text="Übernehmen", width=90,
                      command=lambda: ctk.set_appearance_mode(self.v_appearance.get())
                      ).grid(row=0, column=2, padx=4)

        inner2 = ctk.CTkFrame(body, fg_color="transparent")
        inner2.pack(fill="x", pady=(6, 2))
        ctk.CTkLabel(inner2, text="Akzentfarbe", width=90, anchor="w").pack(side="left", padx=(0, 6))
        self.v_accent = ctk.CTkOptionMenu(inner2, width=130,
                                          values=ACCENT_PRESETS,
                                          command=lambda _: self._pick_preset())
        if self.cfg.get("accent", "blue") in ACCENT_PRESETS:
            self.v_accent.set(self.cfg["accent"])
        else:
            self.v_accent.set("blue")
        self.v_accent.pack(side="left", padx=(0, 4))
        ctk.CTkButton(inner2, text="Eigene Farbe…", width=120,
                      command=self._pick_custom_color).pack(side="left", padx=4)

        # save
        ctk.CTkButton(self.tab_settings, text="Einstellungen speichern", height=36,
                      corner_radius=10, command=self._save_settings).pack(fill="x", padx=16, pady=(10, 8))

        self._settings_built = True

    def _on_tab_change(self, tab):
        if tab == "Einstellungen" and not self._settings_built:
            self._build_settings_tab()

    # ---- commands ----------------------------------------------------------
    def _browse_dl(self):
        from tkinter import filedialog
        start = self.e_dl.get().strip() or os.path.expanduser("~")
        chosen = filedialog.askdirectory(parent=self.root, initialdir=start,
                                         title="Download-Ordner wählen")
        if chosen:
            self.e_dl.delete(0, "end")
            self.e_dl.insert(0, chosen.replace("\\", "/"))
            self._snapshot()

    def _browse_path(self, key):
        from tkinter import filedialog
        start = self._path_vars[key].get().strip() or os.path.expanduser("~")
        chosen = filedialog.askdirectory(parent=self.root, initialdir=start,
                                         title="Ziel-Ordner wählen")
        if chosen:
            self._path_vars[key].set(chosen.replace("\\", "/"))

    def _snapshot(self):
        """Plain-data snapshot read by the worker thread (Tk vars are not
        thread-safe to read outside the GUI thread)."""
        try:
            val = int(self.v_min.get() or 30)
        except ValueError:
            val = 30
        self._worker_state.update(
            dl=self.e_dl.get().strip().replace("\\", "/"),
            min=max(1, val),
            iv=bool(self.v_iv.get()),
            new=bool(self.v_new.get()),
        )

    def _appearance_changed(self, val):
        pass  # applied via the Übernehmen button

    def _pick_preset(self):
        self.cfg["accent"] = self.v_accent.get()

    def _pick_custom_color(self):
        from tkinter import colorchooser
        _, hexcol = colorchooser.askcolor(color="#3B8ED0", title="Akzentfarbe wählen")
        if hexcol:
            self.cfg["accent"] = hexcol
            self.v_accent.set("blue")  # menu only shows presets; custom is kept in cfg
            self._set_status("Eigene Farbe gewählt – mit „Einstellungen speichern\" übernehmen.", ok=True)

    def _save_settings(self):
        try:
            val = int(self.v_min.get() or 30)
        except ValueError:
            val = 30
        self.cfg["dl"] = self.e_dl.get().strip().replace("\\", "/") or self.cfg["dl"]
        self.cfg["min"] = max(1, val)
        self.cfg["iv"] = bool(self.v_iv.get())
        self.cfg["new"] = bool(self.v_new.get())
        # only update accent/appearance if the settings tab was touched
        if self._settings_built:
            self.cfg["appearance"] = self.v_appearance.get()
            self.cfg["accent"] = self.v_accent.get()
        paths = {}
        if self._settings_built:
            for k, v in self._path_vars.items():
                paths[k] = v.get().strip().replace("\\", "/")
        self.cfg["paths"] = paths
        save_config(self.cfg)
        ctk.set_appearance_mode(self.cfg["appearance"])
        self._snapshot()
        self._set_status("✓ Einstellungen gespeichert.", ok=True)

    def _now(self):
        self.jobs.put("now")

    def _set_status(self, msg, ok=True):
        self.status.configure(text=msg,
                              text_color="green" if ok else ("red", "#ff6666"))

    def _log(self, msg):
        self.text.insert("end", msg + "\n")
        try:
            self.text.see("end")
        except Exception:
            pass

    # ---- sorting -----------------------------------------------------------
    def _pump(self):
        try:
            while True:
                job = self.jobs.get_nowait()
                if job == "now":
                    self._do_sort()
        except queue.Empty:
            pass
        self.root.after(150, self._pump)

    def _do_sort(self):
        self._snapshot()
        try:
            dl, target = self._sort_targets()
            if not dl or not os.path.isdir(dl):
                raise FileNotFoundError("Ordner nicht gefunden: %s" % dl)
            count = 0
            for item in sorter.sort_downloads(dl, target):
                self._log("  %s  %s  %s" % (item["category"], item["name"], item["size"]))
                count += 1
            self._set_status("Zuletzt sortiert: %d Datei(en)" % count, ok=True)
            if count > 0:
                self._log("%s: %d Datei(en) einsortiert." % (time.strftime("%H:%M:%S"), count))
        except Exception as exc:
            self._set_status("Fehler: %s" % exc, ok=False)
            self._log(str(exc))
        # refresh baseline file list after any change
        dl = self.e_dl.get().strip().replace("\\", "/")
        self._last = os.listdir(dl) if (dl and os.path.isdir(dl)) else []

    def _background(self):
        while True:
            st = self._worker_state
            dl = st["dl"]
            if dl and os.path.isdir(dl):
                try:
                    now = os.listdir(dl)
                except OSError:
                    now = self._last
                if st["new"] and now and set(now) - set(self._last):
                    self.jobs.put("now")
                self._last = now
            interval = int(st["min"]) * 60
            if st["iv"] and dl and time.time() - self._last_poll >= interval:
                self._last_poll = time.time()
                self.jobs.put("now")
            time.sleep(2)


# convenience mirror for backwards-compatible button binding
App.now = App._now
App.run_sort = App._do_sort


def main():
    cfg = load_config()
    apply_ctk_theme(cfg)
    App(cfg).root.mainloop()


if __name__ == "__main__":
    main()