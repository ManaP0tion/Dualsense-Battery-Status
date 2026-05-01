"""
Internationalisation: language strings and font resolution.

Supported languages
  "en"  English  — Hack Nerd Font  (fallback: Consolas)
  "ko"  한국어   — Noto Sans KR   (fallback: Malgun Gothic)

Call init(root, lang) once after tk.Tk() is created.
Then use t("key") for strings and tk_font(size, bold) / pil_font(size) for fonts.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk
    from PIL import ImageFont as _IF

# ── String tables ──────────────────────────────────────────────────────────────

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # Tray / tooltip
        "tooltip_disconnected": "DualSense: Not connected",
        "tooltip_connected":    "DualSense [{conn}]: {pct}%{charge}",
        "tooltip_charging":     " (Charging)",
        # Tray menu
        "no_controller":        "No controller connected",
        "menu_show_details":    "Show Details",
        "menu_settings":        "⚙  Settings",
        "menu_quit":            "Quit",
        # Popup
        "battery_status":       "Battery Status",
        "not_connected":        "Not Connected",
        "please_connect":       "Please connect a controller.",
        "charging":             "⚡  Charging",
        "fully_charged":        "✔  Fully Charged",
        "discharging":          "Discharging",
        # Settings window
        "settings_title":       "DualSense Battery — Settings",
        "settings_heading":     "Settings",
        "section_startup":      "Startup",
        "run_on_startup":       "Run on Windows startup",
        "section_interval":     "Battery Update Interval",
        "interval_5s":          "5s  (fast)",
        "interval_15s":         "15s",
        "interval_30s":         "30s",
        "interval_60s":         "60s  (slow)",
        "section_low_battery":  "Low Battery Alert",
        "low_battery_warn":     "Show low battery alert",
        "alert_threshold":      "Alert threshold:",
        "section_language":     "Language",
        "btn_save":             "Save",
        "btn_cancel":           "Cancel",
    },
    "ko": {
        # Tray / tooltip
        "tooltip_disconnected": "DualSense: 연결 없음",
        "tooltip_connected":    "DualSense [{conn}]: {pct}%{charge}",
        "tooltip_charging":     " (충전 중)",
        # Tray menu
        "no_controller":        "연결된 컨트롤러 없음",
        "menu_show_details":    "상세 정보 보기",
        "menu_settings":        "⚙  설정",
        "menu_quit":            "종료",
        # Popup
        "battery_status":       "배터리 상태",
        "not_connected":        "연결 없음",
        "please_connect":       "컨트롤러를 연결해 주세요.",
        "charging":             "⚡  충전 중",
        "fully_charged":        "✔  완충됨",
        "discharging":          "방전 중",
        # Settings window
        "settings_title":       "DualSense Battery — 설정",
        "settings_heading":     "설정",
        "section_startup":      "시작",
        "run_on_startup":       "Windows 시작 시 자동 실행",
        "section_interval":     "배터리 업데이트 주기",
        "interval_5s":          "5초  (빠름)",
        "interval_15s":         "15초",
        "interval_30s":         "30초",
        "interval_60s":         "60초  (느림)",
        "section_low_battery":  "저배터리 알림",
        "low_battery_warn":     "저배터리 알림 표시",
        "alert_threshold":      "알림 기준:",
        "section_language":     "언어",
        "btn_save":             "저장",
        "btn_cancel":           "취소",
    },
}

# ── Font configuration ─────────────────────────────────────────────────────────

_WIN_FONTS = Path("C:/Windows/Fonts")

_FONT_CFG: dict[str, dict] = {
    "en": {
        # Tkinter family names to try in order
        "tk": ["Hack Nerd Font", "Hack NF", "Hack", "Arial"],
        # TTF filenames to try for Pillow (searched in C:\Windows\Fonts)
        "pil": ["HackNerdFont-Regular.ttf", "Hack-Regular.ttf",
                "HackNF-Regular.ttf", "arial.ttf"],
    },
    "ko": {
        "tk":  ["Noto Sans KR", "Noto Sans KR Regular",
                "Malgun Gothic", "Gulim", "Dotum"],
        "pil": ["NotoSansKR-Regular.ttf",
                "NotoSansKR-VariableFont_wght.ttf",
                "malgun.ttf", "gulim.ttc", "arial.ttf"],
    },
}

# ── Module state ───────────────────────────────────────────────────────────────

_lang:       str            = "en"
_tk_family:  str | None     = None   # resolved once after Tk init
_tk_families: frozenset[str] = frozenset()


# ── Public API ─────────────────────────────────────────────────────────────────

def init(root: "tk.Tk", lang: str) -> None:
    """
    Must be called once after tk.Tk() is created.
    Resolves available font families and sets the active language.
    """
    global _lang, _tk_families, _tk_family
    import tkinter.font as tkfont
    _tk_families = frozenset(tkfont.families(root))
    set_lang(lang)


def set_lang(lang: str) -> None:
    global _lang, _tk_family
    _lang      = lang if lang in _STRINGS else "en"
    _tk_family = None   # force re-resolution on next tk_font() call


def get_lang() -> str:
    return _lang


def t(key: str, **kw: object) -> str:
    s = _STRINGS.get(_lang, _STRINGS["en"]).get(key, key)
    return s.format(**kw) if kw else s


def tk_font(size: int, bold: bool = False) -> tuple[str, int, str] | tuple[str, int]:
    """Return a tkinter-compatible font tuple."""
    family = _resolve_tk_family()
    return (family, size, "bold") if bold else (family, size)


def pil_font(size: int) -> "_IF.FreeTypeFont | _IF.ImageFont":
    """Return a Pillow font for icon rendering."""
    from PIL import ImageFont
    cfg = _FONT_CFG.get(_lang, _FONT_CFG["en"])
    for fname in cfg["pil"]:
        for path in (_WIN_FONTS / fname, Path(fname)):
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                pass
    return ImageFont.load_default()


# ── Internal helpers ───────────────────────────────────────────────────────────

def _resolve_tk_family() -> str:
    global _tk_family
    if _tk_family is not None:
        return _tk_family
    cfg = _FONT_CFG.get(_lang, _FONT_CFG["en"])
    for name in cfg["tk"]:
        if name in _tk_families:
            _tk_family = name
            return _tk_family
    _tk_family = "TkDefaultFont"
    return _tk_family
