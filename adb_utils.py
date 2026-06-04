"""
ADB Expert Utilities - Core ADB wrapper and device management
Author: ADB Expert Tool
"""

import subprocess
import re
import os
import time
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from threading import Thread


@dataclass
class DeviceInfo:
    serial: str
    status: str
    model: str = "Unknown"
    brand: str = "Unknown"
    android_version: str = "Unknown"
    sdk_version: str = "Unknown"
    product: str = "Unknown"
    bootloader_unlocked: bool = False
    root_access: bool = False
    battery_level: str = "Unknown"
    imei: str = "Unknown"
    

class ADBError(Exception):
    pass


class ADBCore:
    def __init__(self, adb_path: str = "adb"):
        self.adb_path = adb_path
        self.fastboot_path = "fastboot"
        self._ensure_adb()
    
    def _ensure_adb(self):
        """Verify adb is accessible"""
        try:
            self.run_adb_command(["version"])
        except FileNotFoundError:
            # Try common paths
            common_paths = [
                r"C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe",
                r"C:\Program Files\Android\android-sdk\platform-tools\adb.exe",
                r"C:\Users\Dil\AppData\Local\Android\Sdk\platform-tools\adb.exe",
                r".\platform-tools\adb.exe",
            ]
            for path in common_paths:
                if os.path.exists(path):
                    self.adb_path = path
                    self.fastboot_path = path.replace("adb.exe", "fastboot.exe")
                    return
            raise ADBError("ADB not found. Please install Android Platform Tools.")
    
    def run_adb_command(self, args: List[str], device: str = None, timeout: int = 30) -> Tuple[int, str, str]:
        """Run an ADB command and return (returncode, stdout, stderr)"""
        cmd = [self.adb_path]
        if device:
            cmd.extend(["-s", device])
        cmd.extend(args)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='ignore')
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            raise ADBError(f"Command timed out: {' '.join(cmd)}")
    
    def run_fastboot_command(self, args: List[str], device: str = None, timeout: int = 60) -> Tuple[int, str, str]:
        """Run a fastboot command"""
        cmd = [self.fastboot_path]
        if device:
            cmd.extend(["-s", device])
        cmd.extend(args)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='ignore')
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            raise ADBError(f"Fastboot command timed out: {' '.join(cmd)}")
    
    def get_devices(self) -> List[DeviceInfo]:
        """Get list of connected ADB devices"""
        rc, stdout, _ = self.run_adb_command(["devices", "-l"])
        devices = []
        
        if rc != 0:
            return devices
            
        for line in stdout.splitlines()[1:]:  # Skip header
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                status = parts[1]
                
                # Parse additional info
                model = self._parse_device_info(parts, "model")
                product = self._parse_device_info(parts, "product")
                
                devices.append(DeviceInfo(
                    serial=serial,
                    status=status,
                    model=model,
                    product=product
                ))
        
        # Enrich device info
        for device in devices:
            if device.status == "device":
                self._enrich_device_info(device)
        
        return devices
    
    def _parse_device_info(self, parts: List[str], key: str) -> str:
        for part in parts:
            if part.startswith(f"{key}:"):
                return part.split(":", 1)[1]
        return "Unknown"
    
    def _enrich_device_info(self, device: DeviceInfo):
        """Get detailed info for a device"""
        # Brand
        _, out, _ = self.run_adb_command(["shell", "getprop", "ro.product.brand"], device.serial)
        if out.strip():
            device.brand = out.strip()
        
        # Android version
        _, out, _ = self.run_adb_command(["shell", "getprop", "ro.build.version.release"], device.serial)
        if out.strip():
            device.android_version = out.strip()
        
        # SDK
        _, out, _ = self.run_adb_command(["shell", "getprop", "ro.build.version.sdk"], device.serial)
        if out.strip():
            device.sdk_version = out.strip()
        
        # Battery
        _, out, _ = self.run_adb_command(["shell", "dumpsys", "battery"], device.serial)
        level_match = re.search(r"level: (\d+)", out)
        if level_match:
            device.battery_level = level_match.group(1) + "%"
        
        # IMEI (requires root or special permissions)
        _, out, _ = self.run_adb_command(["shell", "service", "call", "iphonesubinfo", "1"], device.serial)
        if out.strip() and " Parcel" in out:
            imei_parts = re.findall(r"'([0-9\.]+)'", out)
            if imei_parts:
                device.imei = "".join(imei_parts).replace(".", "")
        
        # Root check
        _, out, _ = self.run_adb_command(["shell", "su", "-c", "id"], device.serial)
        device.root_access = "uid=0" in out
        
        # Bootloader unlock status
        _, out, _ = self.run_adb_command(["shell", "getprop", "ro.boot.flash.locked"], device.serial)
        if "0" in out or "false" in out.lower():
            device.bootloader_unlocked = True
        elif "1" in out or "true" in out.lower():
            device.bootloader_unlocked = False
    
    def get_fastboot_devices(self) -> List[Dict]:
        """Get devices in fastboot mode"""
        rc, stdout, _ = self.run_fastboot_command(["devices"])
        devices = []
        for line in stdout.splitlines():
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    devices.append({
                        "serial": parts[0],
                        "status": parts[1]
                    })
        return devices
    
    def shell(self, command: str, device: str = None) -> str:
        """Execute shell command on device"""
        rc, out, err = self.run_adb_command(["shell", command], device)
        if rc != 0:
            return f"Error: {err}"
        return out
    
    def root_shell(self, command: str, device: str = None) -> str:
        """Execute root shell command"""
        rc, out, err = self.run_adb_command(["shell", "su", "-c", command], device)
        if rc != 0:
            return f"Error (Root required): {err}"
        return out
    
    def push(self, local: str, remote: str, device: str = None) -> str:
        rc, out, err = self.run_adb_command(["push", local, remote], device)
        if rc != 0:
            return f"Error: {err}"
        return out or "Push successful"
    
    def pull(self, remote: str, local: str, device: str = None) -> str:
        rc, out, err = self.run_adb_command(["pull", remote, local], device)
        if rc != 0:
            return f"Error: {err}"
        return out or "Pull successful"
    
    def install(self, apk_path: str, device: str = None, reinstall: bool = False, downgrade: bool = False) -> str:
        args = ["install"]
        if reinstall:
            args.append("-r")
        if downgrade:
            args.append("-d")
        args.append(apk_path)
        
        rc, out, err = self.run_adb_command(args, device, timeout=120)
        if "Success" in out:
            return "Installation successful"
        return f"Error: {err or out}"
    
    def uninstall(self, package: str, device: str = None, keep_data: bool = False) -> str:
        args = ["uninstall"]
        if keep_data:
            args.append("-k")
        args.append(package)
        
        rc, out, err = self.run_adb_command(args, device)
        if "Success" in out:
            return "Uninstallation successful"
        return f"Error: {err or out}"
    
    def reboot(self, mode: str = "", device: str = None) -> str:
        args = ["reboot"]
        if mode:
            args.append(mode)
        rc, _, err = self.run_adb_command(args, device)
        if rc != 0:
            return f"Error: {err}"
        return f"Rebooting to {mode or 'system'}..."
    
    def reboot_fastboot(self, device: str = None) -> str:
        rc, _, err = self.run_adb_command(["reboot", "bootloader"], device)
        if rc != 0:
            return f"Error: {err}"
        return "Rebooting to bootloader..."
    
    def get_packages(self, device: str = None, system_only: bool = False, third_party_only: bool = False) -> List[Dict]:
        """Get installed packages"""
        args = ["shell", "pm", "list", "packages"]
        if system_only:
            args.append("-s")
        if third_party_only:
            args.append("-3")
        
        rc, out, _ = self.run_adb_command(args, device)
        packages = []
        for line in out.splitlines():
            match = re.match(r"package:(.+)", line.strip())
            if match:
                pkg_name = match.group(1)
                packages.append({"name": pkg_name})
        return packages
    
    def get_app_info(self, package: str, device: str = None) -> Dict:
        """Get detailed app information"""
        rc, out, _ = self.run_adb_command(["shell", "dumpsys", "package", package], device)
        info = {"package": package}
        
        # Parse version
        ver_match = re.search(r"versionName=([\w\.]+)", out)
        if ver_match:
            info["version"] = ver_match.group(1)
        
        # Parse permissions
        perms = re.findall(r"android\.permission\.\w+", out)
        info["permissions"] = list(set(perms))
        
        # Parse activities
        activities = re.findall(r"([\w\.]+)/([\w\.]+)", out)
        info["activities"] = [f"{a[0]}/{a[1]}" for a in activities[:5]]
        
        return info
    
    def clear_app_data(self, package: str, device: str = None) -> str:
        rc, out, err = self.run_adb_command(["shell", "pm", "clear", package], device)
        return out or err
    
    def backup_app(self, package: str, output_path: str, device: str = None) -> str:
        """Backup app APK and data"""
        # Get APK path
        rc, out, _ = self.run_adb_command(["shell", "pm", "path", package], device)
        apk_path = out.strip().replace("package:", "")
        
        if apk_path:
            # Create backup directory
            os.makedirs(output_path, exist_ok=True)
            self.pull(apk_path, os.path.join(output_path, f"{package}.apk"), device)
        
        # Full backup using adb backup (for Android < 12)
        backup_file = os.path.join(output_path, f"{package}.ab")
        rc, out, err = self.run_adb_command(["backup", "-f", backup_file, "-apk", package], device, timeout=300)
        return f"Backup saved to {output_path}"
    
    def get_device_props(self, device: str = None) -> Dict[str, str]:
        """Get all device properties (build.prop)"""
        rc, out, _ = self.run_adb_command(["shell", "getprop"], device)
        props = {}
        for line in out.splitlines():
            match = re.match(r"\[(.+)\]: \[(.*)\]", line)
            if match:
                props[match.group(1)] = match.group(2)
        return props
    
    def get_partitions(self, device: str = None) -> List[Dict]:
        """Get partition information (requires root)"""
        rc, out, _ = self.run_adb_command(["shell", "su", "-c", "cat /proc/partitions"], device)
        partitions = []
        for line in out.splitlines()[2:]:  # Skip headers
            parts = line.strip().split()
            if len(parts) >= 4:
                partitions.append({
                    "major": parts[0],
                    "minor": parts[1],
                    "blocks": parts[2],
                    "name": parts[3]
                })
        return partitions
    
    def get_partition_info(self, device: str = None) -> List[Dict]:
        """Alternative partition info via df"""
        rc, out, _ = self.run_adb_command(["shell", "df", "-h"], device)
        partitions = []
        for line in out.splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 6:
                partitions.append({
                    "filesystem": parts[0],
                    "size": parts[1],
                    "used": parts[2],
                    "available": parts[3],
                    "use_percent": parts[4],
                    "mount": parts[5]
                })
        return partitions
    
    def flash_partition(self, partition: str, image_file: str, device: str = None) -> str:
        """Flash a partition using fastboot (device must be in bootloader)"""
        rc, out, err = self.run_fastboot_command(["flash", partition, image_file], device, timeout=300)
        if rc != 0:
            return f"Flash Error: {err or out}"
        return f"Successfully flashed {partition}"
    
    def erase_partition(self, partition: str, device: str = None) -> str:
        """Erase a partition using fastboot"""
        rc, out, err = self.run_fastboot_command(["erase", partition], device, timeout=120)
        if rc != 0:
            return f"Erase Error: {err or out}"
        return f"Successfully erased {partition}"
    
    def oem_unlock(self, device: str = None) -> str:
        """Unlock bootloader"""
        rc, out, err = self.run_fastboot_command(["oem", "unlock"], device, timeout=60)
        if rc != 0:
            return f"Error: {err or out}"
        return "Bootloader unlock command sent. Check device screen for confirmation."
    
    def oem_lock(self, device: str = None) -> str:
        """Relock bootloader"""
        rc, out, err = self.run_fastboot_command(["oem", "lock"], device, timeout=60)
        if rc != 0:
            return f"Error: {err or out}"
        return "Bootloader relock command sent."
    
    def get_logcat(self, device: str = None, lines: int = 100, filter_expr: str = None) -> str:
        """Get logcat output"""
        args = ["logcat", "-d", "-t", str(lines)]
        if filter_expr:
            args.extend(["-s", filter_expr])
        rc, out, err = self.run_adb_command(args, device)
        return out
    
    def clear_logcat(self, device: str = None) -> str:
        rc, out, err = self.run_adb_command(["logcat", "-c"], device)
        return "Logcat cleared"
    
    def screenshot(self, output_path: str, device: str = None) -> str:
        """Capture screenshot"""
        remote_path = "/sdcard/screenshot.png"
        rc, _, err = self.run_adb_command(["shell", "screencap", "-p", remote_path], device)
        if rc != 0:
            return f"Error: {err}"
        self.pull(remote_path, output_path, device)
        return f"Screenshot saved to {output_path}"
    
    def screenrecord(self, output_path: str, duration: int = 10, device: str = None) -> str:
        """Record screen"""
        remote_path = "/sdcard/screenrecord.mp4"
        rc, out, err = self.run_adb_command(
            ["shell", "screenrecord", "--time-limit", str(duration), remote_path], 
            device, 
            timeout=duration + 10
        )
        self.pull(remote_path, output_path, device)
        return f"Screen recording saved to {output_path}"
    
    def connect_wireless(self, ip: str, port: int = 5555, device: str = None) -> str:
        """Connect to device wirelessly"""
        rc, out, err = self.run_adb_command(["tcpip", str(port)], device)
        time.sleep(1)
        rc, out, err = self.run_adb_command(["connect", f"{ip}:{port}"])
        if rc != 0:
            return f"Connection failed: {err or out}"
        return out or "Connected successfully"
    
    def disconnect_wireless(self, ip: str = None, port: int = 5555) -> str:
        if ip:
            rc, out, err = self.run_adb_command(["disconnect", f"{ip}:{port}"])
        else:
            rc, out, err = self.run_adb_command(["disconnect"])
        return out or "Disconnected"
    
    def forward_port(self, local: str, remote: str, device: str = None) -> str:
        rc, out, err = self.run_adb_command(["forward", local, remote], device)
        return out or f"Forwarded {local} -> {remote}"
    
    def list_forwards(self, device: str = None) -> str:
        rc, out, _ = self.run_adb_command(["forward", "--list"], device)
        return out or "No active forwards"
    
    def input_text(self, text: str, device: str = None) -> str:
        rc, out, err = self.run_adb_command(["shell", "input", "text", text], device)
        return out or "Text input sent"
    
    def input_key(self, keycode: str, device: str = None) -> str:
        rc, out, err = self.run_adb_command(["shell", "input", "keyevent", keycode], device)
        return out or f"Key {keycode} sent"
    
    def tap(self, x: int, y: int, device: str = None) -> str:
        rc, out, err = self.run_adb_command(["shell", "input", "tap", str(x), str(y)], device)
        return out or f"Tap at ({x}, {y}) sent"
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300, device: str = None) -> str:
        rc, out, err = self.run_adb_command(
            ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)], 
            device
        )
        return out or "Swipe sent"
    
    def dump_ui_hierarchy(self, output_path: str = None, device: str = None) -> str:
        """Dump UI hierarchy for automation"""
        remote_path = "/sdcard/window_dump.xml"
        rc, _, err = self.run_adb_command(["shell", "uiautomator", "dump", remote_path], device)
        if rc != 0:
            return f"Error: {err}"
        if output_path:
            self.pull(remote_path, output_path, device)
            return f"UI hierarchy saved to {output_path}"
        rc, out, _ = self.run_adb_command(["shell", "cat", remote_path], device)
        return out
    
    def get_battery_stats(self, device: str = None) -> Dict:
        rc, out, _ = self.run_adb_command(["shell", "dumpsys", "battery"], device)
        stats = {}
        for line in out.splitlines():
            if ":" in line:
                key, _, val = line.strip().partition(": ")
                stats[key] = val
        return stats
    
    def get_memory_info(self, device: str = None) -> Dict:
        rc, out, _ = self.run_adb_command(["shell", "cat", "/proc/meminfo"], device)
        info = {}
        for line in out.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                info[key.strip()] = val.strip()
        return info
    
    def get_cpu_info(self, device: str = None) -> Dict:
        rc, out, _ = self.run_adb_command(["shell", "cat", "/proc/cpuinfo"], device)
        info = {"processors": []}
        processor = {}
        for line in out.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                if key == "processor":
                    if processor:
                        info["processors"].append(processor)
                    processor = {}
                processor[key] = val
        if processor:
            info["processors"].append(processor)
        return info
    
    def get_thermal_zones(self, device: str = None) -> List[Dict]:
        """Get thermal zone temperatures (expert feature)"""
        rc, out, _ = self.run_adb_command(["shell", "cat", "/sys/class/thermal/thermal_zone*/type"], device)
        types = out.strip().splitlines()
        
        rc, out, _ = self.run_adb_command(["shell", "cat", "/sys/class/thermal/thermal_zone*/temp"], device)
        temps = out.strip().splitlines()
        
        zones = []
        for i, (t_type, temp) in enumerate(zip(types, temps)):
            zones.append({
                "zone": i,
                "type": t_type.strip(),
                "temp_celsius": int(temp.strip()) / 1000 if temp.strip().isdigit() else temp.strip()
            })
        return zones
    
    def monkey_test(self, package: str = None, events: int = 1000, device: str = None) -> str:
        """Run monkey stress test"""
        args = ["shell", "monkey"]
        if package:
            args.extend(["-p", package])
        args.extend(["--throttle", "100", "-v", str(events)])
        rc, out, err = self.run_adb_command(args, device, timeout=300)
        return out or err
    
    def get_dmesg(self, device: str = None) -> str:
        rc, out, _ = self.run_adb_command(["shell", "dmesg"], device)
        return out
    
    def get_processes(self, device: str = None) -> List[Dict]:
        rc, out, _ = self.run_adb_command(["shell", "ps"], device)
        processes = []
        for line in out.splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 9:
                processes.append({
                    "user": parts[0],
                    "pid": parts[1],
                    "ppid": parts[2],
                    "vsz": parts[3],
                    "rss": parts[4],
                    "wchan": parts[5],
                    "pc": parts[6],
                    "status": parts[7],
                    "name": parts[8]
                })
        return processes
    
    def kill_process(self, pid: str, device: str = None) -> str:
        rc, out, err = self.run_adb_command(["shell", "kill", pid], device)
        return out or f"Kill signal sent to PID {pid}"
    
    def wipe_data(self, device: str = None) -> str:
        """Factory reset via recovery commands (DANGEROUS)"""
        rc, out, err = self.run_adb_command(["shell", "recovery", "--wipe_data"], device)
        return out or "Wipe data command sent. Device will reset."
    
    def sideload(self, zip_file: str, device: str = None) -> str:
        """Sideload a zip file in recovery mode"""
        rc, out, err = self.run_adb_command(["sideload", zip_file], device, timeout=600)
        if rc != 0:
            return f"Sideload Error: {err or out}"
        return "Sideload completed successfully"
    
    def set_prop(self, prop: str, value: str, device: str = None) -> str:
        """Set a property (requires root)"""
        rc, out, err = self.run_adb_command(["shell", "su", "-c", f"setprop {prop} {value}"], device)
        return out or f"Property {prop} set to {value}"
    
    def remount_system(self, device: str = None) -> str:
        """Remount system as read-write (requires root)"""
        rc, out, err = self.run_adb_command(["remount"], device)
        if rc != 0:
            return f"Remount failed: {err or out}"
        return "System remounted as read-write"
    
    def disable_verity(self, device: str = None) -> str:
        """Disable dm-verity (requires root, expert)"""
        rc, out, err = self.run_adb_command(["disable-verity"], device)
        if rc != 0:
            return f"Error: {err or out}"
        return "Verity disabled. Reboot required."
    
    def enable_verity(self, device: str = None) -> str:
        rc, out, err = self.run_adb_command(["enable-verity"], device)
        if rc != 0:
            return f"Error: {err or out}"
        return "Verity enabled. Reboot required."
    
    def get_wifi_config(self, device: str = None) -> str:
        """Get WiFi configuration (requires root)"""
        rc, out, _ = self.run_adb_command(["shell", "su", "-c", "cat /data/misc/wifi/wpa_supplicant.conf"], device)
        return out
    
    def extract_db(self, db_path: str, output_path: str, device: str = None) -> str:
        """Extract SQLite database"""
        self.pull(db_path, output_path, device)
        return f"Database extracted to {output_path}"
    
    def bypass_lock(self, method: str, device: str = None) -> str:
        """
        Lock screen bypass methods for owned devices (educational/forensic)
        WARNING: Only for devices you own!
        """
        if method == "swipe":
            # Swipe gesture to unlock if no PIN
            self.swipe(300, 1000, 300, 300, device=device)
            return "Swipe unlock attempted"
        elif method == "crash":
            # Crash the lock screen (older Android versions)
            self.run_adb_command(["shell", "am", "start", "com.android.settings/.Settings"], device)
            return "Lock screen bypass attempted via settings crash"
        elif method == "null_pin":
            # Attempt null PIN on some devices
            self.input_text("0000", device)
            self.input_key("66", device)  # ENTER
            return "Null PIN attempt sent"
        return "Unknown method"
    
    def get_network_info(self, device: str = None) -> Dict:
        rc, out, _ = self.run_adb_command(["shell", "ifconfig"], device)
        interfaces = {}
        current_if = None
        for line in out.splitlines():
            if line and not line.startswith(" "):
                current_if = line.split()[0].rstrip(":")
                interfaces[current_if] = {"raw": line}
            elif current_if and line.strip():
                if "inet addr:" in line:
                    ip = re.search(r"inet addr:([\d\.]+)", line)
                    if ip:
                        interfaces[current_if]["ip"] = ip.group(1)
        return interfaces
    
    def set_proxy(self, proxy: str, device: str = None) -> str:
        rc, out, err = self.run_adb_command(["shell", "settings", "put", "global", "http_proxy", proxy], device)
        return out or f"Proxy set to {proxy}"
    
    def remove_proxy(self, device: str = None) -> str:
        rc, out, err = self.run_adb_command(["shell", "settings", "put", "global", "http_proxy", ":0"], device)
        return out or "Proxy removed"
    
    def inject_keystrokes(self, text: str, device: str = None) -> str:
        """Inject keystrokes for automation"""
        for char in text:
            if char == " ":
                char = "%s"
            elif char == "&":
                char = "&"
            self.input_text(char, device)
            time.sleep(0.05)
        return "Keystrokes injected"
    
    def run_async(self, args: List[str], device: str = None, callback=None):
        """Run ADB command asynchronously"""
        def runner():
            rc, out, err = self.run_adb_command(args, device)
            if callback:
                callback(rc, out, err)
        
        thread = Thread(target=runner)
        thread.daemon = True
        thread.start()
        return thread


def detect_adb_path() -> str:
    """Try to find ADB executable automatically"""
    import shutil
    adb = shutil.which("adb")
    if adb:
        return adb
    
    # Check common Windows paths
    windows_paths = [
        r"C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe",
        r"C:\Program Files\Android\android-sdk\platform-tools\adb.exe",
        r"C:\Users\%USERNAME%\AppData\Local\Android\Sdk\platform-tools\adb.exe",
        r"C:\adb\adb.exe",
        r".\platform-tools\adb.exe",
    ]
    
    import getpass
    username = getpass.getuser()
    
    for path in windows_paths:
        path = path.replace("%USERNAME%", username)
        if os.path.exists(path):
            return path
    
    return "adb"


if __name__ == "__main__":
    # Quick test
    core = ADBCore()
    print("Testing ADB connection...")
    devices = core.get_devices()
    for d in devices:
        print(f"Device: {d.serial} - {d.model} ({d.status})")
