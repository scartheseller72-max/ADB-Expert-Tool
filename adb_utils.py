"""
ADB Expert Core v3.5 - Non-blocking, cached, bulletproof
Key fix: Async device enrichment with TTL cache - NO UI freeze
"""

import subprocess, re, os, sys, time, shutil
import glob as globmod, winreg
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from threading import Thread, Lock, RLock
from collections import OrderedDict

# ─── Device Info ───

@dataclass
class DeviceInfo:
    serial: str = ""
    status: str = ""
    transport: str = "usb"
    model: str = "?"
    brand: str = "?"
    device_name: str = "?"
    android_version: str = "?"
    sdk_version: str = "?"
    security_patch: str = "?"
    build_number: str = "?"
    build_fingerprint: str = "?"
    product: str = "?"
    hardware: str = "?"
    chipset: str = "?"
    bootloader_ver: str = "?"
    baseband: str = "?"
    bootloader_unlocked: bool = False
    root_access: bool = False
    magisk_installed: bool = False
    twrp_installed: bool = False
    battery_level: str = "?"
    battery_status: str = "?"
    battery_health: str = "?"
    battery_temp: str = "?"
    imei: str = "?"
    serial_number: str = "?"
    screen_resolution: str = "?"
    screen_density: str = "?"
    selinux_mode: str = "?"
    encryption_state: str = "?"
    total_ram: str = "?"
    available_storage: str = "?"
    usb_config: str = "?"
    ip_address: str = "?"
    wifi_ssid: str = "?"
    uptime: str = "?"
    kernel_version: str = "?"
    is_emulator: bool = False
    is_fastboot: bool = False
    is_recovery: bool = False
    is_sideload: bool = False
    is_edl: bool = False
    enriched: bool = False


class ADBError(Exception):
    pass


# ─── Device Cache ───

class DeviceCache:
    """TTL cache for device info - prevents repeated ADB calls"""
    def __init__(self, ttl_seconds: float = 10.0):
        self._cache: Dict[str, tuple[float, DeviceInfo]] = {}
        self._lock = RLock()
        self._ttl = ttl_seconds

    def get(self, serial: str) -> Optional[DeviceInfo]:
        with self._lock:
            entry = self._cache.get(serial)
            if entry and (time.time() - entry[0]) < self._ttl:
                return entry[1]
        return None

    def set(self, info: DeviceInfo):
        with self._lock:
            self._cache[info.serial] = (time.time(), info)

    def clear(self):
        with self._lock:
            self._cache.clear()


# ─── Core ───

class ADBCore:
    def __init__(self, adb_path: str = None):
        self._adb_path = None
        self._fastboot_path = None
        self._cmd_lock = Lock()
        self._cache = DeviceCache(ttl_seconds=8.0)
        self._detect_adb()
        if adb_path and os.path.exists(adb_path):
            self._adb_path = adb_path
            self._fastboot_path = adb_path.replace("adb.exe", "fastboot.exe").replace("adb", "fastboot")
        self._ensure_adb()

    # ─── PATH DETECTION ───

    def _detect_adb(self):
        found = shutil.which("adb")
        if found:
            self._adb_path = found
            self._fastboot_path = shutil.which("fastboot") or found.replace("adb", "fastboot")
            return
        for env_var in ["ANDROID_HOME", "ANDROID_SDK_ROOT"]:
            sdk = os.environ.get(env_var)
            if sdk:
                c = os.path.join(sdk, "platform-tools", "adb.exe")
                if os.path.exists(c):
                    self._adb_path = c
                    self._fastboot_path = c.replace("adb.exe", "fastboot.exe")
                    return
        common = [
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
            os.path.expandvars(r"%USERPROFILE%\platform-tools\adb.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
            r"C:\platform-tools\adb.exe", r"C:\adb\adb.exe",
            r"C:\Android\platform-tools\adb.exe",
            os.path.expandvars(r"%PROGRAMFILES%\Android\android-sdk\platform-tools\adb.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Android\android-sdk\platform-tools\adb.exe"),
            os.path.join(os.getcwd(), "platform-tools", "adb.exe"),
            os.path.join(os.getcwd(), "adb.exe"),
        ]
        for p in common:
            p = os.path.expandvars(p)
            if os.path.exists(p):
                self._adb_path = p
                self._fastboot_path = p.replace("adb.exe", "fastboot.exe")
                return
        for depth in range(4):
            pattern = os.path.join(os.getcwd(), *["*"] * depth, "adb.exe")
            results = globmod.glob(pattern)
            if results:
                self._adb_path = results[0]
                self._fastboot_path = results[0].replace("adb.exe", "fastboot.exe")
                return
        try:
            for reg_root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                for reg_path in [r"SOFTWARE\Android SDK Tools", r"SOFTWARE\Android Studio",
                                r"SOFTWARE\WOW6432Node\Android SDK Tools"]:
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
                    except:
                        pass
        except:
            pass

    def _ensure_adb(self):
        if not self._adb_path or not os.path.exists(self._adb_path):
            raise ADBError(
                "ADB not found!\n\n"
                "Please install Android Platform Tools:\n"
                "Download: developer.android.com/tools/releases/platform-tools\n"
                "Extract to C:\\platform-tools\\"
            )

    @property
    def adb_path(self) -> str:
        return self._adb_path

    @property
    def fastboot_path(self) -> str:
        if self._fastboot_path and os.path.exists(self._fastboot_path):
            return self._fastboot_path
        if self._adb_path:
            fb = self._adb_path.replace("adb.exe", "fastboot.exe")
            if os.path.exists(fb):
                return fb
        return shutil.which("fastboot") or "fastboot"

    # ─── COMMAND EXEC ───

    def _run(self, cmd: List[str], timeout: int = 10) -> tuple:
        with self._cmd_lock:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=timeout, encoding='utf-8', errors='ignore',
                                   creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                return r.returncode, r.stdout, r.stderr
            except subprocess.TimeoutExpired:
                return -1, "", f"TIMEOUT:{timeout}s"
            except FileNotFoundError:
                return -1, "", "ADB NOT FOUND"
            except:
                return -1, "", "ERROR"

    def adb(self, args: list, device: str = None, timeout: int = 10):
        cmd = [self._adb_path]
        if device:
            cmd += ["-s", device]
        cmd += args
        return self._run(cmd, timeout)

    def fb(self, args: list, device: str = None, timeout: int = 30):
        cmd = [self.fastboot_path]
        if device:
            cmd += ["-s", device]
        cmd += args
        return self._run(cmd, timeout)

    def shell(self, cmd: str, device: str = None, timeout: int = 10) -> str:
        rc, out, err = self.adb(["shell", cmd], device, timeout)
        return out.strip() if rc == 0 and out.strip() else (err.strip() or out.strip())

    def root_shell(self, cmd: str, device: str = None, timeout: int = 10) -> str:
        rc, out, err = self.adb(["shell", "su", "-c", cmd], device, timeout)
        return out.strip() if rc == 0 and out.strip() else (err.strip() or out.strip())

    # ─── FAST DEVICE SCAN (no blocking) ───

    def get_devices(self) -> List[DeviceInfo]:
        """Ultra-fast scan - no enrichment, returns in < 3 seconds"""
        devices = []
        rc, stdout, _ = self.adb(["devices", "-l"], timeout=5)
        if rc != 0:
            return devices
        for line in stdout.splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                model = "?"
                for p in parts[2:]:
                    if p.startswith("model:"):
                        model = p.split(":", 1)[1]
                        break
                devices.append(DeviceInfo(serial=parts[0], status=parts[1], model=model))
        return devices

    def get_fastboot_devices(self) -> List[DeviceInfo]:
        """Fast fastboot scan"""
        rc, stdout, _ = self.fb(["devices"], timeout=5)
        devices = []
        if rc != 0:
            return devices
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                devices.append(DeviceInfo(serial=parts[0], status="fastboot", is_fastboot=True))
        return devices

    # ─── ASYNC ENRICHMENT (non-blocking) ───

    def enrich_device_async(self, serial: str, callback: Callable[[DeviceInfo], None]):
        """Enrich device info in background thread - calls callback when done"""
        cached = self._cache.get(serial)
        if cached and cached.enriched:
            callback(cached)
            return

        def worker():
            device = DeviceInfo(serial=serial, status="device")
            self._do_enrich(device)
            self._cache.set(device)
            callback(device)

        t = Thread(target=worker, daemon=True)
        t.start()

    def _do_enrich(self, d: DeviceInfo):
        """Enrich device info - runs in background thread"""
        # Batch all prop queries into one call for speed
        props_to_get = [
            "ro.product.brand", "ro.product.model", "ro.product.device",
            "ro.build.version.release", "ro.build.version.sdk",
            "ro.build.version.security_patch", "ro.build.display.id",
            "ro.build.fingerprint", "ro.build.product",
            "ro.hardware", "ro.hardware.chipname", "ro.board.platform",
            "ro.bootloader", "gsm.version.baseband",
            "ro.boot.flash.locked", "ro.boot.verifiedbootstate",
            "ro.serialno", "ro.crypto.state",
            "persist.sys.usb.config", "sys.usb.config",
        ]
        prop_cmd = "; ".join(f"getprop {p}" for p in props_to_get)
        prop_out = self.shell(prop_cmd, d.serial, timeout=8)
        props = {}
        if prop_out:
            lines = prop_out.splitlines()
            for i, line in enumerate(lines):
                if i < len(props_to_get) and line.strip():
                    props[props_to_get[i]] = line.strip()

        # Map props
        d.brand = props.get("ro.product.brand", d.brand)
        d.model = props.get("ro.product.model", d.model)
        d.device_name = props.get("ro.product.device", d.device_name)
        d.android_version = props.get("ro.build.version.release", d.android_version)
        d.sdk_version = props.get("ro.build.version.sdk", d.sdk_version)
        d.security_patch = props.get("ro.build.version.security_patch", d.security_patch)
        d.build_number = props.get("ro.build.display.id", d.build_number)
        d.build_fingerprint = props.get("ro.build.fingerprint", d.build_fingerprint)
        d.product = props.get("ro.build.product", d.product)
        d.hardware = props.get("ro.hardware", d.hardware)
        d.bootloader_ver = props.get("ro.bootloader", d.bootloader_ver)
        d.baseband = props.get("gsm.version.baseband", d.baseband)
        d.serial_number = props.get("ro.serialno", d.serial_number)
        d.encryption_state = props.get("ro.crypto.state", d.encryption_state)
        d.usb_config = props.get("persist.sys.usb.config", props.get("sys.usb.config", d.usb_config))
        d.chipset = props.get("ro.hardware.chipname", props.get("ro.board.platform", props.get("ro.hardware", "?")))

        # Bootloader unlock
        lock = props.get("ro.boot.flash.locked", "")
        if lock in ("0", "false"):
            d.bootloader_unlocked = True
        elif lock in ("1", "true"):
            d.bootloader_unlocked = False
        else:
            vb = props.get("ro.boot.verifiedbootstate", "")
            d.bootloader_unlocked = vb == "orange"

        # Battery + RAM + Kernel (batch)
        try:
            batch_cmd = "dumpsys battery | grep -E 'level:|status:|health:|temperature:' && echo ---MEM--- && cat /proc/meminfo | head -1 && echo ---UNAME--- && uname -r && echo ---UPTIME--- && cat /proc/uptime && echo ---SELINUX--- && getenforce"
            batch_out = self.shell(batch_cmd, d.serial, timeout=8)
            if batch_out:
                for line in batch_out.splitlines():
                    line = line.strip()
                    if line.startswith("level:"):
                        d.battery_level = line.split(":")[1].strip() + "%"
                    elif line.startswith("status:"):
                        s = {1: "?", 2: "Charging", 3: "Dschg", 4: "NotChg", 5: "Full"}
                        try:
                            d.battery_status = s.get(int(line.split(":")[1].strip()), "?")
                        except:
                            pass
                    elif line.startswith("health:"):
                        h = {1: "?", 2: "Good", 3: "Hot", 4: "Dead", 5: "OV", 6: "Fail", 7: "Cold"}
                        try:
                            d.battery_health = h.get(int(line.split(":")[1].strip()), "?")
                        except:
                            pass
                    elif line.startswith("temperature:"):
                        try:
                            t = int(line.split(":")[1].strip()) / 10
                            d.battery_temp = f"{t:.0f}°C"
                        except:
                            pass
                    elif line.startswith("MemTotal:"):
                        m = re.search(r"(\d+)", line)
                        if m:
                            gb = int(m.group(1)) / 1048576
                            d.total_ram = f"{gb:.1f}GB"
                    elif line == "---UNAME---":
                        d.kernel_version = ""
                    elif d.kernel_version == "" and not line.startswith("---") and "---" not in line:
                        d.kernel_version = line.strip()
                    elif line.startswith("---UPTIME---"):
                        d.uptime = ""
                    elif d.uptime == "" and not line.startswith("---") and "---" not in line:
                        try:
                            secs = float(line.split()[0])
                            h = int(secs // 3600)
                            m_ = int((secs % 3600) // 60)
                            d.uptime = f"{h}h{m_}m"
                        except:
                            d.uptime = line[:20]
                    elif line == "---SELINUX---":
                        d.selinux_mode = ""
                    elif d.selinux_mode == "" and not line.startswith("---") and "---" not in line:
                        d.selinux_mode = line.strip()
        except:
            pass

        # Screen info (one call)
        try:
            wm = self.shell("wm size && wm density", d.serial, timeout=5)
            for line in wm.splitlines():
                if "size" in line.lower() and "Physical" in line:
                    m = re.search(r"(\d+x\d+)", line)
                    if m:
                        d.screen_resolution = m.group(1)
                if "density" in line.lower() and "Physical" in line:
                    m = re.search(r"(\d+)", line)
                    if m:
                        d.screen_density = m.group(1) + "dpi"
        except:
            pass

        # Storage (one call)
        try:
            df = self.shell("df -h /data 2>/dev/null | tail -1", d.serial, timeout=5)
            parts = df.split()
            if len(parts) >= 5:
                d.available_storage = f"{parts[3]} free / {parts[1]}"
        except:
            pass

        # Root + Magisk + TWRP (one call)
        try:
            chk = self.shell("su -c 'id 2>/dev/null; magisk -v 2>/dev/null; ls /twrp 2>/dev/null; ls /cache/recovery/last_twrp 2>/dev/null'", d.serial, timeout=5)
            d.root_access = "uid=0" in chk
            d.magisk_installed = bool(re.search(r"magisk", chk, re.I))
            d.twrp_installed = "twrp" in chk.lower() or "last_twrp" in chk
        except:
            pass

        # IP + WiFi (one call)
        try:
            net = self.shell("ifconfig wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d: -f2; echo ---SSID---; dumpsys wifi 2>/dev/null | grep -oP 'SSID: \"\\K[^\"]*' | head -1", d.serial, timeout=5)
            for line in net.splitlines():
                if line.startswith("---SSID---"):
                    d.wifi_ssid = ""
                elif d.wifi_ssid == "" and line.strip() and not line.startswith("---"):
                    d.wifi_ssid = line.strip()
                elif not line.startswith("---") and re.match(r"\d+\.\d+", line):
                    d.ip_address = line.strip()
        except:
            pass

        # Emulator check
        d.is_emulator = "emulator" in d.build_fingerprint.lower() or d.hardware in ("goldfish", "ranchu", "vbox86")

        d.enriched = True

    # ─── CACHE CONTROL ───

    def invalidate_cache(self, serial: str = None):
        """Clear cache for a device or all devices"""
        if serial:
            self._cache._lock.acquire()
            self._cache._cache.pop(serial, None)
            self._cache._lock.release()
        else:
            self._cache.clear()

    # ─── OPERATIONS ───

    def push(self, local: str, remote: str, device: str = None) -> str:
        rc, out, err = self.adb(["push", local, remote], device, timeout=300)
        return out.strip() if rc == 0 else f"Error: {err}"

    def pull(self, remote: str, local: str, device: str = None) -> str:
        rc, out, err = self.adb(["pull", remote, local], device, timeout=300)
        return out.strip() if rc == 0 else f"Error: {err}"

    def install(self, apk: str, device: str = None) -> str:
        rc, out, err = self.adb(["install", "-r", "-g", apk], device, timeout=180)
        return "Install OK" if "Success" in out else f"Error: {err or out}"

    def uninstall(self, package: str, device: str = None) -> str:
        rc, out, err = self.adb(["uninstall", package], device, timeout=60)
        return "Uninstall OK" if "Success" in out else f"Error: {err or out}"

    def reboot(self, mode: str = "", device: str = None) -> str:
        args = ["reboot"] + ([mode] if mode else [])
        rc, _, err = self.adb(args, device, timeout=10)
        return f"Rebooting to {mode or 'system'}..." if rc == 0 else err

    # ─── PACKAGES ───

    def get_packages(self, device: str = None, system_only=False, third_only=False) -> list:
        args = ["shell", "pm", "list", "packages"]
        if system_only:
            args.append("-s")
        if third_only:
            args.append("-3")
        rc, out, _ = self.adb(args, device, timeout=20)
        pkgs = []
        for line in out.splitlines():
            m = re.match(r"package:(.+)", line.strip())
            if m:
                pkgs.append({"name": m.group(1)})
        return pkgs

    def get_package_info(self, package: str, device: str = None) -> dict:
        rc, out, _ = self.adb(["shell", "dumpsys", "package", package], device, timeout=15)
        info = {"package": package}
        v = re.search(r"versionName=([\w\.]+)", out)
        if v:
            info["version"] = v.group(1)
        vc = re.search(r"versionCode=(\d+)", out)
        if vc:
            info["versionCode"] = vc.group(1)
        return info

    def clear_app_data(self, package: str, device: str = None) -> str:
        rc, out, err = self.adb(["shell", "pm", "clear", package], device, timeout=15)
        return out.strip() if rc == 0 else f"Error: {err}"

    def force_stop(self, package: str, device: str = None) -> str:
        rc, out, err = self.adb(["shell", "am", "force-stop", package], device)
        return f"Force stopped {package}" if rc == 0 else f"Error: {err}"

    def disable_app(self, package: str, device: str = None) -> str:
        rc, out, err = self.adb(["shell", "pm", "disable-user", "--user", "0", package], device)
        return f"Disabled {package}" if rc == 0 else f"Error: {err}"

    def enable_app(self, package: str, device: str = None) -> str:
        rc, out, err = self.adb(["shell", "pm", "enable", package], device)
        return f"Enabled {package}" if rc == 0 else f"Error: {err}"

    def backup_app(self, pkg: str, out_dir: str, device: str = None) -> str:
        os.makedirs(out_dir, exist_ok=True)
        rc, out, _ = self.adb(["shell", "pm", "path", pkg], device)
        apk_path = out.strip().replace("package:", "")
        if apk_path:
            self.pull(apk_path, os.path.join(out_dir, f"{pkg}.apk"), device)
        bf = os.path.join(out_dir, f"{pkg}.ab")
        self.adb(["backup", "-f", bf, "-apk", "-shared", pkg], device, timeout=300)
        return f"Backup -> {out_dir}"

    # ─── FILE OPS ───

    def list_files(self, path: str, device: str = None) -> str:
        return self.shell(f"ls -la '{path}'", device)

    def delete_file(self, path: str, device: str = None) -> str:
        return self.root_shell(f"rm -rf '{path}'", device)

    def make_dir(self, path: str, device: str = None) -> str:
        return self.shell(f"mkdir -p '{path}'", device)

    def search_files(self, directory: str, pattern: str, device: str = None) -> str:
        return self.shell(f"find '{directory}' -name '{pattern}' -type f 2>/dev/null", device, timeout=30)

    # ─── SCREEN ───

    def screenshot(self, output_path: str, device: str = None) -> str:
        remote = "/sdcard/sc.png"
        self.adb(["shell", "screencap", "-p", remote], device)
        self.pull(remote, output_path, device)
        self.shell(f"rm -f {remote}", device)
        return f"Screenshot: {output_path}"

    def screenrecord(self, output_path: str, duration: int = 10, device: str = None) -> str:
        remote = "/sdcard/sr.mp4"
        self.adb(["shell", "screenrecord", "--time-limit", str(duration), remote], device, timeout=duration + 15)
        self.pull(remote, output_path, device)
        self.shell(f"rm -f {remote}", device)
        return f"Recording: {output_path}"

    def tap(self, x: int, y: int, device: str = None) -> str:
        return self.shell(f"input tap {x} {y}", device)

    def swipe(self, x1, y1, x2, y2, duration=300, device: str = None) -> str:
        return self.shell(f"input swipe {x1} {y1} {x2} {y2} {duration}", device)

    def long_press(self, x, y, duration=1000, device: str = None) -> str:
        return self.shell(f"input swipe {x} {y} {x} {y} {duration}", device)

    def input_text(self, text: str, device: str = None) -> str:
        return self.shell(f"input text '{text.replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'", device)

    def input_key(self, keycode: str, device: str = None) -> str:
        return self.shell(f"input keyevent {keycode}", device)

    def dump_ui(self, output_path: str, device: str = None) -> str:
        remote = "/sdcard/ui.xml"
        rc, _, err = self.adb(["shell", "uiautomator", "dump", remote], device, timeout=15)
        if rc == 0:
            self.pull(remote, output_path, device)
            return f"UI dump: {output_path}"
        return f"Error: {err}"

    def wake_screen(self, device: str = None) -> str:
        return self.shell("input keyevent KEYCODE_WAKEUP", device)

    # ─── NETWORK ───

    def connect_wifi(self, ip: str, port: int = 5555, device: str = None) -> str:
        self.adb(["tcpip", str(port)], device, timeout=10)
        time.sleep(2)
        rc, out, err = self.adb(["connect", f"{ip}:{port}"], timeout=15)
        return out.strip() or f"Error: {err}" if rc != 0 else "Connected!"

    def disconnect_all(self) -> str:
        rc, out, _ = self.adb(["disconnect"], timeout=10)
        return out.strip() or "Disconnected"

    def forward_port(self, local: str, remote: str, device: str = None) -> str:
        rc, out, err = self.adb(["forward", local, remote], device)
        return f"Forward {local}->{remote}" if rc == 0 else f"Error: {err}"

    def reverse_forward(self, remote: str, local: str, device: str = None) -> str:
        rc, out, err = self.adb(["reverse", remote, local], device)
        return f"Reverse {remote}->{local}" if rc == 0 else f"Error: {err}"

    def list_forwards(self, device: str = None) -> str:
        rc, out, _ = self.adb(["forward", "--list"], device)
        return out.strip() or "None"

    def list_reverse(self, device: str = None) -> str:
        rc, out, _ = self.adb(["reverse", "--list"], device)
        return out.strip() or "None"

    def set_proxy(self, proxy: str, device: str = None) -> str:
        return self.shell(f"settings put global http_proxy {proxy}", device)

    def remove_proxy(self, device: str = None) -> str:
        return self.shell("settings put global http_proxy :0", device)

    def bt_pair(self, addr: str, device: str = None) -> str:
        rc, out, err = self.adb(["pair", addr], device, timeout=30)
        return out.strip() if rc == 0 else f"Error: {err}"

    def bt_connect(self, addr: str, device: str = None) -> str:
        rc, out, err = self.adb(["connect", addr], device, timeout=30)
        return out.strip() if rc == 0 else f"Error: {err}"

    # ─── DIAGNOSTICS ───

    def get_logcat(self, device: str = None, lines: int = 500, filters: str = None) -> str:
        args = ["logcat", "-d", "-t", str(lines)]
        if filters:
            args += ["-s", filters]
        rc, out, _ = self.adb(args, device, timeout=20)
        return out

    def clear_logcat(self, device: str = None) -> str:
        self.adb(["logcat", "-c"], device)
        return "Cleared"

    def get_dmesg(self, device: str = None) -> str:
        return self.root_shell("dmesg", device, timeout=15)

    def get_processes(self, device: str = None) -> str:
        return self.shell("ps -A 2>/dev/null || ps", device, timeout=10)

    def get_battery(self, device: str = None) -> str:
        return self.shell("dumpsys battery", device)

    def get_memory(self, device: str = None) -> str:
        return self.shell("cat /proc/meminfo", device)

    def get_cpu(self, device: str = None) -> str:
        return self.shell("cat /proc/cpuinfo", device)

    def get_thermal(self, device: str = None) -> str:
        return self.shell("for tz in /sys/class/thermal/thermal_zone*/type; do t=${tz%/type}; echo \"$(<$t/type 2>/dev/null): $(<$t/temp 2>/dev/null)\"; done", device, timeout=10)

    def get_disk(self, device: str = None) -> str:
        return self.shell("df -h", device)

    def get_mounts(self, device: str = None) -> str:
        return self.shell("mount", device)

    def get_kernel(self, device: str = None) -> str:
        return self.shell("uname -a", device)

    def get_partitions(self, device: str = None) -> str:
        return self.root_shell("cat /proc/partitions", device)

    def get_partition_list(self, device: str = None) -> str:
        return self.shell("ls -la /dev/block/by-name/ 2>/dev/null || ls /dev/block/platform/*/by-name/ 2>/dev/null", device)

    def get_services(self, device: str = None) -> str:
        return self.shell("dumpsys activity services | head -60", device)

    def get_current_app(self, device: str = None) -> str:
        out = self.shell("dumpsys activity activities | grep mResumedActivity", device)
        m = re.search(r"u0\s+([\w\.]+)/([\w\.]+)", out)
        return f"{m.group(1)}/{m.group(2)}" if m else out.strip()

    # ─── ROOT / SELINUX ───

    def get_selinux(self, device: str = None) -> str:
        return self.shell("getenforce", device)

    def set_selinux(self, mode: str, device: str = None) -> str:
        return self.root_shell(f"setenforce {1 if mode == 'enforcing' else 0}", device)

    def remount(self, device: str = None) -> str:
        rc, out, err = self.adb(["remount"], device, timeout=15)
        return out.strip() if rc == 0 else f"Error: {err}"

    def disable_verity(self, device: str = None) -> str:
        rc, out, err = self.adb(["disable-verity"], device, timeout=30)
        return out.strip() if rc == 0 else f"Error: {err}"

    def enable_verity(self, device: str = None) -> str:
        rc, out, err = self.adb(["enable-verity"], device, timeout=30)
        return out.strip() if rc == 0 else f"Error: {err}"

    # ─── FASTBOOT ───

    def fb_flash(self, part: str, img: str, device: str = None) -> str:
        rc, out, err = self.fb(["flash", part, img], device, timeout=300)
        return f"Flashed {part}" if rc == 0 else f"Error: {err or out}"

    def fb_erase(self, part: str, device: str = None) -> str:
        rc, out, err = self.fb(["erase", part], device, timeout=120)
        return f"Erased {part}" if rc == 0 else f"Error: {err or out}"

    def fb_format(self, part: str, device: str = None) -> str:
        rc, out, err = self.fb(["format", part], device, timeout=120)
        return f"Formatted {part}" if rc == 0 else f"Error: {err or out}"

    def fb_boot(self, img: str, device: str = None) -> str:
        rc, out, err = self.fb(["boot", img], device, timeout=120)
        return f"Booting {img}" if rc == 0 else f"Error: {err or out}"

    def fb_update(self, zf: str, device: str = None) -> str:
        rc, out, err = self.fb(["update", zf], device, timeout=600)
        return "Update OK" if rc == 0 else f"Error: {err or out}"

    def fb_getvar(self, var: str = "all", device: str = None) -> str:
        rc, out, err = self.fb(["getvar", var], device, timeout=15)
        return out.strip() if rc == 0 else f"Error: {err}"

    def fb_oem_unlock(self, device: str = None) -> str:
        rc, out, err = self.fb(["oem", "unlock"], device, timeout=60)
        return "Unlock sent!" if rc == 0 else f"Error: {err or out}"

    def fb_oem_lock(self, device: str = None) -> str:
        rc, out, err = self.fb(["oem", "lock"], device, timeout=60)
        return "Lock sent" if rc == 0 else f"Error: {err or out}"

    def fb_flashing_unlock(self, device: str = None) -> str:
        rc, out, err = self.fb(["flashing", "unlock"], device, timeout=60)
        return "Unlock sent!" if rc == 0 else f"Error: {err or out}"

    def fb_flashing_lock(self, device: str = None) -> str:
        rc, out, err = self.fb(["flashing", "lock"], device, timeout=60)
        return "Lock sent" if rc == 0 else f"Error: {err or out}"

    def fb_edl(self, device: str = None) -> str:
        rc, out, err = self.fb(["oem", "edl"], device, timeout=15)
        if rc == 0:
            return "EDL mode..."
        rc, out, err = self.fb(["oem", "enter-dload"], device, timeout=15)
        return "EDL mode..." if rc == 0 else f"Error: {err}"

    def fb_active_slot(self, slot: str = None, device: str = None) -> str:
        if slot:
            rc, out, err = self.fb(["set-active", slot], device, timeout=30)
        else:
            rc, out, err = self.fb(["getvar", "current-slot"], device, timeout=15)
        return out.strip() if rc == 0 else f"Error: {err}"

    def fb_reboot(self, target: str = "", device: str = None) -> str:
        args = ["reboot"] + ([target] if target else [])
        rc, _, err = self.fb(args, device, timeout=30)
        return f"Rebooting to {target or 'system'}..." if rc == 0 else f"Error: {err}"

    # ─── SIDELOAD / RECOVERY ───

    def sideload(self, zf: str, device: str = None) -> str:
        rc, out, err = self.adb(["sideload", zf], device, timeout=600)
        return "Sideload OK" if rc == 0 else f"Error: {err or out}"

    def wipe_data(self, device: str = None) -> str:
        return self.shell("recovery --wipe_data", device, timeout=60)

    def wipe_cache(self, device: str = None) -> str:
        return self.root_shell("rm -rf /cache/*", device)

    # ─── LOCK BYPASS ───

    def bypass_swipe(self, device: str = None) -> str:
        self.swipe(540, 1900, 540, 900, 300, device)
        time.sleep(0.3)
        return "Swipe attempted"

    def bypass_null_pin(self, device: str = None) -> str:
        self.input_text("0000", device)
        time.sleep(0.3)
        self.input_key("66", device)
        return "Null PIN sent"

    def bypass_settings(self, device: str = None) -> str:
        self.adb(["shell", "am", "start", "-n", "com.android.settings/.Settings"], device)
        return "Settings launched"

    def bypass_delete_keys(self, device: str = None) -> str:
        res = []
        for f in ["/data/system/gesture.key", "/data/system/password.key",
                   "/data/system/locksettings.db", "/data/system/locksettings.db-wal",
                   "/data/system/locksettings.db-shm"]:
            res.append(self.root_shell(f"rm -f {f}", device))
        return "\n".join(res)

    def bypass_frp(self, device: str = None) -> str:
        res = []
        res.append(self.root_shell("rm -rf /data/system/users/0/accounts_ce.db", device))
        res.append(self.root_shell("rm -rf /data/system/users/0/accounts_de.db", device))
        res.append(self.shell("am broadcast -a android.intent.action.MASTER_CLEAR", device))
        return "\n".join(res)

    # ─── SETTINGS ───

    def settings_list(self, namespace: str, device: str = None) -> str:
        return self.shell(f"settings list {namespace}", device, timeout=15)

    def get_device_props(self, device: str = None) -> dict:
        rc, out, _ = self.adb(["shell", "getprop"], device, timeout=15)
        props = {}
        for line in out.splitlines():
            m = re.match(r"\[(.+?)\]:\s*\[(.*?)\]", line)
            if m:
                props[m.group(1)] = m.group(2)
        return props

    def set_prop(self, prop: str, value: str, device: str = None) -> str:
        return self.root_shell(f"setprop {prop} {value}", device)

    # ─── DEV OPTIONS ───

    def enable_dev_options(self, device: str = None) -> str:
        return self.shell("settings put global development_settings_enabled 1", device)

    def enable_stay_awake(self, device: str = None) -> str:
        return self.shell("settings put global stay_on_while_plugged_in 3", device)

    def set_animation_scale(self, scale: float, device: str = None) -> str:
        r = []
        for k in ["window_animation_scale", "transition_animation_scale", "animator_duration_scale"]:
            r.append(self.shell(f"settings put global {k} {scale}", device))
        return "\n".join(r)

    def enable_show_touches(self, device: str = None) -> str:
        return self.shell("settings put system show_touches 1", device)

    def enable_pointer(self, device: str = None) -> str:
        return self.shell("settings put system pointer_location 1", device)

    def enable_mock_location(self, device: str = None) -> str:
        return self.shell("settings put global mock_location 1", device)

    def set_dpi(self, dpi: int, device: str = None) -> str:
        return self.shell(f"wm density {dpi}", device)

    def reset_dpi(self, device: str = None) -> str:
        return self.shell("wm density reset", device)

    def set_resolution(self, w: int, h: int, device: str = None) -> str:
        return self.shell(f"wm size {w}x{h}", device)

    def reset_resolution(self, device: str = None) -> str:
        return self.shell("wm size reset", device)

    # ─── MISC ───

    def monkey(self, pkg: str = None, events: int = 5000, device: str = None) -> str:
        args = ["shell", "monkey"]
        if pkg:
            args += ["-p", pkg]
        args += ["--throttle", "100", "--ignore-crashes", "--ignore-timeouts", "-v", str(events)]
        rc, out, err = self.adb(args, device, timeout=events + 60)
        return out or err

    def open_app(self, pkg: str, device: str = None) -> str:
        return self.shell(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1", device)

    def open_url(self, url: str, device: str = None) -> str:
        return self.shell(f"am start -a android.intent.action.VIEW -d '{url}'", device)

    def list_users(self, device: str = None) -> str:
        return self.shell("pm list users", device)

    def list_accounts(self, device: str = None) -> str:
        return self.shell("pm list accounts", device)

    def media_scan(self, path: str, device: str = None) -> str:
        return self.shell(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{path}", device)

    def kill_process(self, pid: str, device: str = None) -> str:
        return self.root_shell(f"kill {pid}", device)

    def get_screen_state(self, device: str = None) -> str:
        return self.shell("dumpsys power | grep 'Display Power'", device)


def detect_adb_path() -> str:
    try:
        core = ADBCore.__new__(ADBCore)
        core._adb_path = None
        core._detect_adb()
        return core._adb_path or "adb"
    except:
        return "adb"


if __name__ == "__main__":
    print("ADB Expert Core v3.5 - Self Test")
    core = ADBCore()
    print(f"ADB: {core.adb_path}")
    print(f"Fastboot: {core.fastboot_path}")
    devices = core.get_devices()
    print(f"Devices: {len(devices)}")
    for d in devices:
        print(f"  [{d.status}] {d.serial}")
    fb = core.get_fastboot_devices()
    print(f"Fastboot devices: {len(fb)}")
    print("OK")
