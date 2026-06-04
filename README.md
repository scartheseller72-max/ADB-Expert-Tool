# ADB Expert Tool v3.0

## Ultimate Professional Android Control Center

> Max Expert Level - Unanswered, Unbound, Raw Expert

---

### Bulletproof Device Detection
- Auto-scans: PATH, ANDROID_HOME, registry, full disk, all drives
- Handles: ADB, Fastboot, Recovery, Sideload, EDL modes
- Detects: Unauthorized, Offline, No Permissions states
- Works even when ADB isn't in PATH

### 10 Expert Tabs

| Tab | What It Does |
|-----|-------------|
| **Dashboard** | 20+ device stats (IMEI, RAM, Storage, SELinux, Kernel, Chipset, Thermal, Battery Health) |
| **Shell** | Full terminal with root toggle, command history (Up/Down), async execution |
| **Files** | File browser with push/pull/delete/mkdir/search, double-click navigation |
| **Apps** | Install/uninstall/backup/clear/force-stop/disable/enable, permissions management |
| **Flash** | Fastboot flash ANY partition (boot/recovery/system/vendor/super/vbmeta/dtbo/userdata/cache/persist/modem/product), sideload ZIP/OTA, erase/format partitions |
| **Unlock & Root** | OEM Unlock (old), Flashing Unlock (new), OEM Lock, Root check, Magisk push, Remount RW, dm-verity, SELinux enforcing/permissive, **Lock bypass (swipe/null PIN/settings crash/key deletion/FRP)** |
| **Diagnostics** | Logcat, dmesg, processes, battery, memory, CPU, thermal zones, disk usage, mounts, kernel, partitions, running services, current app |
| **Network** | Wireless ADB (WiFi), Bluetooth pair/connect, port forwarding, reverse forwarding, proxy |
| **Automation** | Tap/swipe/long-press, text/key injection, 18 key buttons, monkey stress test, developer options (animations/stay awake/show touches/mock location/DPI/resolution) |
| **Advanced** | Build.prop editor, settings browser (global/secure/system), UI dump, contacts/SMS DB extract, WiFi config, users/accounts, factory reset, wipe cache, full ROM flash package, media scan |

### Key Features
- **20+ device stats** on dashboard (IMEI, RAM, storage, SELinux, kernel, chipset, battery temp/health)
- **Full fastboot support** - flash, erase, format, boot, update, getvar, active slot, EDL mode
- **Lock bypass tools** - swipe, null PIN, settings crash, key file deletion, FRP data deletion
- **Root tools** - Magisk, remount, dm-verity, SELinux toggle
- **Developer options** - animation scale, stay awake, show touches, pointer location, DPI/resolution
- **Network tools** - WiFi ADB, Bluetooth, port forwarding, proxy
- **Safety** - Double confirmation on dangerous operations
- **Async execution** - UI never freezes
- **Dark professional theme** - GitHub-inspired dark UI

### Requirements
- Python 3.8+ (Windows)
- Android Platform Tools (ADB & Fastboot) - auto-detected

### Run
```
launch.bat
# or
python adb_gui.py
```

### Safety Warnings
- Bootloader unlock **WILL wipe all data**
- Wrong flash images **can permanently brick** your device
- Lock bypass tools are **for owned devices only**
- Always backup before dangerous operations

### Auto-Detection Locations (Windows)
1. System PATH
2. ANDROID_HOME / ANDROID_SDK_ROOT
3. %LOCALAPPDATA%\Android\Sdk\platform-tools
4. %USERPROFILE%\platform-tools
5. C:\platform-tools
6. Windows Registry
7. Full disk scan (depth 5)
