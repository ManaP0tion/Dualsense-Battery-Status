"""
DualSense HID communication and battery parsing.

Standard HID input report:
  USB  Report 0x01  battery byte @ data[53]
  BT   Report 0x31  battery byte @ data[54]

Battery byte layout:
  bits [3:0]  -> level 0–10  (× 10 = %)
  bits [7:4]  -> charging flags
                   0x0 = discharging
                   0x1 = charging
                   0x2 = fully charged
                   0xB = USB cable, not charging
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable

import hid

log = logging.getLogger(__name__)

DUALSENSE_VID = 0x054C
DUALSENSE_PID = 0x0CE6

_USB_MIN_LEN = 54
_BT_MIN_LEN  = 55

DEFAULT_POLL_INTERVAL = 5


@dataclass
class BatteryState:
    connected:   bool = False
    percent:     int  = 0
    is_charging: bool = False
    connection:  str  = ""    # "USB" | "Bluetooth" | ""

    def tooltip(self) -> str:
        from i18n import t
        if not self.connected:
            return t("tooltip_disconnected")
        charge = t("tooltip_charging") if self.is_charging else ""
        return t("tooltip_connected",
                 conn=self.connection, pct=self.percent, charge=charge)


def _parse_battery(raw: int) -> tuple[int, bool]:
    level    = raw & 0x0F
    flags    = (raw & 0xF0) >> 4
    percent  = 100 if flags == 0x2 else min(level * 10, 100)
    charging = flags in (0x1, 0x2)
    return percent, charging


def _read_state(dev: hid.device, is_bt: bool) -> tuple[int, bool] | None:
    try:
        data = bytes(dev.read(100, timeout_ms=1000))
    except OSError:
        return None
    if not data:
        return None

    min_len = _BT_MIN_LEN if is_bt else _USB_MIN_LEN
    if len(data) < min_len:
        return None

    return _parse_battery(data[54] if is_bt else data[53])


def find_dualsense() -> tuple[hid.device, bool] | tuple[None, None]:
    """Return (opened hid.device, is_bluetooth) or (None, None)."""
    for info in hid.enumerate(DUALSENSE_VID, DUALSENSE_PID):
        dev = hid.device()
        try:
            dev.open_path(info["path"])
            dev.set_nonblocking(False)
            data = dev.read(100, timeout_ms=500)
            if not data:
                dev.close()
                continue
            return dev, (data[0] == 0x31)
        except OSError:
            try:
                dev.close()
            except Exception:
                pass
    return None, None


class ControllerMonitor:
    def __init__(
        self,
        on_update:     Callable[[BatteryState], None],
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ) -> None:
        self._on_update     = on_update
        self._poll_interval = poll_interval
        self._state         = BatteryState()
        self._lock          = threading.Lock()
        self._stop_event    = threading.Event()
        self._thread        = threading.Thread(target=self._loop, daemon=True)

    @property
    def current_state(self) -> BatteryState:
        with self._lock:
            return self._state

    def set_poll_interval(self, seconds: int) -> None:
        self._poll_interval = seconds

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self._poll_once()
            self._stop_event.wait(self._poll_interval)

    def _poll_once(self) -> None:
        dev, is_bt = find_dualsense()

        if dev is None:
            if self._state.connected:
                self._emit(BatteryState(connected=False))
            return

        result = _read_state(dev, is_bt)
        try:
            dev.close()
        except Exception:
            pass

        if result is None:
            if self._state.connected:
                self._emit(BatteryState(connected=False))
            return

        percent, is_charging = result
        new = BatteryState(
            connected=True,
            percent=percent,
            is_charging=is_charging,
            connection="Bluetooth" if is_bt else "USB",
        )
        prev = self._state
        if (new.connected != prev.connected or new.percent != prev.percent
                or new.is_charging != prev.is_charging
                or new.connection  != prev.connection):
            self._emit(new)

    def _emit(self, state: BatteryState) -> None:
        with self._lock:
            self._state = state
        log.info("Battery: %d%% [%s] charging=%s",
                 state.percent, state.connection, state.is_charging)
        self._on_update(state)
