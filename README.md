# 🎮 DualSense Battery Status

A lightweight, unobtrusive system tray application for Windows that monitors and displays the battery status of your PlayStation 5 DualSense controller. 

## ✨ Features

- **System Tray Icon**: Displays a dynamic battery icon that updates based on the current charge level and charging status.
- **Detailed Popup**: Left-click the tray icon to view a sleek, floating popup with precise battery percentage and connection type (USB/Bluetooth).
- **Low Battery Alerts**: Get notified when your controller's battery drops below a customizable threshold.
- **Customizable Interval**: Choose how frequently the app checks the battery status (5s, 15s, 30s, or 60s).
- **Auto-Start**: Option to run the application automatically when Windows starts.
- **Multi-language Support**: Supports both English and Korean (한국어).

## 📥 Installation & Usage

1. Go to the [Releases](../../releases/latest) page.
2. Download the latest `DualSenseBatteryStatus.exe` file.
3. Run the downloaded `.exe` file. The app will immediately appear in your system tray.
4. Right-click the tray icon to access **Settings** or to **Quit**. Left-click to view the detailed battery status popup.

## 🛠️ Building from Source

If you prefer to run the script directly or build the executable yourself:

1. Clone this repository:
   ```cmd
   git clone https://github.com/ManaP0tion/Dualsense-Battery-Status.git
   cd Dualsense-Battery-Status
   ```

2. Install the required dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

3. Run the application directly:
   ```cmd
   python src/main.py
   ```

4. Build the executable using PyInstaller:
   ```cmd
   pip install pyinstaller
   pyinstaller --onefile --noconsole --name DualSenseBattery --icon=assets/app_icon.ico src/main.py
   ```
   The executable will be located in the `dist/` directory.
