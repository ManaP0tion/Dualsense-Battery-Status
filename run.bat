@echo off
title DualSense Battery Status

echo DualSense 배터리 상태 확인 프로그램 시작 중...
echo Starting DualSense Battery Status...
echo.

:: Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo [Error] Python is not installed.
    echo.
    echo Python 3.8 이상을 설치해주세요: https://www.python.org/downloads/
    echo Please install Python 3.8 or higher: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Install/upgrade dependencies quietly
echo 의존성 설치 중... / Installing dependencies...
python -m pip install --quiet --upgrade -r requirements.txt

echo 프로그램 실행 중... / Launching application...
echo.
python dualsense_battery.py

if %errorlevel% neq 0 (
    echo.
    echo [오류] 프로그램 실행 중 문제가 발생했습니다.
    echo [Error] An error occurred while running the program.
    pause
)
