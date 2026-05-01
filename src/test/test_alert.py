import sys
import tkinter as tk
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import i18n
from popup import AlertPopup


@dataclass
class FakeBatteryState:
    connected:   bool = True
    percent:     int  = 15
    is_charging: bool = False
    connection:  str  = "Bluetooth"


def test_alert_popup():
    root = tk.Tk()
    root.withdraw()

    i18n.init(root, "ko")

    state = FakeBatteryState(percent=15)
    alert = AlertPopup(root)
    alert.show(state)

    print("AlertPopup을 띄웠습니다. 화면 우측 하단을 확인해 주세요.")
    root.mainloop()


if __name__ == "__main__":
    test_alert_popup()
