"""
Settings: persistence (JSON), Windows startup (Registry), and UI window.
"""

from __future__ import annotations

import json
import logging
import sys
import winreg
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import tkinter as tk

import i18n

log = logging.getLogger(__name__)

BASE_DIR    = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
APP_NAME    = "DualSenseBattery"
REG_RUN     = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"

BG      = "#0d1117"
BG2     = "#161b22"
BORDER  = "#30363d"
FG      = "#e6edf3"
FG_DIM  = "#8b949e"
ACCENT  = "#58a6ff"


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class Settings:
    startup:               bool = False
    poll_interval:         int  = 5
    low_battery_warn:      bool = True
    low_battery_threshold: int  = 20
    language:              str  = "en"

    def save(self) -> None:
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        log.info("Settings saved: %s", asdict(self))

    @classmethod
    def load(cls) -> "Settings":
        if CONFIG_PATH.exists():
            try:
                raw  = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                keys = cls.__dataclass_fields__.keys()
                return cls(**{k: v for k, v in raw.items() if k in keys})
            except Exception as exc:
                log.warning("Could not load settings (%s), using defaults", exc)
        return cls()


# ── Windows startup ────────────────────────────────────────────────────────────

def _exe_path() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{BASE_DIR / "src" / "main.py"}"'


def apply_startup(enabled: bool) -> None:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN, 0,
                             winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _exe_path())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        log.info("Startup registry %s", "enabled" if enabled else "disabled")
    except OSError as exc:
        log.error("Registry write failed: %s", exc)


def is_startup_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN, 0,
                             winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False


# ── Settings window ────────────────────────────────────────────────────────────

class SettingsWindow:
    def __init__(
        self,
        root:     tk.Tk,
        settings: Settings,
        on_apply: Callable[[Settings], None] | None = None,
    ) -> None:
        self._root     = root
        self._settings = settings
        self._on_apply = on_apply
        self._win: tk.Toplevel | None = None

    def show(self) -> None:
        if self._win and self._win.winfo_exists():
            self._win.lift()
            return

        win = tk.Toplevel(self._root)
        self._win = win
        win.title(i18n.t("settings_title"))
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.configure(bg=BG)
        self._build(win)

        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        w, h   = win.winfo_reqwidth(),    win.winfo_reqheight()
        win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build(self, win: tk.Toplevel) -> None:
        s   = self._settings
        out = tk.Frame(win, bg=BG, padx=20, pady=18)
        out.pack(fill="both", expand=True)

        tk.Label(out, text=i18n.t("settings_heading"), bg=BG, fg=FG,
                 font=i18n.tk_font(13, bold=True)).pack(anchor="w")
        _divider(out)

        # ── Language ──────────────────────────────────────────────────────────
        _section(out, i18n.t("section_language"))
        var_lang = tk.StringVar(value=s.language)
        lang_row = tk.Frame(out, bg=BG)
        lang_row.pack(anchor="w", pady=(2, 0))
        for code, label in [("en", "English"), ("ko", "한국어")]:
            tk.Radiobutton(
                lang_row, text=label, variable=var_lang, value=code,
                bg=BG, fg=FG, selectcolor=BG2,
                activebackground=BG, activeforeground=FG,
                font=i18n.tk_font(9),
            ).pack(side="left", padx=(0, 14))
        _divider(out)

        # ── Startup ───────────────────────────────────────────────────────────
        _section(out, i18n.t("section_startup"))
        var_startup = tk.BooleanVar(value=is_startup_enabled())
        _checkbox(out, i18n.t("run_on_startup"), var_startup)
        _divider(out)

        # ── Poll interval ─────────────────────────────────────────────────────
        _section(out, i18n.t("section_interval"))
        var_interval = tk.IntVar(value=s.poll_interval)
        radio_row    = tk.Frame(out, bg=BG)
        radio_row.pack(anchor="w", pady=(2, 0))
        for val, key in [(5, "interval_5s"), (15, "interval_15s"),
                         (30, "interval_30s"), (60, "interval_60s")]:
            tk.Radiobutton(
                radio_row, text=i18n.t(key), variable=var_interval, value=val,
                bg=BG, fg=FG, selectcolor=BG2,
                activebackground=BG, activeforeground=FG,
                font=i18n.tk_font(9),
            ).pack(side="left", padx=(0, 10))
        _divider(out)

        # ── Low battery ───────────────────────────────────────────────────────
        _section(out, i18n.t("section_low_battery"))
        var_warn = tk.BooleanVar(value=s.low_battery_warn)
        _checkbox(out, i18n.t("low_battery_warn"), var_warn)

        thr_row = tk.Frame(out, bg=BG)
        thr_row.pack(anchor="w", pady=(6, 0))
        tk.Label(thr_row, text=i18n.t("alert_threshold"),
                 bg=BG, fg=FG_DIM, font=i18n.tk_font(9)).pack(side="left")
        var_threshold = tk.IntVar(value=s.low_battery_threshold)
        tk.Spinbox(
            thr_row, from_=5, to=50, increment=5,
            textvariable=var_threshold, width=4,
            bg=BG2, fg=FG, insertbackground=FG,
            buttonbackground=BORDER, relief="flat",
            font=i18n.tk_font(9),
        ).pack(side="left", padx=6)
        tk.Label(thr_row, text="%", bg=BG, fg=FG_DIM,
                 font=i18n.tk_font(9)).pack(side="left")
        _divider(out)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = tk.Frame(out, bg=BG)
        btn_row.pack(fill="x", pady=(4, 0))

        def _save() -> None:
            new_lang = var_lang.get()
            new = Settings(
                startup               = var_startup.get(),
                poll_interval         = var_interval.get(),
                low_battery_warn      = var_warn.get(),
                low_battery_threshold = var_threshold.get(),
                language              = new_lang,
            )
            apply_startup(new.startup)
            i18n.set_lang(new_lang)
            new.save()
            self._settings.__dict__.update(asdict(new))
            if self._on_apply:
                self._on_apply(new)
            win.destroy()

        tk.Button(
            btn_row, text=i18n.t("btn_save"), command=_save,
            bg=ACCENT, fg="#000000", activebackground="#79beff",
            relief="flat", font=i18n.tk_font(9, bold=True),
            padx=18, pady=4, cursor="hand2",
        ).pack(side="right", padx=(6, 0))
        tk.Button(
            btn_row, text=i18n.t("btn_cancel"), command=win.destroy,
            bg=BG2, fg=FG, activebackground=BORDER,
            relief="flat", font=i18n.tk_font(9),
            padx=18, pady=4, cursor="hand2",
        ).pack(side="right")


# ── Widget helpers ─────────────────────────────────────────────────────────────

def _divider(parent: tk.Frame) -> None:
    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=10)


def _section(parent: tk.Frame, text: str) -> None:
    tk.Label(parent, text=text, bg=BG, fg=FG_DIM,
             font=i18n.tk_font(8, bold=True)).pack(anchor="w", pady=(0, 6))


def _checkbox(parent: tk.Frame, text: str, var: tk.BooleanVar) -> None:
    tk.Checkbutton(
        parent, text=text, variable=var,
        bg=BG, fg=FG, selectcolor=BG2,
        activebackground=BG, activeforeground=FG,
        font=i18n.tk_font(9),
    ).pack(anchor="w")
