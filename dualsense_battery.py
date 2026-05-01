"""
DualSense Battery Status / 듀얼센스 배터리 상태 확인
A Windows program for monitoring PS5 DualSense controller battery level.
"""

import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import hid
except ImportError:
    print("hid 모듈을 설치해주세요: pip install hid>=1.0.5")
    sys.exit(1)

# DualSense USB Vendor/Product IDs
DUALSENSE_VID = 0x054C
DUALSENSE_PID = 0x0CE6

# HID report constants
USB_REPORT_ID = 0x01
USB_BATTERY_OFFSET = 53   # Byte index in USB input report (64-byte)

BT_REPORT_ID = 0x31
BT_BATTERY_OFFSET = 54    # Byte index in Bluetooth input report (78-byte)

# Battery status codes (lower nibble of battery byte)
BATTERY_STATUS_LABELS = {
    0: ("방전 중", "Discharging"),
    1: ("충전 중", "Charging"),
    2: ("완전 충전", "Full"),
    10: ("전압 오류", "Voltage Error"),
    11: ("온도 오류", "Temp Error"),
}

REFRESH_INTERVAL_MS = 5000  # Auto-refresh every 5 seconds

# Color thresholds for the battery bar
COLOR_CRITICAL = "#e74c3c"   # red   – below 20 %
COLOR_LOW = "#e67e22"        # orange – 20-40 %
COLOR_MEDIUM = "#f1c40f"     # yellow – 40-60 %
COLOR_GOOD = "#2ecc71"       # green  – above 60 %
COLOR_CHARGING = "#3498db"   # blue   – charging


def find_dualsense():
    """Return the first DualSense HID device descriptor dict, or None."""
    for device_info in hid.enumerate():
        if (device_info["vendor_id"] == DUALSENSE_VID
                and device_info["product_id"] == DUALSENSE_PID):
            return device_info
    return None


def read_battery(device: hid.device):
    """
    Read one HID input report and return (battery_percent, status_code, connection_type).
    battery_percent : int 0-100, or None on error.
    status_code     : int (see BATTERY_STATUS_LABELS), or None on error.
    connection_type : "USB" | "Bluetooth"
    """
    try:
        report = device.read(78, timeout_ms=3000)
    except OSError:
        return None, None, None

    if not report:
        return None, None, None

    report_id = report[0]

    if report_id == BT_REPORT_ID and len(report) > BT_BATTERY_OFFSET:
        battery_byte = report[BT_BATTERY_OFFSET]
        connection_type = "Bluetooth"
    else:
        # Default to USB report layout (report_id == 0x01)
        if len(report) <= USB_BATTERY_OFFSET:
            return None, None, None
        battery_byte = report[USB_BATTERY_OFFSET]
        connection_type = "USB"

    battery_level = (battery_byte >> 4) & 0x0F   # upper nibble: 0-10
    status_code = battery_byte & 0x0F             # lower nibble: status

    # Some firmware versions report level 0-8 (×12.5%) or 0-10 (×10%).
    # Clamp to 100 to be safe.
    battery_percent = min(battery_level * 10, 100)

    return battery_percent, status_code, connection_type


def battery_color(percent: int, status_code: int) -> str:
    """Return a colour string for the given battery state."""
    if status_code == 1:          # charging
        return COLOR_CHARGING
    if percent >= 60:
        return COLOR_GOOD
    if percent >= 40:
        return COLOR_MEDIUM
    if percent >= 20:
        return COLOR_LOW
    return COLOR_CRITICAL


class DualSenseBatteryApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("DualSense 배터리 상태 / Battery Status")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")

        # Internal state
        self._device: hid.device | None = None
        self._refresh_job = None
        self._lock = threading.Lock()

        self._build_ui()
        self._schedule_refresh(delay=100)   # first refresh almost immediately

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 20, "pady": 10}

        # Header
        header = tk.Label(
            self,
            text="🎮  DualSense 배터리 상태",
            font=("Segoe UI", 16, "bold"),
            fg="#e0e0e0",
            bg="#1a1a2e",
        )
        header.pack(pady=(20, 5))

        sub_header = tk.Label(
            self,
            text="PlayStation 5 DualSense Controller",
            font=("Segoe UI", 9),
            fg="#7f8c8d",
            bg="#1a1a2e",
        )
        sub_header.pack()

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # Connection status row
        conn_frame = tk.Frame(self, bg="#1a1a2e")
        conn_frame.pack(fill="x", **pad)

        tk.Label(
            conn_frame,
            text="연결 상태 / Connection:",
            font=("Segoe UI", 10),
            fg="#bdc3c7",
            bg="#1a1a2e",
        ).pack(side="left")

        self._conn_label = tk.Label(
            conn_frame,
            text="감지 중… / Detecting…",
            font=("Segoe UI", 10, "bold"),
            fg="#f39c12",
            bg="#1a1a2e",
        )
        self._conn_label.pack(side="left", padx=8)

        # Connection type (USB / Bluetooth)
        self._conn_type_label = tk.Label(
            conn_frame,
            text="",
            font=("Segoe UI", 9),
            fg="#7f8c8d",
            bg="#1a1a2e",
        )
        self._conn_type_label.pack(side="left")

        # Battery percentage
        pct_frame = tk.Frame(self, bg="#1a1a2e")
        pct_frame.pack(**pad)

        self._pct_label = tk.Label(
            pct_frame,
            text="-- %",
            font=("Segoe UI", 48, "bold"),
            fg="#2ecc71",
            bg="#1a1a2e",
        )
        self._pct_label.pack()

        # Progress bar (custom canvas)
        bar_frame = tk.Frame(self, bg="#1a1a2e")
        bar_frame.pack(fill="x", padx=30, pady=(0, 5))

        self._bar_bg = tk.Canvas(
            bar_frame,
            width=340,
            height=22,
            bg="#2c3e50",
            highlightthickness=0,
            bd=0,
        )
        self._bar_bg.pack()
        self._bar_fill = self._bar_bg.create_rectangle(
            0, 0, 0, 22, fill=COLOR_GOOD, outline=""
        )

        # Charging / status label
        self._status_label = tk.Label(
            self,
            text="",
            font=("Segoe UI", 11),
            fg="#3498db",
            bg="#1a1a2e",
        )
        self._status_label.pack(pady=(5, 0))

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # Last updated
        self._updated_label = tk.Label(
            self,
            text="마지막 업데이트: --",
            font=("Segoe UI", 8),
            fg="#7f8c8d",
            bg="#1a1a2e",
        )
        self._updated_label.pack()

        # Refresh button
        self._refresh_btn = tk.Button(
            self,
            text="🔄  새로고침 / Refresh",
            font=("Segoe UI", 10),
            bg="#2c3e50",
            fg="#e0e0e0",
            activebackground="#34495e",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            command=self._manual_refresh,
        )
        self._refresh_btn.pack(pady=(8, 20))

        # Bind window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Device management
    # ------------------------------------------------------------------
    def _open_device(self, device_info: dict) -> hid.device | None:
        """Open a HID device handle from an enumerated device descriptor."""
        try:
            dev = hid.device()
            dev.open_path(device_info["path"])
            dev.set_nonblocking(False)
            return dev
        except OSError:
            return None

    def _close_device(self):
        with self._lock:
            if self._device is not None:
                try:
                    self._device.close()
                except OSError:
                    pass
                self._device = None

    # ------------------------------------------------------------------
    # Refresh logic
    # ------------------------------------------------------------------
    def _schedule_refresh(self, delay: int = REFRESH_INTERVAL_MS):
        if self._refresh_job is not None:
            self.after_cancel(self._refresh_job)
        self._refresh_job = self.after(delay, self._do_refresh)

    def _manual_refresh(self):
        # Cancel pending auto-refresh and trigger immediately
        self._close_device()
        self._schedule_refresh(delay=0)

    def _do_refresh(self):
        """Run in the main thread via after(); may block briefly on HID read."""
        device_info = find_dualsense()

        if device_info is None:
            self._update_ui_disconnected()
            self._close_device()
            self._schedule_refresh()
            return

        # Re-open if device path changed or not yet open
        with self._lock:
            if self._device is None:
                self._device = self._open_device(device_info)

            if self._device is None:
                self._update_ui_error("장치를 열 수 없습니다 / Cannot open device")
                self._schedule_refresh()
                return

            percent, status_code, conn_type = read_battery(self._device)

        if percent is None:
            # Read failed – close device so we re-open next cycle
            self._close_device()
            self._update_ui_error("읽기 실패 / Read failed")
        else:
            self._update_ui_battery(percent, status_code, conn_type)

        self._schedule_refresh()

    # ------------------------------------------------------------------
    # UI update helpers
    # ------------------------------------------------------------------
    def _update_ui_disconnected(self):
        self._conn_label.config(text="연결 안됨 / Disconnected", fg="#e74c3c")
        self._conn_type_label.config(text="")
        self._pct_label.config(text="-- %", fg="#7f8c8d")
        self._status_label.config(text="컨트롤러를 연결해주세요 / Connect your controller", fg="#7f8c8d")
        self._bar_bg.coords(self._bar_fill, 0, 0, 0, 22)
        self._bar_bg.itemconfig(self._bar_fill, fill=COLOR_CRITICAL)
        self._updated_label.config(text=f"마지막 업데이트: {_now()}")

    def _update_ui_error(self, msg: str):
        self._conn_label.config(text="오류 / Error", fg="#e74c3c")
        self._status_label.config(text=msg, fg="#e74c3c")
        self._updated_label.config(text=f"마지막 업데이트: {_now()}")

    def _update_ui_battery(self, percent: int, status_code: int, conn_type: str):
        color = battery_color(percent, status_code)
        ko_status, en_status = BATTERY_STATUS_LABELS.get(
            status_code, (f"알 수 없음({status_code})", f"Unknown({status_code})")
        )
        status_text = f"{ko_status} / {en_status}"

        self._conn_label.config(text="연결됨 / Connected", fg="#2ecc71")
        self._conn_type_label.config(text=f"({conn_type})", fg="#7f8c8d")
        self._pct_label.config(text=f"{percent} %", fg=color)
        self._status_label.config(text=status_text, fg=color)

        # Update progress bar (canvas width = 340)
        bar_width = int(340 * percent / 100)
        self._bar_bg.coords(self._bar_fill, 0, 0, bar_width, 22)
        self._bar_bg.itemconfig(self._bar_fill, fill=color)

        self._updated_label.config(text=f"마지막 업데이트: {_now()}")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def _on_close(self):
        if self._refresh_job is not None:
            self.after_cancel(self._refresh_job)
        self._close_device()
        self.destroy()


def _now() -> str:
    return time.strftime("%H:%M:%S")


def main():
    app = DualSenseBatteryApp()
    app.mainloop()


if __name__ == "__main__":
    main()
