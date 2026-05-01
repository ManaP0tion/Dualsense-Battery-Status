"""
Battery info popup — appears above the tray icon on left-click.
Runs on the Tkinter main thread via root.after() queue.
"""

from __future__ import annotations

import ctypes
import tkinter as tk
from typing import TYPE_CHECKING, Callable

import i18n

if TYPE_CHECKING:
    from controller import BatteryState

BG       = "#0d1117"
BG_INNER = "#161b22"
BORDER   = "#30363d"
FG       = "#e6edf3"
FG_DIM   = "#8b949e"
C_GREEN  = "#3fb950"
C_YELLOW = "#d29922"
C_RED    = "#f85149"
C_BLUE   = "#58a6ff"

POPUP_W  = 230


def _accent(percent: int, is_charging: bool) -> str:
    if is_charging:  return C_BLUE
    if percent > 50: return C_GREEN
    if percent > 20: return C_YELLOW
    return C_RED


def _cursor_pos() -> tuple[int, int]:
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


class BatteryPopup:
    def __init__(self, root: tk.Tk, on_settings: Callable[[], None] | None = None) -> None:
        self._root = root
        self._win: tk.Toplevel | None = None
        self._on_settings = on_settings

    def show(self, state: "BatteryState") -> None:
        self._close()
        x, y = _cursor_pos()

        win = tk.Toplevel(self._root)
        self._win = win
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.96)
        win.configure(bg=BORDER)

        self._build(win, state)

        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        px = max(4, min(x - w // 2, sw - w - 4))
        py = y - h - 14
        if py < 4:
            py = y + 14

        win.geometry(f"{w}x{h}+{px}+{py}")
        win.focus_force()
        win.bind("<FocusOut>", lambda e: self._root.after(80, self._close_if_unfocused))
        win.bind("<Escape>",   lambda e: self._close())

    def _build(self, win: tk.Toplevel, state: "BatteryState") -> None:
        pad   = tk.Frame(win, bg=BORDER, padx=1, pady=1)
        pad.pack(fill="both", expand=True)
        inner = tk.Frame(pad, bg=BG, padx=16, pady=14)
        inner.pack(fill="both", expand=True)

        # Header
        hdr = tk.Frame(inner, bg=BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="DualSense", bg=BG, fg=FG,
                 font=i18n.tk_font(11, bold=True)).pack(side="left")
        tk.Label(hdr, text=i18n.t("battery_status"), bg=BG, fg=FG_DIM,
                 font=i18n.tk_font(9)).pack(side="left", padx=(5, 0), pady=(2, 0))

        btn_close = tk.Label(hdr, text="✕", bg=BG, fg=FG_DIM, font=i18n.tk_font(10), cursor="hand2")
        btn_close.pack(side="right", padx=(4, 0))
        btn_close.bind("<Button-1>", lambda e: self._close())
        btn_close.bind("<Enter>", lambda e: btn_close.config(fg=FG))
        btn_close.bind("<Leave>", lambda e: btn_close.config(fg=FG_DIM))

        btn_settings = tk.Label(hdr, text="⚙", bg=BG, fg=FG_DIM, font=i18n.tk_font(11), cursor="hand2")
        btn_settings.pack(side="right")
        btn_settings.bind("<Button-1>", lambda e: self._open_settings())
        btn_settings.bind("<Enter>", lambda e: btn_settings.config(fg=FG))
        btn_settings.bind("<Leave>", lambda e: btn_settings.config(fg=FG_DIM))

        # Connection badge
        if state.connected:
            badge_text  = f"  {state.connection}  "
            badge_color = C_BLUE if state.connection == "Bluetooth" else C_GREEN
        else:
            badge_text  = f"  {i18n.t('not_connected')}  "
            badge_color = FG_DIM

        tk.Label(inner, text=badge_text, bg=BG_INNER, fg=badge_color,
                 font=i18n.tk_font(8, bold=True),
                 relief="flat", padx=4, pady=2).pack(anchor="w", pady=(6, 10))

        if not state.connected:
            tk.Label(inner, text=i18n.t("please_connect"),
                     bg=BG, fg=FG_DIM, font=i18n.tk_font(9)).pack()
            return

        # Battery bar
        accent = _accent(state.percent, state.is_charging)
        bar_w, bar_h, nub_w = POPUP_W - 36, 16, 5

        cv = tk.Canvas(inner, width=bar_w + nub_w, height=bar_h,
                       bg=BG, highlightthickness=0)
        cv.pack()
        cv.create_rectangle(0, 0, bar_w, bar_h,
                            outline=BORDER, fill=BG_INNER, width=1)
        ny = bar_h // 2
        cv.create_rectangle(bar_w + 1, ny - 4, bar_w + nub_w, ny + 4,
                            fill=BORDER, outline="")
        fw = max(0, int((bar_w - 4) * state.percent / 100))
        if fw:
            cv.create_rectangle(2, 2, 2 + fw, bar_h - 2, fill=accent, outline="")

        # Large percentage
        tk.Label(inner, text=f"{state.percent}%", bg=BG, fg=accent,
                 font=i18n.tk_font(32, bold=True)).pack(pady=(8, 0))

        # Status line
        if state.is_charging:
            status, color = i18n.t("charging"),    C_BLUE
        elif state.percent == 100:
            status, color = i18n.t("fully_charged"), C_GREEN
        else:
            status, color = i18n.t("discharging"),   FG_DIM

        tk.Label(inner, text=status, bg=BG, fg=color,
                 font=i18n.tk_font(9)).pack(pady=(2, 0))

    def _open_settings(self) -> None:
        if self._on_settings:
            self._on_settings()
        self._close()

    def _close(self) -> None:
        if self._win is not None:
            try:
                self._win.destroy()
            except tk.TclError:
                pass
            self._win = None

    def _close_if_unfocused(self) -> None:
        if self._win is None:
            return
        try:
            focused = self._root.focus_get()
            if focused is None or not str(focused).startswith(str(self._win)):
                self._close()
        except tk.TclError:
            self._close()
