"""
HID communication and battery parsing for Sony PlayStation controllers.

DualSense:
  USB  Report 0x01  battery byte @ data[53]  bits[3:0]=level 0-10 (×10=%)
  BT   Report 0x31  battery byte @ data[54]  bits[7:4]=charging flags
                      0x0=discharging  0x1=charging  0x2=full  0xB=USB/not charging

DualShock 4:
  USB  Report 0x01  battery byte @ data[31]  bits[3:0]=level 0-11 (×10=%, capped 100%)
  BT   Report 0x11  battery byte @ data[33]  bit[4]=USB plugged
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable

import hid

log = logging.getLogger(__name__)

SONY_VID        = 0x054C
DUALSENSE_PID   = 0x0CE6
DUALSHOCK4_PIDS = (0x05C4, 0x09CC)   # v1, v2

CTRL_DUALSENSE  = "DualSense"
CTRL_DUALSHOCK4 = "DualShock 4"

# Minimum HID read lengths (report ID byte included)
_DS_USB_MIN_LEN  = 54
_DS_BT_MIN_LEN   = 55
_DS4_USB_MIN_LEN = 32
_DS4_BT_MIN_LEN  = 34

# Battery byte offsets in the HIDAPI read buffer (report ID at index 0)
_DS4_USB_BATT_OFFSET = 31
_DS4_BT_BATT_OFFSET  = 33

DEFAULT_POLL_INTERVAL = 60


@dataclass
class BatteryState:
    connected:   bool = False
    percent:     int  = 0
    is_charging: bool = False
    connection:  str  = ""    # "USB" | "Bluetooth" | ""
    controller:  str  = ""    # "DualSense" | "DualShock 4" | ""

    def tooltip(self) -> str:
        from i18n import t
        if not self.connected:
            return t("tooltip_disconnected", ctrl=self.controller or "Controller")
        charge = t("tooltip_charging") if self.is_charging else ""
        return t("tooltip_connected",
                 ctrl=self.controller, conn=self.connection,
                 pct=self.percent, charge=charge)


def _parse_battery_ds(raw: int) -> tuple[int, bool]:
    level    = raw & 0x0F
    flags    = (raw & 0xF0) >> 4
    percent  = 100 if flags == 0x2 else min(level * 10, 100)
    charging = flags in (0x1, 0x2)
    return percent, charging


def _parse_battery_ds4(raw: int) -> tuple[int, bool]:
    level       = raw & 0x0F
    usb_plugged = bool(raw & 0x10)
    percent     = min(level * 10, 100)
    return percent, usb_plugged


def _read_state(dev: hid.device, is_bt: bool, ctrl: str) -> tuple[int, bool] | None:
    try:
        data = bytes(dev.read(100, timeout_ms=1000))
    except OSError:
        return None
    if not data:
        return None

    if ctrl == CTRL_DUALSHOCK4:
        offset  = _DS4_BT_BATT_OFFSET  if is_bt else _DS4_USB_BATT_OFFSET
        min_len = _DS4_BT_MIN_LEN      if is_bt else _DS4_USB_MIN_LEN
        if len(data) < min_len:
            return None
        return _parse_battery_ds4(data[offset])
    else:
        min_len = _DS_BT_MIN_LEN if is_bt else _DS_USB_MIN_LEN
        if len(data) < min_len:
            return None
        return _parse_battery_ds(data[54] if is_bt else data[53])


def find_controller() -> tuple[hid.device, bool, str] | tuple[None, None, None]:
    """Return (opened hid.device, is_bluetooth, controller_type) or (None, None, None)."""
    candidates: list[tuple[dict, str]] = []
    for info in hid.enumerate(SONY_VID, DUALSENSE_PID):
        candidates.append((info, CTRL_DUALSENSE))
    for pid in DUALSHOCK4_PIDS:
        for info in hid.enumerate(SONY_VID, pid):
            candidates.append((info, CTRL_DUALSHOCK4))

    for info, ctrl in candidates:
        dev = hid.device()
        try:
            dev.open_path(info["path"])
            dev.set_nonblocking(False)
            data = dev.read(100, timeout_ms=500)
            if not data:
                dev.close()
                continue
            if ctrl == CTRL_DUALSENSE:
                is_bt = (data[0] == 0x31)
            else:
                is_bt = (data[0] == 0x11)
            return dev, is_bt, ctrl
        except OSError:
            try:
                dev.close()
            except Exception:
                pass
    return None, None, None


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
        dev, is_bt, ctrl = find_controller()

        if dev is None:
            if self._state.connected:
                self._emit(BatteryState(connected=False,
                                        controller=self._state.controller))
            return

        result = _read_state(dev, is_bt, ctrl)
        try:
            dev.close()
        except Exception:
            pass

        if result is None:
            if self._state.connected:
                self._emit(BatteryState(connected=False, controller=ctrl))
            return

        percent, is_charging = result
        new = BatteryState(
            connected=True,
            percent=percent,
            is_charging=is_charging,
            connection="Bluetooth" if is_bt else "USB",
            controller=ctrl,
        )
        prev = self._state
        if (new.connected != prev.connected or new.percent != prev.percent
                or new.is_charging != prev.is_charging
                or new.connection  != prev.connection
                or new.controller  != prev.controller):
            self._emit(new)

    def _emit(self, state: BatteryState) -> None:
        with self._lock:
            self._state = state
        log.info("Battery: %d%% [%s] [%s] charging=%s",
                 state.percent, state.connection, state.controller, state.is_charging)
        self._on_update(state)
