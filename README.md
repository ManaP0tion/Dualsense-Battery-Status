# DualSense Battery Status / 듀얼센스 배터리 상태 확인

PS5 DualSense 컨트롤러의 배터리 잔량을 실시간으로 확인하는 Windows 프로그램입니다.  
A Windows program for monitoring your PS5 DualSense controller's battery level in real time.

---

## 스크린샷 / Screenshot

> 프로그램을 실행하면 컨트롤러 연결 상태와 배터리 잔량이 색상 바와 함께 표시됩니다.  
> When launched, the app shows connection state and battery level with a colour-coded bar.

---

## 사전 요구 사항 / Prerequisites

| 항목 / Item | 버전 / Version |
|---|---|
| Python | 3.8 이상 / 3.8 or higher |
| OS | Windows 10 / 11 |
| 컨트롤러 연결 / Controller connection | USB 또는 블루투스 / USB or Bluetooth |

---

## 설치 및 실행 / Installation & Run

### 방법 1 – BAT 파일 (권장 / Recommended)

```bat
run.bat
```

`run.bat`을 더블클릭하면 의존성 자동 설치 후 프로그램이 실행됩니다.  
Double-click `run.bat` to auto-install dependencies and launch the app.

### 방법 2 – 직접 실행 / Manual

```bash
pip install -r requirements.txt
python dualsense_battery.py
```

---

## 기능 / Features

- ✅ USB 및 블루투스 연결 모두 지원 / Supports both USB and Bluetooth connections
- ✅ 배터리 잔량 % 및 색상 바 표시 / Displays battery % with a colour-coded progress bar
- ✅ 충전 중 / 방전 중 / 완전 충전 상태 표시 / Shows Charging / Discharging / Full status
- ✅ 5초마다 자동 새로고침 / Auto-refreshes every 5 seconds
- ✅ 수동 새로고침 버튼 / Manual refresh button
- ✅ 컨트롤러 미연결 시 대기 모드 / Waiting mode when controller is disconnected

---

## 배터리 색상 / Battery Colours

| 색상 / Colour | 조건 / Condition |
|---|---|
| 🟢 초록 / Green | 60 % 이상 / 60 % or above |
| 🟡 노랑 / Yellow | 40–59 % |
| 🟠 주황 / Orange | 20–39 % |
| 🔴 빨강 / Red | 20 % 미만 / Below 20 % |
| 🔵 파랑 / Blue | 충전 중 / Charging |

---

## 라이선스 / License

MIT License – see [LICENSE](LICENSE).