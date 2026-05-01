import time
import sys
from pathlib import Path

# src 폴더를 모듈 경로에 추가하여 controller.py를 불러올 수 있게 합니다.
sys.path.insert(0, str(Path(__file__).parent.parent))
from controller import ControllerMonitor

def on_battery_update(state):
    pass # 콜백은 상태가 '변경'될 때만 호출되므로 여기서는 비워둡니다.

print("듀얼센스 배터리 모니터링 시작... (종료하려면 Ctrl+C)")

# 1초마다 배터리 상태 업데이트
monitor = ControllerMonitor(on_battery_update, poll_interval=1)
monitor.start()

try:
    while True:
        state = monitor.current_state
        if state.connected:
            print(f"[{time.strftime('%H:%M:%S')}] 배터리: {state.percent}% | 충전 중: {'O' if state.is_charging else 'X'} | 연결: {state.connection}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] 컨트롤러 연결 안 됨 (또는 찾는 중...)")
        time.sleep(1)
except KeyboardInterrupt:
    monitor.stop()
    print("\n테스트가 종료되었습니다.")