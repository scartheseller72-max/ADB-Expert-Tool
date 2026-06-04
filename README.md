# ADB Expert Tool v2.0

## Professional Android Debug Bridge Control Center

### Features

#### 1. Dashboard
- Real-time device detection and selection
- Device information panel (model, brand, Android version, IMEI, battery, root status)
- Quick stats cards
- One-click screenshot, screen recording, cache clear

#### 2. Interactive Shell
- Full ADB shell terminal with command history (Up/Down arrows)
- Root shell toggle
- Async command execution (no UI freezing)

#### 3. File Manager
- Browse device filesystem with ls -la
- Double-click to navigate directories
- Push/Pull files
- Delete files/directories

#### 4. App Manager
- List all/system/third-party packages
- Install APK files
- Uninstall apps
- Clear app data
- Backup app + data (APK + ADB backup)

#### 5. Flash & Recovery
- Fastboot partition flashing (boot, recovery, system, etc.)
- Recovery sideload for OTA/ZIP files
- Output console for progress

#### 6. Unlock & Root Tools
- Check bootloader lock status
- OEM Unlock / OEM Lock
- Check root status
- Push Magisk APK
- Remount system read-write
- Enable/Disable dm-verity
- Lock screen bypass tools (educational/owned devices only)

#### 7. Diagnostics
- Logcat viewer (last 500 lines)
- Kernel dmesg
- Process list with kill capability
- Battery stats
- Memory info (/proc/meminfo)
- CPU info
- Thermal zones (temperature monitoring)

#### 8. Network Tools
- Wireless ADB (connect over WiFi)
- Port forwarding (local/remote)
- Proxy configuration
- Network interface info

#### 9. Automation
- Touch events (tap, swipe)
- Text input injection
- Key event injection (Home, Back, Power, Volume, etc.)
- Macro recording and playback
- Monkey stress testing

#### 10. Advanced Tools
- Build.prop property viewer/editor
- Partition table viewer
- Disk usage (df -h)
- UI hierarchy dump (for automation)
- Contacts/SMS database extraction (root required)
- WiFi configuration dump (root required)
- Factory reset command

### Requirements
- Python 3.8+
- Android Platform Tools (ADB & Fastboot)
- Windows OS (optimized for Win32)

### How to Run
```
# Method 1: Double-click launch.bat
launch.bat

# Method 2: Direct Python
python adb_gui.py
```

### Safety Warnings
- Bootloader unlock WILL wipe all data
- Flashing wrong images can permanently brick your device
- Root tools may void warranty
- Lock bypass tools are for educational use on owned devices only
- Always backup before performing dangerous operations

### Auto-Detection
The tool automatically detects ADB in common locations:
- System PATH
- Android SDK platform-tools
- Local ./platform-tools/

### Support
This is an expert-level tool. Use at your own risk!
