"""
DualSense Battery Status — system tray app
Run:    python src/main.py
Build:  pyinstaller --onefile --noconsole --icon=assets/app_icon.ico src/main.py
"""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"


def _setup_logging() -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8")],
    )


def _ensure_assets() -> None:
    if not (BASE_DIR / "assets" / "app_icon.ico").exists():
        try:
            import generate_app_icon
            generate_app_icon.main()
        except Exception as exc:
            logging.warning("Could not generate app icon: %s", exc)


def main() -> None:
    _setup_logging()
    log = logging.getLogger("main")
    log.info("Starting DualSense Battery Status")

    _ensure_assets()

    from controller import BatteryState, ControllerMonitor
    from popup import BatteryPopup, AlertPopup
    from settings import Settings, SettingsWindow
    from tray_icon import TrayApp
    import i18n

    # ── Tkinter root (hidden) ──────────────────────────────────────────────────
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-alpha", 0)

    # Load settings, then initialise i18n (needs Tk root for font detection)
    cfg = Settings.load()
    i18n.init(root, cfg.language)
    log.info("Language: %s  font: %s", cfg.language, i18n.tk_font(9))

    popup_q:    queue.Queue[BatteryState] = queue.Queue()
    settings_q: queue.Queue[None]         = queue.Queue()
    alert_q:    queue.Queue[BatteryState] = queue.Queue()
    
    popup        = BatteryPopup(root, on_settings=lambda: settings_q.put(None))
    alert_popup  = AlertPopup(root)
    
    alert_state  = {"has_alerted": False}

    tray: TrayApp | None = None

    def on_battery_update(state: BatteryState) -> None:
        if tray is not None:
            tray.update(state)
            
        if cfg.low_battery_warn and state.connected and not state.is_charging:
            if state.percent <= cfg.low_battery_threshold:
                if not alert_state["has_alerted"]:
                    alert_state["has_alerted"] = True
                    alert_q.put(state)
            else:
                alert_state["has_alerted"] = False
        else:
            alert_state["has_alerted"] = False

    def on_quit() -> None:
        log.info("Quit requested")
        monitor.stop()
        root.after(0, root.quit)

    monitor = ControllerMonitor(
        on_update=on_battery_update,
        poll_interval=cfg.poll_interval,
    )

    settings_win = SettingsWindow(
        root=root,
        settings=cfg,
        on_apply=lambda new: (
            monitor.set_poll_interval(new.poll_interval),
            tray.update(monitor.current_state) if tray else None,
        ),
    )

    tray = TrayApp(
        on_quit=on_quit,
        on_click=lambda _state: popup_q.put(_state),
        on_settings=lambda: settings_q.put(None),
    )

    def _drain() -> None:
        try:
            while True:
                popup_q.get_nowait()
                popup.show(monitor.current_state)
        except queue.Empty:
            pass
        try:
            while True:
                settings_q.get_nowait()
                settings_win.show()
        except queue.Empty:
            pass
        try:
            while True:
                astate = alert_q.get_nowait()
                alert_popup.show(astate)
        except queue.Empty:
            pass
        root.after(100, _drain)

    monitor.start()
    threading.Thread(target=tray.run, daemon=True).start()
    root.after(100, _drain)
    root.mainloop()
    log.info("Exited cleanly")


if __name__ == "__main__":
    main()
