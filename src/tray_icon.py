from __future__ import annotations

import threading
from typing import Callable

import pystray

import i18n
from controller import BatteryState
from icon_render import render_disconnected, render_icon


class TrayApp:
    def __init__(
        self,
        on_quit:     Callable[[], None],
        on_click:    Callable[[BatteryState], None] | None = None,
        on_settings: Callable[[], None] | None = None,
    ) -> None:
        self._on_quit     = on_quit
        self._on_click    = on_click
        self._on_settings = on_settings
        self._state       = BatteryState()
        self._lock        = threading.Lock()

        self._icon = pystray.Icon(
            name="dualsense_battery",
            icon=render_disconnected(),
            title=i18n.t("tooltip_disconnected"),
            menu=self._build_menu(),
        )

    def run(self) -> None:
        self._icon.run()

    def stop(self) -> None:
        self._icon.stop()

    def update(self, state: BatteryState) -> None:
        with self._lock:
            self._state = state
        img = render_icon(state.percent, state.is_charging) \
            if state.connected else render_disconnected()
        self._icon.icon  = img
        self._icon.title = state.tooltip()
        self._icon.menu  = self._build_menu()

    def _build_menu(self) -> pystray.Menu:
        with self._lock:
            state = self._state

        if state.connected:
            charge = f" ({i18n.t('charging').strip()})" if state.is_charging else ""
            info   = f"{state.percent}%{charge}  [{state.connection}]"
        else:
            info = i18n.t("no_controller")

        items: list[pystray.MenuItem] = []
        if self._on_click is not None:
            items.append(pystray.MenuItem(
                i18n.t("menu_show_details"),
                self._handle_click,
                default=True,
                visible=False,
            ))

        items += [
            pystray.MenuItem(info, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(i18n.t("menu_settings"), self._handle_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(i18n.t("menu_quit"), self._quit),
        ]
        return pystray.Menu(*items)

    def _handle_click(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        if self._on_click is not None:
            with self._lock:
                state = self._state
            self._on_click(state)

    def _handle_settings(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        if self._on_settings is not None:
            self._on_settings()

    def _quit(self, icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._on_quit()
        icon.stop()
