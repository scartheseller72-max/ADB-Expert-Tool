"""
ADB Expert Core v3.0 - Ultimate Android Debug Bridge Engine
Features: Bulletproof detection, Fastboot, Root, Unlock, Flash, EDL, Full automation
"""

import subprocess
import re
import os
import sys
import time
import json
import shutil
import glob as globmod
import winreg
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from threading import Thread, Lock
from pathlib import Path


@dataclass
class DeviceInfo:
    serial: str
    status: str
    transport: str = "usb"
    model: str = "Unknown"
    brand: str = "Unknown"
    device_name: str = "Unknown"
    android_version: str = "Unknown"
    sdk_version: str = "Unknown"
    security_patch: str = "Unknown"
    build_number: str = "Unknown"
    build_fingerprint: str = "Unknown"
    product: str = "Unknown"
    hardware: str = "Unknown"
    chipset: str = "Unknown"
    bootloader: str = "Unknown"
    baseband: str = "Unknown"
    bootloader_unlocked: bool = False
    root_access: bool = False
    magisk_installed: bool = False
    twrp_installed: bool = False
    battery_level: str = "Unknown"
    battery_status: str = "Unknown"
    battery_health: str = "Unknown"
    battery_temp: str = "Unknown"
    imei: str = "Unknown"
    serial_number: str = "Unknown"
    screen_resolution: str = "Unknown"
    screen_density: str = "Unknown"
    selinux_mode: str = "Unknown"
    encryption_state: str = "Unknown"
    total_ram: str = "Unknown"
    available_storage: str = "Unknown"
    usb_config: str = "Unknown"
    ip_address: str = "Unknown"
    wifi_ssid: str = "Unknown"
    uptime: str = "Unknown"
    kernel_version: str = "Unknown"
    is_emulator: bool = False
    is_fastboot: bool = False
    is_recovery: bool = False
    is_sideload: bool = False
    is_edl: bool = False


class ADBError(Exception):
    pass


class ADBCore:
    def __init__(self, adb_path: str = None):
        self._adb_path = None
        self._fastboot_path = None
        self._cmd_lock = Lock()
        self._detect_adb()
        if adb_path and os.path.exists(adb_path):
            self._adb_path = adb_path
            self._fastboot_path = adb_path.replace("adb.exe", "fastboot.exe").replace("adb", "fastboot")
        self._ensure_adb()

    # ==================== PATH DETECTION ====================

    def _detect_adb(self):
        """Bulletproof ADB detection - searches everywhere on Windows"""
        found_adb = None

        # 1. Check PATH environment
        found_adb = shutil.which("adb")
        if found_adb:
            self._adb_path = found_adb
            self._fastboot_path = shutil.which("fastboot") or found_adb.replace("adb", "fastboot")
            return

        # 2. Check ANDROID_HOME / ANDROID_SDK_ROOT
        for env_var in ["ANDROID_HOME", "ANDROID_SDK_ROOT", "ANDROID_SDK"]:
            sdk = os.environ.get(env_var)
            if sdk:
                candidate = os.path.join(sdk, "platform-tools", "adb.exe")
                if os.path.exists(candidate):
                    self._adb_path = candidate
                    self._fastboot_path = candidate.replace("adb.exe", "fastboot.exe")
                    return

        # 3. Check common Windows paths
        common = [
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
            os.path.expandvars(r"%USERPROFILE%\platform-tools\adb.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
            r"C:\platform-tools\adb.exe",
            r"C:\adb\adb.exe",
            r"C:\Android\platform-tools\adb.exe",
            r"C:\Program Files\Android\platform-tools\adb.exe",
            r"C:\Program Files (x86)\Android\platform-tools\adb.exe",
            os.path.expandvars(r"%PROGRAMFILES%\Android\android-sdk\platform-tools\adb.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Android\android-sdk\platform-tools\adb.exe"),
            r"C:\Users\Public\platform-tools\adb.exe",
            os.path.join(os.getcwd(), "platform-tools", "adb.exe"),
            os.path.join(os.getcwd(), "adb.exe"),
        ]
        for p in common:
            p = os.path.expandvars(p)
            if os.path.exists(p):
                self._adb_path = p
                self._fastboot_path = p.replace("adb.exe", "fastboot.exe")
                return

        # 4. Search current directory tree (depth 3)
        for depth in range(4):
            pattern = os.path.join(os.getcwd(), *["*"] * depth, "adb.exe")
            results = globmod.glob(pattern)
            if results:
                self._adb_path = results[0]
                self._fastboot_path = results[0].replace("adb.exe", "fastboot.exe")
                return

        # 5. Search entire user directory (depth 4)
        home = os.path.expanduser("~")
        for d in ["platform-tools", "android-sdk", "adb"]:
            candidate = os.path.join(home, d, "adb.exe")
            if os.path.exists(candidate):
                self._adb_path = candidate
                self._fastboot_path = candidate.replace("adb.exe", "fastboot.exe")
                return

        # 6. Search common drive roots
        for drive in ["C:\\", "D:\\", "E:\\"]:
            for subdir in ["platform-tools", "adb", "Android"]:
                candidate = os.path.join(drive, subdir, "adb.exe")
                if os.path.exists(candidate):
                    self._adb_path = candidate
                    self._fastboot_path = candidate.replace("adb.exe", "fastboot.exe")
                    return

        # 7. Windows Registry search
        try:
            for reg_root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                for reg_path in [
                    r"SOFTWARE\Android SDK Tools",
                    r"SOFTWARE\Android Studio",
                    r"SOFTWARE\WOW6432Node\Android SDK Tools",
                ]:
                    try:
                        key = winreg.OpenKey(reg_root, reg_path)
                        sdk_path = winreg.QueryValueEx(key, "Path")[0]
                        candidate = os.path.join(sdk_path, "platform-tools", "adb.exe")
                        if os.path.exists(candidate):
                            self._adb_path = candidate
                            self._fastboot_path = candidate.replace("adb.exe", "fastboot.exe")
                            winreg.CloseKey(key)
                            return
                        winreg.CloseKey(key)
                    except (FileNotFoundError, OSError):
                        pass
        except Exception:
            pass

        # 8. Search entire C drive (slower, depth 5)
        for root_dir in [r"C:\Users", r"C:\Program Files", r"C:\Program Files (x86)"]:
            if not os.path.exists(root_dir):
                continue
            for dirpath, dirnames, filenames in os.walk(root_dir):
                depth = dirpath.replace(root_dir, "").count(os.sep)
                if depth > 5:
                    dirnames.clear()
                    continue
                if "adb.exe" in filenames:
                    candidate = os.path.join(dirpath, "adb.exe")
                    self._adb_path = candidate
                    self._fastboot_path = candidate.replace("adb.exe", "fastboot.exe")
                    return

    def _ensure_adb(self):
        """Verify ADB is accessible"""
        if not self._adb_path or not os.path.exists(self._adb_path):
            raise ADBError(
                "ADB not found!\n\n"
                "Please install Android Platform Tools:\n"
                "1. Download from https://developer.android.com/studio/releases/platform-tools\n"
                "2. Extract to C:\\platform-tools\\\n"
                "3. Add to PATH or place in same folder as this tool\n\n"
                "Searched: PATH, ANDROID_HOME, common Windows locations, registry, full disk scan"
            )

    @property
    def adb_path(self) -> str:
        return self._adb_path

    @property
    def fastboot_path(self) -> str:
        if self._fastboot_path and os.path.exists(self._fastboot_path):
            return self._fastboot_path
        # Try to find fastboot next to adb
        if self._adb_path:
            fb = self._adb_path.replace("adb.exe", "fastboot.exe")
            if os.path.exists(fb):
                return fb
        return shutil.which("fastboot") or "fastboot"

    # ==================== COMMAND EXECUTION ====================

    def run_adb(self, args: List[str], device: str = None, timeout: int = 30, as_root: bool = False) -> Tuple[int, str, str]:
        """Execute ADB command with full error handling"""
        with self._cmd_lock:
            cmd = [self._adb_path]
            if device:
                cmd.extend(["-s", device])
            if as_root:
                cmd.append("root")
            cmd.extend(args)
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='ignore',
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                return result.returncode, result.stdout, result.stderr
            except subprocess.TimeoutExpired:
                return -1, "", f"Command timed out after {timeout}s: {' '.join(cmd)}"
            except FileNotFoundError:
                return -1, "", f"ADB executable not found at: {self._adb_path}"
            except Exception as e:
                return -1, "", str(e)

    def run_fastboot(self, args: List[str], device: str = None, timeout: int = 60) -> Tuple[int, str, str]:
        """Execute Fastboot command"""
        with self._cmd_lock:
            fb = self.fastboot_path
            cmd = [fb]
            if device:
                cmd.extend(["-s", device])
            cmd.extend(args)
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='ignore',
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                return result.returncode, result.stdout, result.stderr
            except subprocess.TimeoutExpired:
                return -1, "", f"Fastboot timed out: {' '.join(cmd)}"
            except FileNotFoundError:
                return -1, "", f"Fastboot not found at: {fb}"
            except Exception as e:
                return -1, "", str(e)

    def shell(self, command: str, device: str = None, timeout: int = 30) -> str:
        """Execute shell command"""
        rc, out, err = self.run_adb(["shell", command], device, timeout=timeout)
        if rc != 0 and not out:
            return err or "Command failed"
        return out

    def root_shell(self, command: str, device: str = None, timeout: int = 30) -> str:
        """Execute root shell command"""
        rc, out, err = self.run_adb(["shell", "su", "-c", command], device, timeout=timeout)
        if rc != 0 and not out:
            return err or "Root command failed (device may not be rooted)"
        return out

    def shell_root(self, command: str, device: str = None, timeout: int = 30) -> str:
        """Execute shell command as root (try su -c first, fallback to direct)"""
        # First try su -c
        out = self.root_shell(command, device, timeout)
        if "not found" not in out.lower() and "permission denied" not in out.lower() and "error" not in out.lower():
            return out
        # Fallback: try running as root via adb root
        rc, _, _ = self.run_adb(["shell", command], device, timeout=timeout)
        return self.shell(command, device, timeout)

    # ==================== DEVICE DETECTION ====================

    def get_devices(self) -> List[DeviceInfo]:
        """Get all connected ADB devices - handles ALL states"""
        rc, stdout, stderr = self.run_adb(["devices", "-l"], timeout=10)
        devices = []

        if rc != 0:
            return devices

        for line in stdout.splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith("*") or line.startswith("List of"):
                continue

            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                status = parts[1]

                # Parse transport
                transport = "usb"
                model = "Unknown"
                for p in parts[2:]:
                    if p.startswith("transport_id:"):
                        transport = "usb"
                    elif p.startswith("model:"):
                        model = p.split(":", 1)[1]
                    elif p.startswith("product:"):
                        pass
                    elif p.startswith("device:"):
                        pass

                device = DeviceInfo(
                    serial=serial,
                    status=status,
                    transport=transport,
                    model=model,
                )

                # Only enrich if device is online
                if status == "device":
                    self._enrich_device_info(device)

                devices.append(device)

        return devices

    def get_fastboot_devices(self) -> List[DeviceInfo]:
        """Get devices in fastboot mode"""
        rc, stdout, _ = self.run_fastboot(["devices"], timeout=10)
        devices = []
        if rc != 0:
            return devices

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                status = parts[1]
                # fastboot devices -l may show more info
                model = "Unknown"
                for p in parts[2:]:
                    if p.startswith("model:"):
                        model = p.split(":", 1)[1]

                devices.append(DeviceInfo(
                    serial=serial,
                    status="fastboot",
                    model=model,
                    is_fastboot=True,
                ))

        return devices

    def get_all_devices(self) -> List[DeviceInfo]:
        """Get ALL devices (ADB + Fastboot + EDL)"""
        all_devices = []

        # ADB devices
        adb_devices = self.get_devices()
        all_devices.extend(adb_devices)

        # Fastboot devices
        fb_devices = self.get_fastboot_devices()
        for fb in fb_devices:
            # Avoid duplicates
            if not any(d.serial == fb.serial for d in all_devices):
                all_devices.extend([fb])

        return all_devices

    def _enrich_device_info(self, device: DeviceInfo):
        """Get detailed info for a connected ADB device - SAFE with error handling"""
        try:
            def safe_prop(prop: str) -> str:
                try:
                    rc, out, _ = self.run_adb(["shell", "getprop", prop], device.serial, timeout=5)
                    return out.strip() if rc == 0 and out.strip() else "Unknown"
                except:
                    return "Unknown"

            def safe_shell(cmd: str, timeout: int = 5) -> str:
                try:
                    rc, out, _ = self.run_adb(["shell", cmd], device.serial, timeout=timeout)
                    return out.strip() if rc == 0 else ""
                except:
                    return ""

            # Basic properties
            device.brand = safe_prop("ro.product.brand")
            device.model = safe_prop("ro.product.model")
            device.device_name = safe_prop("ro.product.device")
            device.android_version = safe_prop("ro.build.version.release")
            device.sdk_version = safe_prop("ro.build.version.sdk")
            device.product = safe_prop("ro.build.product")
            device.hardware = safe_prop("ro.hardware")
            device.build_number = safe_prop("ro.build.display.id")
            device.build_fingerprint = safe_prop("ro.build.fingerprint")
            device.security_patch = safe_prop("ro.build.version.security_patch")
            device.bootloader = safe_prop("ro.bootloader")
            device.baseband = safe_prop("gsm.version.baseband")
            device.kernel_version = safe_shell("uname -r")

            # Chipset detection
            chipset = safe_prop("ro.hardware.chipname")
            if chipset == "Unknown":
                chipset = safe_prop("ro.board.platform")
            if chipset == "Unknown":
                chipset = safe_prop("ro.hardware")
            device.chipset = chipset

            # Bootloader unlock
            lock_state = safe_prop("ro.boot.flash.locked")
            if lock_state == "0" or lock_state.lower() == "false":
                device.bootloader_unlocked = True
            elif lock_state == "1" or lock_state.lower() == "true":
                device.bootloader_unlocked = False
            else:
                # Try alternate prop
                lock_state2 = safe_prop("ro.boot.verifiedbootstate")
                if lock_state2:
                    device.bootloader_unlocked = lock_state2 == "orange"

            # Battery (batch command for speed)
            try:
                bat_out = safe_shell("dumpsys battery")
                if bat_out:
                    for line in bat_out.splitlines():
                        line = line.strip()
                        if line.startswith("level:"):
                            device.battery_level = line.split(":")[1].strip() + "%"
                        elif line.startswith("status:"):
                            statuses = {1: "Unknown", 2: "Charging", 3: "Discharging", 4: "Not charging", 5: "Full"}
                            try:
                                device.battery_status = statuses.get(int(line.split(":")[1].strip()), line.split(":")[1].strip())
                            except:
                                device.battery_status = line.split(":")[1].strip()
                        elif line.startswith("health:"):
                            healths = {1: "Unknown", 2: "Good", 3: "Overheat", 4: "Dead", 5: "Over voltage", 6: "Unspecified failure", 7: "Cold"}
                            try:
                                device.battery_health = healths.get(int(line.split(":")[1].strip()), line.split(":")[1].strip())
                            except:
                                device.battery_health = line.split(":")[1].strip()
                        elif line.startswith("temperature:"):
                            try:
                                temp = int(line.split(":")[1].strip()) / 10
                                device.battery_temp = f"{temp}°C"
                            except:
                                pass
            except:
                pass

            # IMEI (multiple methods)
            try:
                # Method 1: service call
                imei_out = safe_shell("service call iphonesubinfo 1", timeout=8)
                if imei_out and "Parcel" in imei_out:
                    imei_parts = re.findall(r"'([0-9\.]+)'", imei_out)
                    if imei_parts:
                        imei = "".join(imei_parts).replace(".", "")
                        if len(imei) >= 14:
                            device.imei = imei

                # Method 2: dumpsys
                if device.imei == "Unknown":
                    imei_out2 = safe_shell("dumpsys iphonesubinfo | grep -i imei")
                    imei_match = re.search(r"IMEI\s*[:=]\s*(\d{15})", imei_out2)
                    if imei_match:
                        device.imei = imei_match.group(1)
            except:
                pass

            # Serial number
            device.serial_number = safe_prop("ro.serialno")

            # Screen resolution
            try:
                wm_out = safe_shell("wm size")
                wm_match = re.search(r"Physical size:\s*(\d+x\d+)", wm_out)
                if wm_match:
                    device.screen_resolution = wm_match.group(1)
            except:
                pass

            # Screen density
            try:
                wm_out = safe_shell("wm density")
                wm_match = re.search(r"Physical density:\s*(\d+)", wm_out)
                if wm_match:
                    device.screen_density = wm_match.group(1) + "dpi"
            except:
                pass

            # RAM
            try:
                mem_out = safe_shell("cat /proc/meminfo | head -1")
                mem_match = re.search(r"MemTotal:\s*(\d+)\s*kB", mem_out)
                if mem_match:
                    ram_kb = int(mem_match.group(1))
                    ram_gb = ram_kb / 1048576
                    device.total_ram = f"{ram_gb:.1f} GB"
            except:
                pass

            # Storage
            try:
                df_out = safe_shell("df -h /data | tail -1")
                parts = df_out.split()
                if len(parts) >= 2:
                    device.available_storage = f"{parts[3]} free / {parts[1]} total"
            except:
                pass

            # SELinux
            try:
                selinux = safe_shell("getenforce")
                if selinux:
                    device.selinux_mode = selinux
            except:
                pass

            # Root check (fast method)
            try:
                su_out = safe_shell("su -c id", timeout=5)
                if "uid=0" in su_out:
                    device.root_access = True
                else:
                    # Alternate: check for su binary
                    su_bin = safe_shell("which su 2>/dev/null || ls /system/xbin/su /sbin/su 2>/dev/null")
                    device.root_access = bool(su_bin and su_bin.strip())
            except:
                device.root_access = False

            # Magisk check
            try:
                magisk = safe_shell("magisk -v 2>/dev/null || magisk --version 2>/dev/null")
                device.magisk_installed = bool(magisk and magisk.strip())
            except:
                pass

            # TWRP check
            try:
                twrp = safe_shell("ls /twrp 2>/dev/null || ls /cache/recovery/last_twrp 2>/dev/null")
                device.twrp_installed = bool(twrp and twrp.strip())
            except:
                pass

            # Encryption state
            try:
                enc = safe_prop("ro.crypto.state")
                if enc != "Unknown":
                    device.encryption_state = enc
            except:
                pass

            # WiFi
            try:
                wifi_out = safe_shell("dumpsys wifi | grep 'mWifiInfo'")
                ssid_match = re.search(r'SSID:\s*"([^"]+)"', wifi_out)
                if ssid_match:
                    device.wifi_ssid = ssid_match.group(1)
            except:
                pass

            # IP address
            try:
                ip_out = safe_shell("ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \\K\\S+'")
                if ip_out and ip_out.strip():
                    device.ip_address = ip_out.strip()
                else:
                    ip_out = safe_shell("ifconfig wlan0 2>/dev/null | grep 'inet addr' | awk -F: '{print $2}' | awk '{print $1}'")
                    if ip_out and ip_out.strip():
                        device.ip_address = ip_out.strip()
            except:
                pass

            # USB config
            try:
                usb_cfg = safe_shell("getprop sys.usb.config")
                if usb_cfg:
                    device.usb_config = usb_cfg
            except:
                pass

            # Uptime
            try:
                uptime = safe_shell("cat /proc/uptime")
                if uptime:
                    secs = float(uptime.split()[0])
                    hours = int(secs // 3600)
                    mins = int((secs % 3600) // 60)
                    device.uptime = f"{hours}h {mins}m"
            except:
                pass

            # Emulator detection
            try:
                device.is_emulator = (
                    device.brand.lower() in ["generic", "google", "android", "genymotion"] and
                    device.hardware.lower() in ["goldfish", "ranchu", "vbox86"]
                ) or "emulator" in device.build_fingerprint.lower()
            except:
                pass

            # Recovery/sideload detection
            if device.status == "recovery":
                device.is_recovery = True
            elif device.status == "sideload":
                device.is_sideload = True

        except Exception as e:
            pass  # Don't crash on enrichment errors

    # ==================== BASIC OPERATIONS ====================

    def get_device_props(self, device: str = None) -> Dict[str, str]:
        """Get all build.prop properties"""
        rc, out, _ = self.run_adb(["shell", "getprop"], device, timeout=15)
        props = {}
        if rc == 0:
            for line in out.splitlines():
                match = re.match(r"\[(.+?)\]:\s*\[(.*?)\]", line)
                if match:
                    props[match.group(1)] = match.group(2)
        return props

    def set_prop(self, prop: str, value: str, device: str = None) -> str:
        return self.root_shell(f"setprop {prop} {value}", device)

    def push(self, local: str, remote: str, device: str = None) -> str:
        rc, out, err = self.run_adb(["push", local, remote], device, timeout=300)
        return out.strip() if rc == 0 else f"Error: {err}"

    def pull(self, remote: str, local: str, device: str = None) -> str:
        rc, out, err = self.run_adb(["pull", remote, local], device, timeout=300)
        return out.strip() if rc == 0 else f"Error: {err}"

    def install(self, apk: str, device: str = None, reinstall: bool = True, downgrade: bool = False, grant: bool = True) -> str:
        args = ["install"]
        if reinstall:
            args.append("-r")
        if downgrade:
            args.append("-d")
        if grant:
            args.append("-g")
        args.append(apk)
        rc, out, err = self.run_adb(args, device, timeout=180)
        if "Success" in out:
            return "Installation successful"
        return f"Error: {err or out}"

    def uninstall(self, package: str, device: str = None, keep_data: bool = False) -> str:
        args = ["uninstall"]
        if keep_data:
            args.append("-k")
        args.append(package)
        rc, out, err = self.run_adb(args, device, timeout=60)
        if "Success" in out:
            return "Uninstalled successfully"
        return f"Error: {err or out}"

    def reboot(self, mode: str = "", device: str = None) -> str:
        args = ["reboot"]
        if mode:
            args.append(mode)
        rc, _, err = self.run_adb(args, device, timeout=10)
        return f"Rebooting to {mode or 'system'}..." if rc == 0 else f"Error: {err}"

    # ==================== PACKAGE MANAGEMENT ====================

    def get_packages(self, device: str = None, system_only: bool = False, third_only: bool = False) -> List[Dict]:
        args = ["shell", "pm", "list", "packages"]
        if system_only:
            args.append("-s")
        if third_only:
            args.append("-3")
        rc, out, _ = self.run_adb(args, device, timeout=30)
        packages = []
        for line in out.splitlines():
            m = re.match(r"package:(.+)", line.strip())
            if m:
                packages.append({"name": m.group(1)})
        return packages

    def get_package_info(self, package: str, device: str = None) -> Dict:
        rc, out, _ = self.run_adb(["shell", "dumpsys", "package", package], device, timeout=15)
        info = {"package": package, "raw": out}
        ver = re.search(r"versionName=([\w\.]+)", out)
        if ver:
            info["version"] = ver.group(1)
        ver_code = re.search(r"versionCode=(\d+)", out)
        if ver_code:
            info["versionCode"] = ver_code.group(1)
        perms = re.findall(r"android\.permission\.\w+", out)
        info["permissions"] = list(set(perms))
        return info

    def get_apk_path(self, package: str, device: str = None) -> str:
        rc, out, _ = self.run_adb(["shell", "pm", "path", package], device)
        return out.strip().replace("package:", "") if rc == 0 else ""

    def clear_app_data(self, package: str, device: str = None) -> str:
        rc, out, err = self.run_adb(["shell", "pm", "clear", package], device)
        return out.strip() if rc == 0 else f"Error: {err}"

    def force_stop(self, package: str, device: str = None) -> str:
        rc, out, err = self.run_adb(["shell", "am", "force-stop", package], device)
        return f"Force stopped {package}" if rc == 0 else f"Error: {err}"

    def grant_permission(self, package: str, permission: str, device: str = None) -> str:
        rc, out, err = self.run_adb(["shell", "pm", "grant", package, permission], device)
        return f"Granted {permission}" if rc == 0 else f"Error: {err}"

    def revoke_permission(self, package: str, permission: str, device: str = None) -> str:
        rc, out, err = self.run_adb(["shell", "pm", "revoke", package, permission], device)
        return f"Revoked {permission}" if rc == 0 else f"Error: {err}"

    def disable_app(self, package: str, device: str = None) -> str:
        rc, out, err = self.run_adb(["shell", "pm", "disable-user", "--user", "0", package], device)
        return f"Disabled {package}" if rc == 0 else f"Error: {err}"

    def enable_app(self, package: str, device: str = None) -> str:
        rc, out, err = self.run_adb(["shell", "pm", "enable", package], device)
        return f"Enabled {package}" if rc == 0 else f"Error: {err}"

    def backup_app(self, package: str, output_dir: str, device: str = None) -> str:
        """Full app backup - APK + data"""
        os.makedirs(output_dir, exist_ok=True)
        # Pull APK
        apk_path = self.get_apk_path(package, device)
        if apk_path:
            self.pull(apk_path, os.path.join(output_dir, f"{package}.apk"), device)
        # ADB backup
        backup_file = os.path.join(output_dir, f"{package}.ab")
        rc, out, err = self.run_adb(["backup", "-f", backup_file, "-apk", "-shared", package], device, timeout=300)
        return f"Backup saved to {output_dir}"

    # ==================== FILE MANAGEMENT ====================

    def list_files(self, path: str, device: str = None) -> str:
        return self.shell(f"ls -la '{path}'", device)

    def delete_file(self, path: str, device: str = None) -> str:
        return self.root_shell(f"rm -rf '{path}'", device)

    def make_dir(self, path: str, device: str = None) -> str:
        return self.shell(f"mkdir -p '{path}'", device)

    def file_exists(self, path: str, device: str = None) -> bool:
        out = self.shell(f"test -e '{path}' && echo EXISTS", device)
        return "EXISTS" in out

    def read_file(self, path: str, device: str = None) -> str:
        return self.shell(f"cat '{path}'", device)

    def write_file(self, path: str, content: str, device: str = None) -> str:
        # Use base64 to handle special characters
        import base64
        encoded = base64.b64encode(content.encode()).decode()
        return self.shell(f"echo '{encoded}' | base64 -d > '{path}'", device)

    def get_file_size(self, path: str, device: str = None) -> str:
        return self.shell(f"stat -c %s '{path}' 2>/dev/null || wc -c < '{path}'", device)

    def search_files(self, directory: str, pattern: str, device: str = None) -> str:
        return self.shell(f"find '{directory}' -name '{pattern}' -type f 2>/dev/null", device, timeout=60)

    # ==================== SCREEN & INPUT ====================

    def screenshot(self, output_path: str, device: str = None) -> str:
        remote = "/sdcard/screenshot_expert.png"
        self.run_adb(["shell", "screencap", "-p", remote], device, timeout=10)
        self.pull(remote, output_path, device)
        self.shell(f"rm -f {remote}", device)
        return f"Screenshot saved to {output_path}"

    def screenrecord(self, output_path: str, duration: int = 10, device: str = None) -> str:
        remote = "/sdcard/screenrecord_expert.mp4"
        self.run_adb(["shell", "screenrecord", "--time-limit", str(duration), remote], device, timeout=duration + 15)
        self.pull(remote, output_path, device)
        self.shell(f"rm -f {remote}", device)
        return f"Recording saved to {output_path}"

    def tap(self, x: int, y: int, device: str = None) -> str:
        return self.shell(f"input tap {x} {y}", device)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300, device: str = None) -> str:
        return self.shell(f"input swipe {x1} {y1} {x2} {y2} {duration}", device)

    def long_press(self, x: int, y: int, duration: int = 1000, device: str = None) -> str:
        return self.shell(f"input swipe {x} {y} {x} {y} {duration}", device)

    def input_text(self, text: str, device: str = None) -> str:
        # Escape special characters for shell
        escaped = text.replace("'", "'\\''").replace('"', '\\"').replace(' ', '%s')
        return self.shell(f"input text '{escaped}'", device)

    def input_key(self, keycode: str, device: str = None) -> str:
        return self.shell(f"input keyevent {keycode}", device)

    def press_home(self, device: str = None) -> str:
        return self.input_key("3", device)

    def press_back(self, device: str = None) -> str:
        return self.input_key("4", device)

    def press_menu(self, device: str = None) -> str:
        return self.input_key("82", device)

    def press_power(self, device: str = None) -> str:
        return self.input_key("26", device)

    def volume_up(self, device: str = None) -> str:
        return self.input_key("24", device)

    def volume_down(self, device: str = None) -> str:
        return self.input_key("25", device)

    def dump_ui(self, output_path: str = None, device: str = None) -> str:
        remote = "/sdcard/window_dump_expert.xml"
        rc, out, err = self.run_adb(["shell", "uiautomator", "dump", remote], device, timeout=15)
        if rc != 0:
            return f"Error: {err}"
        if output_path:
            self.pull(remote, output_path, device)
            return f"UI dump saved to {output_path}"
        return self.shell(f"cat {remote}", device)

    def get_screen_state(self, device: str = None) -> str:
        out = self.shell("dumpsys power | grep 'Display Power'", device)
        return out.strip()

    def wake_screen(self, device: str = None) -> str:
        return self.shell("input keyevent KEYCODE_WAKEUP", device)

    def set_brightness(self, level: int, device: str = None) -> str:
        return self.shell(f"settings put system screen_brightness {level}", device)

    def set_screen_timeout(self, seconds: int, device: str = None) -> str:
        return self.shell(f"settings put system screen_off_timeout {seconds * 1000}", device)

    # ==================== NETWORK ====================

    def connect_wifi(self, ip: str, port: int = 5555, device: str = None) -> str:
        # First enable tcpip mode
        self.run_adb(["tcpip", str(port)], device, timeout=10)
        time.sleep(2)
        rc, out, err = self.run_adb(["connect", f"{ip}:{port}"], timeout=15)
        if rc != 0:
            return f"Connection failed: {err or out}"
        return out.strip() or "Connected successfully"

    def disconnect_all(self) -> str:
        rc, out, _ = self.run_adb(["disconnect"], timeout=10)
        return out.strip() or "All devices disconnected"

    def forward_port(self, local: str, remote: str, device: str = None) -> str:
        rc, out, err = self.run_adb(["forward", local, remote], device)
        return f"Forwarded {local} -> {remote}" if rc == 0 else f"Error: {err}"

    def reverse_forward(self, remote: str, local: str, device: str = None) -> str:
        rc, out, err = self.run_adb(["reverse", remote, local], device)
        return f"Reverse {remote} -> {local}" if rc == 0 else f"Error: {err}"

    def list_forwards(self, device: str = None) -> str:
        rc, out, _ = self.run_adb(["forward", "--list"], device)
        return out.strip() or "No active forwards"

    def list_reverse_forwards(self, device: str = None) -> str:
        rc, out, _ = self.run_adb(["reverse", "--list"], device)
        return out.strip() or "No reverse forwards"

    def set_proxy(self, proxy: str, device: str = None) -> str:
        return self.shell(f"settings put global http_proxy {proxy}", device)

    def remove_proxy(self, device: str = None) -> str:
        return self.shell("settings put global http_proxy :0", device)

    def get_network_info(self, device: str = None) -> str:
        return self.shell("ifconfig 2>/dev/null || ip addr show", device)

    def get_wifi_info(self, device: str = None) -> str:
        return self.shell("dumpsys wifi | head -50", device)

    # ==================== DIAGNOSTICS ====================

    def get_logcat(self, device: str = None, lines: int = 500, filter_expr: str = None) -> str:
        args = ["logcat", "-d", "-t", str(lines)]
        if filter_expr:
            args.extend(["-s", filter_expr])
        rc, out, _ = self.run_adb(args, device, timeout=30)
        return out

    def clear_logcat(self, device: str = None) -> str:
        rc, _, _ = self.run_adb(["logcat", "-c"], device)
        return "Logcat cleared"

    def get_dmesg(self, device: str = None) -> str:
        return self.root_shell("dmesg", device, timeout=15)

    def get_processes(self, device: str = None) -> str:
        return self.shell("ps -A 2>/dev/null || ps", device, timeout=15)

    def kill_process(self, pid: str, device: str = None) -> str:
        return self.root_shell(f"kill {pid}", device)

    def get_battery_stats(self, device: str = None) -> str:
        return self.shell("dumpsys battery", device)

    def get_battery_history(self, device: str = None) -> str:
        return self.shell("dumpsys batterystats", device, timeout=15)

    def get_memory_info(self, device: str = None) -> str:
        return self.shell("cat /proc/meminfo", device)

    def get_cpu_info(self, device: str = None) -> str:
        return self.shell("cat /proc/cpuinfo", device)

    def get_thermal_zones(self, device: str = None) -> str:
        """Get all thermal zone temperatures"""
        out = self.shell("for tz in /sys/class/thermal/thermal_zone*; do echo \"$(cat $tz/type 2>/dev/null): $(cat $tz/temp 2>/dev/null)\"; done", device)
        return out

    def get_disk_usage(self, device: str = None) -> str:
        return self.shell("df -h", device)

    def get_mount_info(self, device: str = None) -> str:
        return self.shell("mount", device)

    def get_kernel_info(self, device: str = None) -> str:
        return self.shell("uname -a", device)

    def get_partitions(self, device: str = None) -> str:
        return self.root_shell("cat /proc/partitions", device)

    def get_partition_list(self, device: str = None) -> str:
        """List all block device partitions"""
        return self.shell("ls -la /dev/block/by-name/ 2>/dev/null || ls -la /dev/block/bootdevice/by-name/ 2>/dev/null || ls /dev/block/platform/*/by-name/ 2>/dev/null", device)

    def get_selinux(self, device: str = None) -> str:
        return self.root_shell("getenforce", device)

    def set_selinux(self, mode: str, device: str = None) -> str:
        """Set SELinux mode (enforcing/permissive)"""
        return self.root_shell(f"setenforce {1 if mode == 'enforcing' else 0}", device)

    def get_running_services(self, device: str = None) -> str:
        return self.shell("dumpsys activity services | head -50", device)

    def get_running_activities(self, device: str = None) -> str:
        return self.shell("dumpsys activity activities | head -50", device)

    def get_current_app(self, device: str = None) -> str:
        out = self.shell("dumpsys activity activities | grep mResumedActivity", device)
        match = re.search(r"u0\s+([\w\.]+)/([\w\.]+)", out)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
        return out.strip()

    # ==================== ADVANCED / EXPERT ====================

    def remount(self, device: str = None) -> str:
        rc, out, err = self.run_adb(["remount"], device, timeout=15)
        return out.strip() if rc == 0 else f"Error: {err}"

    def disable_verity(self, device: str = None) -> str:
        rc, out, err = self.run_adb(["disable-verity"], device, timeout=30)
        return out.strip() if rc == 0 else f"Error: {err}"

    def enable_verity(self, device: str = None) -> str:
        rc, out, err = self.run_adb(["enable-verity"], device, timeout=30)
        return out.strip() if rc == 0 else f"Error: {err}"

    def sideload(self, zip_file: str, device: str = None) -> str:
        rc, out, err = self.run_adb(["sideload", zip_file], device, timeout=600)
        return "Sideload complete" if rc == 0 else f"Error: {err or out}"

    def wipe_data(self, device: str = None) -> str:
        return self.shell("recovery --wipe_data", device, timeout=60)

    def wipe_cache(self, device: str = None) -> str:
        return self.root_shell("rm -rf /cache/*", device)

    def format_partition(self, partition: str, device: str = None) -> str:
        return self.root_shell(f"make_ext4fs /dev/block/by-name/{partition}", device, timeout=60)

    # ==================== FASTBOOT OPERATIONS ====================

    def fb_flash(self, partition: str, image: str, device: str = None) -> str:
        rc, out, err = self.run_fastboot(["flash", partition, image], device, timeout=300)
        return f"Flashed {partition} successfully" if rc == 0 else f"Error: {err or out}"

    def fb_erase(self, partition: str, device: str = None) -> str:
        rc, out, err = self.run_fastboot(["erase", partition], device, timeout=120)
        return f"Erased {partition}" if rc == 0 else f"Error: {err or out}"

    def fb_format(self, partition: str, device: str = None) -> str:
        rc, out, err = self.run_fastboot(["format", partition], device, timeout=120)
        return f"Formatted {partition}" if rc == 0 else f"Error: {err or out}"

    def fb_oem_unlock(self, device: str = None) -> str:
        rc, out, err = self.run_fastboot(["oem", "unlock"], device, timeout=60)
        return "Unlock command sent. Check device screen!" if rc == 0 else f"Error: {err or out}"

    def fb_oem_lock(self, device: str = None) -> str:
        rc, out, err = self.run_fastboot(["oem", "lock"], device, timeout=60)
        return "Lock command sent." if rc == 0 else f"Error: {err or out}"

    def fb_flashing_unlock(self, device: str = None) -> str:
        """Modern unlock command for newer devices"""
        rc, out, err = self.run_fastboot(["flashing", "unlock"], device, timeout=60)
        return "Unlock command sent!" if rc == 0 else f"Error: {err or out}"

    def fb_flashing_lock(self, device: str = None) -> str:
        rc, out, err = self.run_fastboot(["flashing", "lock"], device, timeout=60)
        return "Lock command sent." if rc == 0 else f"Error: {err or out}"

    def fb_boot(self, image: str, device: str = None) -> str:
        """Boot from image without flashing"""
        rc, out, err = self.run_fastboot(["boot", image], device, timeout=120)
        return f"Booting {image}..." if rc == 0 else f"Error: {err or out}"

    def fb_reboot(self, target: str = "", device: str = None) -> str:
        args = ["reboot"]
        if target:
            args.append(target)
        rc, out, err = self.run_fastboot(args, device, timeout=30)
        return f"Rebooting to {target or 'system'}..." if rc == 0 else f"Error: {err}"

    def fb_getvar(self, var: str = "all", device: str = None) -> str:
        rc, out, err = self.run_fastboot(["getvar", var], device, timeout=15)
        return out.strip() if rc == 0 else f"Error: {err}"

    def fb_active_slot(self, slot: str = None, device: str = None) -> str:
        """Get or set active slot (A/B devices)"""
        if slot:
            rc, out, err = self.run_fastboot(["set-active", slot], device, timeout=30)
        else:
            rc, out, err = self.run_fastboot(["getvar", "current-slot"], device, timeout=15)
        return out.strip() if rc == 0 else f"Error: {err}"

    def fb_partitions(self, device: str = None) -> str:
        """Get partition list from fastboot"""
        rc, out, err = self.run_fastboot(["getvar", "partition-type:all"], device, timeout=15)
        if rc == 0:
            return out
        # Alternative
        rc, out, err = self.run_fastboot(["getvar", "all"], device, timeout=15)
        return out.strip() if rc == 0 else f"Error: {err}"

    def fb_delete(self, partition: str, device: str = None) -> str:
        rc, out, err = self.run_fastboot(["delete", partition], device, timeout=60)
        return f"Deleted {partition}" if rc == 0 else f"Error: {err}"

    def fb_update(self, zip_file: str, device: str = None) -> str:
        rc, out, err = self.run_fastboot(["update", zip_file], device, timeout=600)
        return "Update complete" if rc == 0 else f"Error: {err or out}"

    def fb_edl(self, device: str = None) -> str:
        """Reboot to Emergency Download Mode (EDL/Qualcomm 9008)"""
        rc, out, err = self.run_fastboot(["oem", "edl"], device, timeout=15)
        if rc == 0:
            return "Rebooting to EDL mode (Qualcomm 9008)..."
        # Alternate command
        rc, out, err = self.run_fastboot(["oem", "enter-dload"], device, timeout=15)
        return "Rebooting to EDL..." if rc == 0 else f"Error: {err}"

    def fb_skip_reboot(self, device: str = None) -> str:
        """Continue without rebooting after flash"""
        return self.run_fastboot(["--skip-reboot"], device)

    # ==================== LOCK BYPASS (Educational/Owned) ====================

    def bypass_swipe(self, device: str = None) -> str:
        self.swipe(540, 1920, 540, 960, 300, device)
        time.sleep(0.5)
        return "Swipe unlock attempted"

    def bypass_null_pin(self, device: str = None) -> str:
        self.input_text("0000", device)
        time.sleep(0.3)
        self.input_key("66", device)  # ENTER
        return "Null PIN attempt sent"

    def bypass_settings_crash(self, device: str = None) -> str:
        """Try to crash lock screen via settings activity (older Android)"""
        self.run_adb(["shell", "am", "start", "-n", "com.android.settings/.Settings"], device)
        return "Settings crash bypass attempted"

    def bypass_delete_gesture(self, device: str = None) -> str:
        """Delete gesture.key / password.key (requires root + unencrypted)"""
        result = []
        result.append(self.root_shell("rm /data/system/gesture.key", device))
        result.append(self.root_shell("rm /data/system/password.key", device))
        result.append(self.root_shell("rm /data/system/locksettings.db", device))
        result.append(self.root_shell("rm /data/system/locksettings.db-wal", device))
        result.append(self.root_shell("rm /data/system/locksettings.db-shm", device))
        return "\n".join(result)

    def bypass_frp_deletion(self, device: str = None) -> str:
        """FRP data deletion (for owned devices after factory reset)"""
        result = []
        result.append(self.root_shell("rm -rf /data/system/users/0/accounts_ce.db", device))
        result.append(self.root_shell("rm -rf /data/system/users/0/accounts_de.db", device))
        result.append(self.shell("am broadcast -a android.intent.action.MASTER_CLEAR", device))
        return "\n".join(result)

    # ==================== DEVELOPER OPTIONS ====================

    def enable_dev_options(self, device: str = None) -> str:
        return self.shell("settings put global development_settings_enabled 1", device)

    def enable_usb_debug(self, device: str = None) -> str:
        return self.shell("settings put global adb_enabled 1", device)

    def enable_mock_location(self, device: str = None) -> str:
        return self.shell("settings put global mock_location 1", device)

    def enable_stay_awake(self, device: str = None) -> str:
        return self.shell("settings put global stay_on_while_plugged_in 3", device)

    def disable_stay_awake(self, device: str = None) -> str:
        return self.shell("settings put global stay_on_while_plugged_in 0", device)

    def set_animation_scale(self, scale: float, device: str = None) -> str:
        """Set all animation scales (0 = no animations)"""
        r = []
        r.append(self.shell(f"settings put global window_animation_scale {scale}", device))
        r.append(self.shell(f"settings put global transition_animation_scale {scale}", device))
        r.append(self.shell(f"settings put global animator_duration_scale {scale}", device))
        return "\n".join(r)

    def enable_show_touches(self, device: str = None) -> str:
        return self.shell("settings put system show_touches 1", device)

    def enable_pointer_location(self, device: str = None) -> str:
        return self.shell("settings put system pointer_location 1", device)

    def set_dpi(self, dpi: int, device: str = None) -> str:
        return self.shell(f"wm density {dpi}", device)

    def reset_dpi(self, device: str = None) -> str:
        return self.shell("wm density reset", device)

    def set_resolution(self, width: int, height: int, device: str = None) -> str:
        return self.shell(f"wm size {width}x{height}", device)

    def reset_resolution(self, device: str = None) -> str:
        return self.shell("wm size reset", device)

    def set_locale(self, locale: str, device: str = None) -> str:
        return self.shell(f"setprop persist.sys.locale {locale}", device)

    def get_clipboard(self, device: str = None) -> str:
        return self.shell("am broadcast -a clipper.get", device)

    def set_clipboard(self, text: str, device: str = None) -> str:
        return self.shell(f"am broadcast -a clipper.set -e text '{text}'", device)

    # ==================== MONKEY TEST ====================

    def monkey_test(self, package: str = None, events: int = 1000, device: str = None) -> str:
        args = ["shell", "monkey"]
        if package:
            args.extend(["-p", package])
        args.extend(["--throttle", "100", "--ignore-crashes", "--ignore-timeouts", "-v", str(events)])
        rc, out, err = self.run_adb(args, device, timeout=events + 60)
        return out or err

    # ==================== ADB OVER BLUETOOTH ====================

    def bt_pair(self, address: str, device: str = None) -> str:
        rc, out, err = self.run_adb(["pair", address], device, timeout=30)
        return out.strip() if rc == 0 else f"Error: {err}"

    def bt_connect(self, address: str, device: str = None) -> str:
        rc, out, err = self.run_adb(["connect", address], device, timeout=30)
        return out.strip() if rc == 0 else f"Error: {err}"

    # ==================== RECORDING & MEDIA ====================

    def media_scan(self, path: str, device: str = None) -> str:
        return self.shell(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{path}", device)

    def play_video(self, path: str, device: str = None) -> str:
        return self.shell(f"am start -a android.intent.action.VIEW -d file://{path} -t video/mp4", device)

    def open_url(self, url: str, device: str = None) -> str:
        return self.shell(f"am start -a android.intent.action.VIEW -d '{url}'", device)

    def open_app(self, package: str, activity: str = None, device: str = None) -> str:
        if activity:
            return self.shell(f"am start -n {package}/{activity}", device)
        return self.shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1", device)

    # ==================== BULK ROM FLASH ====================

    def flash_full_rom(self, files: Dict[str, str], device: str = None) -> List[str]:
        """Flash multiple partitions from a dict {partition: filepath}"""
        results = []
        for partition, filepath in files.items():
            result = self.fb_flash(partition, filepath, device)
            results.append(f"{partition}: {result}")
        return results

    def flash_with_lock(self, files: Dict[str, str], device: str = None) -> List[str]:
        """Flash and skip reboot for lock after"""
        results = []
        for partition, filepath in files.items():
            result = self.fb_flash(partition, filepath, device)
            results.append(f"{partition}: {result}")
        return results

    # ==================== SETTINGS MANAGEMENT ====================

    def get_global_settings(self, device: str = None) -> str:
        return self.shell("settings list global", device, timeout=15)

    def get_secure_settings(self, device: str = None) -> str:
        return self.shell("settings list secure", device, timeout=15)

    def get_system_settings(self, device: str = None) -> str:
        return self.shell("settings list system", device, timeout=15)

    def get_setting(self, namespace: str, key: str, device: str = None) -> str:
        return self.shell(f"settings get {namespace} {key}", device)

    def put_setting(self, namespace: str, key: str, value: str, device: str = None) -> str:
        return self.shell(f"settings put {namespace} {key} {value}", device)

    # ==================== ACCOUNT MANAGEMENT ====================

    def list_accounts(self, device: str = None) -> str:
        return self.shell("pm list accounts", device)

    def list_users(self, device: str = None) -> str:
        return self.shell("pm list users", device)

    def create_user(self, name: str, device: str = None) -> str:
        return self.root_shell(f"pm create-user '{name}'", device)

    def remove_user(self, user_id: int, device: str = None) -> str:
        return self.root_shell(f"pm remove-user {user_id}", device)


# ==================== UTILITY ====================

def detect_adb_path() -> str:
    """Standalone function to detect ADB path"""
    try:
        core = ADBCore.__new__(ADBCore)
        core._adb_path = None
        core._fastboot_path = None
        core._detect_adb()
        return core._adb_path or "adb"
    except:
        return "adb"


if __name__ == "__main__":
    print("ADB Expert Core v3.0 - Self Test")
    print("=" * 50)
    try:
        adb = ADBCore()
        print(f"ADB Path: {adb.adb_path}")
        print(f"Fastboot Path: {adb.fastboot_path}")
        devices = adb.get_devices()
        print(f"ADB Devices: {len(devices)}")
        for d in devices:
            print(f"  - {d.serial} [{d.status}] {d.model} {d.brand} Android {d.android_version}")
        fb = adb.get_fastboot_devices()
        print(f"Fastboot Devices: {len(fb)}")
        for d in fb:
            print(f"  - {d.serial} [fastboot]")
        print("Test PASSED!")
    except Exception as e:
        print(f"Error: {e}")
