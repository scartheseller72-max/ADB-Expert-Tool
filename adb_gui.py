"""
ADB Expert GUI v3.0 - Ultimate Professional Android Control Center
Max Expert Level - Unanswered, Unbound, Raw Expert
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os
import sys
import threading
import time
import json
from datetime import datetime

from adb_utils import ADBCore, ADBError, DeviceInfo, detect_adb_path


class ADBExpertGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ADB EXPERT TOOL v3.0 - Ultimate Android Control Center")
        self.root.geometry("1500x950")
        self.root.minsize(1300, 850)

        # ─── Theme ───
        self.BG0 = "#010409"
        self.BG1 = "#0d1117"
        self.BG2 = "#161b22"
        self.BG3 = "#21262d"
        self.BG4 = "#30363d"
        self.FG = "#e6edf3"
        self.FG2 = "#8b949e"
        self.BLUE = "#58a6ff"
        self.GREEN = "#3fb950"
        self.YELLOW = "#d29922"
        self.RED = "#f85149"
        self.PURPLE = "#bc8cff"
        self.CYAN = "#39d353"
        self.ORANGE = "#f0883e"

        self.root.configure(bg=self.BG0)

        # ─── ADB Core ───
        self.core = None
        self.selected_device = None
        self.devices: list = []
        self.fastboot_devices: list = []
        self.command_history = []
        self.history_index = -1

        # ─── Init ADB ───
        try:
            self.core = ADBCore()
        except ADBError as e:
            self._show_adb_error(str(e))
            return

        self._setup_styles()
        self._build_ui()
        self._refresh_devices()
        self.root.after(6000, self._auto_refresh)

    def _show_adb_error(self, msg):
        error_win = tk.Toplevel(self.root)
        error_win.title("ADB Not Found")
        error_win.geometry("600x300")
        error_win.configure(bg=self.BG1)

        tk.Label(error_win, text="ADB NOT FOUND", font=("Segoe UI", 18, "bold"),
                 bg=self.BG1, fg=self.RED).pack(pady=20)
        tk.Label(error_win, text=msg, font=("Consolas", 10), bg=self.BG1, fg=self.FG,
                 wraplength=550, justify=tk.LEFT).pack(padx=20, pady=10)
        tk.Label(error_win, text="Download from: https://developer.android.com/studio/releases/platform-tools",
                 font=("Consolas", 9), bg=self.BG1, fg=self.CYAN).pack(pady=5)
        tk.Button(error_win, text="Browse for adb.exe", command=lambda: self._browse_adb(error_win),
                  bg=self.BG3, fg=self.FG, font=("Segoe UI", 10), relief=tk.FLAT, padx=20, pady=8).pack(pady=15)

    def _browse_adb(self, win):
        path = filedialog.askopenfilename(filetypes=[("ADB", "adb.exe"), ("All", "*.*")])
        if path and os.path.exists(path):
            try:
                self.core = ADBCore(path)
                win.destroy()
                self._setup_styles()
                self._build_ui()
                self._refresh_devices()
                self.root.after(6000, self._auto_refresh)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TNotebook", background=self.BG0, borderwidth=0)
        s.configure("TNotebook.Tab", background=self.BG2, foreground=self.FG,
                     padding=[18, 10], font=("Segoe UI", 10, "bold"))
        s.map("TNotebook.Tab",
              background=[("selected", self.BG3), ("active", self.BG4)],
              foreground=[("selected", self.BLUE), ("active", self.FG)])
        s.configure("TFrame", background=self.BG0)
        s.configure("TLabelframe", background=self.BG2, borderwidth=2, relief="solid",
                     bordercolor=self.BG4)
        s.configure("TLabelframe.Label", background=self.BG2, foreground=self.BLUE,
                     font=("Segoe UI", 11, "bold"))
        s.configure("Treeview", background=self.BG2, foreground=self.FG,
                     fieldbackground=self.BG2, borderwidth=0, rowheight=26,
                     font=("Consolas", 9))
        s.configure("Treeview.Heading", background=self.BG3, foreground=self.FG,
                     font=("Segoe UI", 9, "bold"))
        s.map("Treeview", background=[("selected", self.BLUE)])

    def _build_ui(self):
        self._build_top_bar()
        self.notebook = ttk.Notebook(self.root, padding=5)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self._build_dashboard()
        self._build_shell()
        self._build_file_manager()
        self._build_app_manager()
        self._build_flash_tab()
        self._build_unlock_tab()
        self._build_diagnostics()
        self._build_network_tab()
        self._build_automation_tab()
        self._build_advanced_tab()
        self._build_status_bar()

    # ─── TOP BAR ───
    def _build_top_bar(self):
        bar = tk.Frame(self.root, bg=self.BG2, height=65)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        tk.Label(bar, text="ADB EXPERT", bg=self.BG2, fg=self.BLUE,
                 font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT, padx=15)
        tk.Label(bar, text="v3.0", bg=self.BG2, fg=self.FG2,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)

        tk.Label(bar, text="Device:", bg=self.BG2, fg=self.FG2,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(30, 5))
        self.device_var = tk.StringVar(value="Scanning...")
        self.device_combo = ttk.Combobox(bar, textvariable=self.device_var,
                                         state="readonly", width=55, font=("Consolas", 10))
        self.device_combo.pack(side=tk.LEFT, padx=5, pady=15)
        self.device_combo.bind("<<ComboboxSelected>>", self._on_device_select)

        self._make_btn(bar, "Refresh", self._refresh_devices, self.BLUE).pack(side=tk.LEFT, padx=5)
        self._make_btn(bar, "Connect WiFi", self._wifi_connect_dialog, self.GREEN).pack(side=tk.LEFT, padx=5)

        self._make_btn(bar, "Reboot", lambda: self._reboot(""), self.YELLOW).pack(side=tk.RIGHT, padx=3)
        self._make_btn(bar, "Bootloader", lambda: self._reboot("bootloader"), self.ORANGE).pack(side=tk.RIGHT, padx=3)
        self._make_btn(bar, "Recovery", lambda: self._reboot("recovery"), self.ORANGE).pack(side=tk.RIGHT, padx=3)
        self._make_btn(bar, "EDL", lambda: self._reboot_edl(), self.RED).pack(side=tk.RIGHT, padx=3)

        # Device status indicator
        self.device_status_dot = tk.Label(bar, text="●", bg=self.BG2, fg=self.RED,
                                          font=("Segoe UI", 18))
        self.device_status_dot.pack(side=tk.RIGHT, padx=10)

    def _make_btn(self, parent, text, cmd, color):
        btn = tk.Button(parent, text=text, command=cmd,
                        bg=self.BG3, fg=color, activebackground=color,
                        activeforeground="#fff", font=("Segoe UI", 9, "bold"),
                        relief=tk.FLAT, padx=12, pady=6, cursor="hand2")
        return btn

    def _build_status_bar(self):
        self.status_bar = tk.Label(self.root, text=f"Ready | ADB: {self.core.adb_path}",
                                   bg=self.BG2, fg=self.FG2, font=("Consolas", 9),
                                   anchor=tk.W, padx=10)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ─── DASHBOARD ───
    def _build_dashboard(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Dashboard ")

        # Left - Info
        left = ttk.LabelFrame(frame, text="Device Information", padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.info_text = scrolledtext.ScrolledText(left, wrap=tk.WORD, font=("Consolas", 10),
                                                    bg=self.BG2, fg=self.FG, insertbackground=self.FG,
                                                    relief=tk.FLAT, state=tk.DISABLED, padx=12, pady=12)
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # Right - Stats + Actions
        right = tk.Frame(frame, bg=self.BG0)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        stats = ttk.LabelFrame(right, text="Quick Stats", padding=10)
        stats.pack(fill=tk.X, pady=5)

        self.stat_labels = {}
        stat_items = [
            ("Status", "●"), ("Model", ""), ("Brand", ""), ("Android", ""),
            ("SDK", ""), ("Battery", ""), ("Root", ""), ("Bootloader", ""),
            ("Chipset", ""), ("IMEI", ""), ("RAM", ""), ("Storage", ""),
            ("SELinux", ""), ("Resolution", ""), ("Density", ""), ("Uptime", ""),
            ("Kernel", ""), ("Magisk", ""), ("TWRP", ""), ("WiFi", ""),
        ]
        for i, (key, _) in enumerate(stat_items):
            row, col = divmod(i, 2)
            tk.Label(stats, text=f"{key}:", font=("Segoe UI", 9, "bold"),
                     bg=self.BG2, fg=self.CYAN, anchor=tk.W).grid(row=row, column=col*2, sticky=tk.W, pady=2, padx=5)
            lbl = tk.Label(stats, text="N/A", font=("Consolas", 9),
                           bg=self.BG2, fg=self.FG, anchor=tk.W, width=20)
            lbl.grid(row=row, column=col*2+1, sticky=tk.W, padx=5, pady=2)
            self.stat_labels[key] = lbl

        actions = ttk.LabelFrame(right, text="Quick Actions", padding=10)
        actions.pack(fill=tk.X, pady=10)

        btns = [
            ("Screenshot", self._screenshot, self.BLUE),
            ("Screen Record", self._screen_record, self.BLUE),
            ("Dump UI XML", self._dump_ui_action, self.PURPLE),
            ("Clear Cache", self._clear_cache, self.YELLOW),
            ("Emergency Info", self._emergency_info, self.RED),
            ("Wake Screen", self._wake_screen, self.GREEN),
            ("Open App...", self._open_app_dialog, self.CYAN),
            ("Reboot System", lambda: self._reboot(""), self.ORANGE),
        ]
        for i, (text, cmd, color) in enumerate(btns):
            tk.Button(actions, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=12, pady=8,
                      cursor="hand2", width=14).grid(row=i//4, column=i%4, padx=4, pady=4)

    # ─── SHELL ───
    def _build_shell(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Shell ")

        self.shell_out = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Consolas", 10),
                                                     bg=self.BG2, fg=self.GREEN, insertbackground=self.GREEN,
                                                     relief=tk.FLAT, state=tk.DISABLED, padx=12, pady=12)
        self.shell_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))

        inp = tk.Frame(frame, bg=self.BG0, height=50)
        inp.pack(fill=tk.X, padx=8, pady=8)
        inp.pack_propagate(False)

        tk.Label(inp, text="$", bg=self.BG0, fg=self.GREEN,
                 font=("Consolas", 14, "bold")).pack(side=tk.LEFT, padx=8)

        self.shell_input = tk.Entry(inp, font=("Consolas", 11), bg=self.BG2, fg=self.FG,
                                     insertbackground=self.GREEN, relief=tk.FLAT,
                                     highlightthickness=1, highlightcolor=self.GREEN,
                                     highlightbackground=self.BG4)
        self.shell_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=8)
        self.shell_input.bind("<Return>", self._exec_shell)
        self.shell_input.bind("<Up>", self._hist_prev)
        self.shell_input.bind("<Down>", self._hist_next)

        self.root_var = tk.BooleanVar(value=False)
        tk.Checkbutton(inp, text="ROOT", variable=self.root_var, bg=self.BG0, fg=self.RED,
                       selectcolor=self.BG3, activebackground=self.BG0,
                       activeforeground=self.RED, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=8)

        tk.Button(inp, text="EXECUTE", command=lambda: self._exec_shell(None),
                  bg=self.GREEN, fg="#000", activebackground="#5ffa7d",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=20, pady=6,
                  cursor="hand2").pack(side=tk.RIGHT, padx=5, pady=8)
        tk.Button(inp, text="CLEAR", command=self._clear_shell,
                  bg=self.BG3, fg=self.FG, activebackground=self.RED, activeforeground="#fff",
                  font=("Segoe UI", 9), relief=tk.FLAT, padx=12, pady=6,
                  cursor="hand2").pack(side=tk.RIGHT, padx=5, pady=8)

    # ─── FILE MANAGER ───
    def _build_file_manager(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Files ")

        toolbar = tk.Frame(frame, bg=self.BG0, height=40)
        toolbar.pack(fill=tk.X, padx=8, pady=5)
        toolbar.pack_propagate(False)

        self.fm_path = tk.StringVar(value="/sdcard/")
        tk.Entry(toolbar, textvariable=self.fm_path, font=("Consolas", 10),
                 bg=self.BG2, fg=self.FG, relief=tk.FLAT,
                 highlightthickness=1, highlightcolor=self.BLUE).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        for text, cmd, color in [("List", self._fm_list, self.BLUE), ("Push", self._fm_push, self.GREEN),
                                   ("Pull", self._fm_pull, self.CYAN), ("Delete", self._fm_delete, self.RED),
                                   ("Mkdir", self._fm_mkdir, self.YELLOW), ("Search", self._fm_search, self.PURPLE),
                                   ("Up", self._fm_up, self.FG2), ("Refresh", self._fm_list, self.BLUE)]:
            tk.Button(toolbar, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4,
                      cursor="hand2").pack(side=tk.LEFT, padx=3, pady=5)

        cols = ("Perms", "Owner", "Size", "Date", "Name")
        self.fm_tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        widths = [100, 80, 80, 120, 400]
        for c, w in zip(cols, widths):
            self.fm_tree.heading(c, text=c)
            self.fm_tree.column(c, width=w)

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.fm_tree.yview)
        self.fm_tree.configure(yscrollcommand=sb.set)
        self.fm_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=5)
        sb.pack(side=tk.LEFT, fill=tk.Y, pady=5)
        self.fm_tree.bind("<Double-1>", self._fm_dblclick)

    # ─── APP MANAGER ───
    def _build_app_manager(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Apps ")

        toolbar = tk.Frame(frame, bg=self.BG0, height=40)
        toolbar.pack(fill=tk.X, padx=8, pady=5)
        toolbar.pack_propagate(False)

        self.app_filter = tk.StringVar(value="All")
        tk.OptionMenu(toolbar, self.app_filter, "All", "System", "Third-Party").pack(side=tk.LEFT, padx=5)

        for text, cmd, color in [("Refresh", self._app_refresh, self.BLUE), ("Install APK", self._app_install, self.GREEN),
                                   ("Uninstall", self._app_uninstall, self.RED), ("Backup", self._app_backup, self.CYAN),
                                   ("Clear Data", self._app_clear, self.YELLOW), ("Force Stop", self._app_force_stop, self.ORANGE),
                                   ("Disable", self._app_disable, self.RED), ("Enable", self._app_enable, self.GREEN)]:
            tk.Button(toolbar, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4,
                      cursor="hand2").pack(side=tk.LEFT, padx=3, pady=5)

        cols = ("Package Name",)
        self.app_tree = ttk.Treeview(frame, columns=cols, show="headings", height=22)
        self.app_tree.heading("Package Name", text="Package Name")
        self.app_tree.column("Package Name", width=500)

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.app_tree.yview)
        self.app_tree.configure(yscrollcommand=sb.set)
        self.app_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=5)
        sb.pack(side=tk.LEFT, fill=tk.Y, pady=5)

        self.app_info = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Consolas", 9),
                                                   bg=self.BG2, fg=self.FG, width=45,
                                                   insertbackground=self.FG, relief=tk.FLAT,
                                                   state=tk.DISABLED, padx=10, pady=10)
        self.app_info.pack(side=tk.RIGHT, fill=tk.BOTH, padx=8, pady=5)

    # ─── FLASH TAB ───
    def _build_flash_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Flash & Recovery ")

        warn = tk.Label(frame, text="DANGER ZONE - Fastboot Flash & Sideload",
                        bg=self.RED, fg="#fff", font=("Segoe UI", 12, "bold"), pady=8)
        warn.pack(fill=tk.X, padx=8, pady=(8, 0))

        # Flash section
        flash = ttk.LabelFrame(frame, text="Fastboot Partition Flash", padding=12)
        flash.pack(fill=tk.X, padx=8, pady=8)

        tk.Label(flash, text="Partition:", bg=self.BG2, fg=self.FG).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.flash_part = tk.StringVar(value="boot")
        tk.Entry(flash, textvariable=self.flash_part, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=20).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(flash, text="Image:", bg=self.BG2, fg=self.FG).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.flash_file = tk.StringVar()
        tk.Entry(flash, textvariable=self.flash_file, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=50).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(flash, text="Browse", command=self._browse_flash,
                  bg=self.BG3, fg=self.FG, relief=tk.FLAT, padx=10, cursor="hand2").grid(row=1, column=2, padx=5)

        tk.Button(flash, text="FLASH IMAGE", command=self._flash_image,
                  bg=self.RED, fg="#fff", activebackground="#ff6b6b",
                  font=("Segoe UI", 11, "bold"), relief=tk.FLAT, padx=40, pady=10,
                  cursor="hand2").grid(row=2, column=0, columnspan=3, pady=10)

        # Quick flash buttons
        quick = ttk.LabelFrame(frame, text="Quick Partition Flash", padding=12)
        quick.pack(fill=tk.X, padx=8, pady=8)

        parts = [("boot", "Boot"), ("recovery", "Recovery"), ("system", "System"),
                 ("vendor", "Vendor"), ("vbmeta", "VBMeta"), ("dtbo", "DTBO"),
                 ("userdata", "UserData"), ("cache", "Cache"), ("persist", "Persist"),
                 ("modem", "Modem"), ("super", "Super"), ("product", "Product")]
        for i, (part, label) in enumerate(parts):
            tk.Button(quick, text=label, command=lambda p=part: self._quick_flash(p),
                      bg=self.BG3, fg=self.ORANGE, activebackground=self.ORANGE,
                      activeforeground="#fff", font=("Segoe UI", 9, "bold"),
                      relief=tk.FLAT, padx=15, pady=6, cursor="hand2",
                      width=10).grid(row=i//6, column=i%6, padx=3, pady=3)

        # Sideload
        side = ttk.LabelFrame(frame, text="Recovery Sideload (OTA / ZIP)", padding=12)
        side.pack(fill=tk.X, padx=8, pady=8)

        tk.Label(side, text="ZIP File:", bg=self.BG2, fg=self.FG).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.sideload_file = tk.StringVar()
        tk.Entry(side, textvariable=self.sideload_file, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=50).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(side, text="Browse", command=self._browse_sideload,
                  bg=self.BG3, fg=self.FG, relief=tk.FLAT, padx=10, cursor="hand2").grid(row=0, column=2, padx=5)
        tk.Button(side, text="SIDELOAD", command=self._sideload,
                  bg=self.YELLOW, fg="#000", activebackground="#ffd966",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=30, pady=8,
                  cursor="hand2").grid(row=1, column=0, columnspan=3, pady=10)

        # Fastboot info
        info = ttk.LabelFrame(frame, text="Fastboot Info", padding=12)
        info.pack(fill=tk.X, padx=8, pady=8)

        for i, (text, cmd) in enumerate([("Getvar All", lambda: self._fb_getvar("all")),
                                          ("Active Slot", lambda: self._fb_getvar("current-slot")),
                                          ("Partitions", lambda: self._fb_getvar("partition-type:all")),
                                          ("Erase Partition", self._fb_erase_dialog),
                                          ("Format Partition", self._fb_format_dialog),
                                          ("Boot Image", self._fb_boot_dialog),
                                          ("Update ZIP", self._fb_update_dialog)]):
            tk.Button(info, text=text, command=cmd, bg=self.BG3, fg=self.CYAN,
                      activebackground=self.CYAN, activeforeground="#000",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                      cursor="hand2").grid(row=i//4, column=i%4, padx=3, pady=3)

        # Output
        self.flash_out = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Consolas", 9),
                                                    bg=self.BG2, fg=self.FG, height=10,
                                                    insertbackground=self.FG, relief=tk.FLAT,
                                                    state=tk.DISABLED, padx=10, pady=10)
        self.flash_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    # ─── UNLOCK & ROOT TAB ───
    def _build_unlock_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Unlock & Root ")

        warn = tk.Label(frame, text="EXPERT ZONE - These operations can PERMANENTLY brick your device!",
                        bg=self.RED, fg="#fff", font=("Segoe UI", 12, "bold"), pady=10)
        warn.pack(fill=tk.X, padx=8, pady=(8, 0))

        # Bootloader
        bl = ttk.LabelFrame(frame, text="Bootloader Control", padding=12)
        bl.pack(fill=tk.X, padx=8, pady=8)

        bl_btns = [
            ("Check Status", self._bl_check, self.BLUE),
            ("OEM Unlock (Old)", self._bl_oem_unlock, self.RED),
            ("OEM Lock", self._bl_oem_lock, self.YELLOW),
            ("Flashing Unlock (New)", self._bl_flashing_unlock, self.RED),
            ("Flashing Lock", self._bl_flashing_lock, self.YELLOW),
        ]
        for i, (text, cmd, color) in enumerate(bl_btns):
            tk.Button(bl, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=20, pady=8,
                      cursor="hand2").grid(row=0, column=i, padx=5, pady=5)

        # Root
        root = ttk.LabelFrame(frame, text="Root & Privilege Escalation", padding=12)
        root.pack(fill=tk.X, padx=8, pady=8)

        root_btns = [
            ("Check Root", self._root_check, self.BLUE),
            ("Push Magisk", self._root_magisk, self.GREEN),
            ("Remount RW", self._root_remount, self.ORANGE),
            ("Disable Verity", self._root_disable_verity, self.RED),
            ("Enable Verity", self._root_enable_verity, self.GREEN),
            ("SELinux Enforcing", lambda: self._set_selinux("enforcing"), self.BLUE),
            ("SELinux Permissive", lambda: self._set_selinux("permissive"), self.YELLOW),
        ]
        for i, (text, cmd, color) in enumerate(root_btns):
            tk.Button(root, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=8,
                      cursor="hand2").grid(row=i//4, column=i%4, padx=5, pady=5)

        # Lock bypass
        bypass = ttk.LabelFrame(frame, text="Lock Screen Bypass (OWN DEVICE ONLY)", padding=12)
        bypass.pack(fill=tk.X, padx=8, pady=8)

        bypass_btns = [
            ("Swipe Unlock", lambda: self._bypass("swipe"), self.BLUE),
            ("Null PIN", lambda: self._bypass("null_pin"), self.YELLOW),
            ("Settings Crash", lambda: self._bypass("settings_crash"), self.ORANGE),
            ("Delete Keys (Root)", lambda: self._bypass("delete_keys"), self.RED),
            ("FRP Data Delete (Root)", lambda: self._bypass("frp"), self.RED),
        ]
        for i, (text, cmd, color) in enumerate(bypass_btns):
            tk.Button(bypass, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=8,
                      cursor="hand2").grid(row=0, column=i, padx=5, pady=5)

        self.unlock_out = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Consolas", 9),
                                                     bg=self.BG2, fg=self.FG, height=12,
                                                     insertbackground=self.FG, relief=tk.FLAT,
                                                     state=tk.DISABLED, padx=10, pady=10)
        self.unlock_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    # ─── DIAGNOSTICS TAB ───
    def _build_diagnostics(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Diagnostics ")

        ctrl = tk.Frame(frame, bg=self.BG0, height=40)
        ctrl.pack(fill=tk.X, padx=8, pady=5)
        ctrl.pack_propagate(False)

        diag_btns = [
            ("Logcat", self._diag_logcat, self.BLUE),
            ("dmesg", self._diag_dmesg, self.CYAN),
            ("Processes", self._diag_procs, self.GREEN),
            ("Battery", self._diag_battery, self.YELLOW),
            ("Memory", self._diag_memory, self.PURPLE),
            ("CPU Info", self._diag_cpu, self.ORANGE),
            ("Thermal", self._diag_thermal, self.RED),
            ("Disk Usage", self._diag_disk, self.CYAN),
            ("Mounts", self._diag_mounts, self.FG2),
            ("Kernel", self._diag_kernel, self.BLUE),
            ("Partitions", self._diag_partitions, self.GREEN),
            ("Services", self._diag_services, self.PURPLE),
            ("Current App", self._diag_current_app, self.YELLOW),
            ("Clear", self._diag_clear, self.RED),
        ]
        for text, cmd, color in diag_btns:
            tk.Button(ctrl, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10, pady=4,
                      cursor="hand2").pack(side=tk.LEFT, padx=2, pady=5)

        self.diag_out = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Consolas", 9),
                                                   bg=self.BG2, fg=self.FG,
                                                   insertbackground=self.FG, relief=tk.FLAT,
                                                   state=tk.DISABLED, padx=10, pady=10)
        self.diag_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)

    # ─── NETWORK TAB ───
    def _build_network_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Network ")

        # Wireless ADB
        wifi = ttk.LabelFrame(frame, text="Wireless ADB", padding=12)
        wifi.pack(fill=tk.X, padx=8, pady=8)

        tk.Label(wifi, text="IP:", bg=self.BG2, fg=self.FG).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.wifi_ip = tk.StringVar()
        tk.Entry(wifi, textvariable=self.wifi_ip, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=20).grid(row=0, column=1, padx=5, pady=5)
        tk.Label(wifi, text="Port:", bg=self.BG2, fg=self.FG).grid(row=0, column=2, sticky=tk.W, pady=5)
        self.wifi_port = tk.StringVar(value="5555")
        tk.Entry(wifi, textvariable=self.wifi_port, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=8).grid(row=0, column=3, padx=5, pady=5)

        for text, cmd, color in [("Connect", self._net_connect, self.GREEN),
                                   ("Disconnect All", self._net_disconnect, self.RED),
                                   ("Bluetooth Pair", self._net_bt_pair, self.PURPLE),
                                   ("Bluetooth Connect", self._net_bt_connect, self.CYAN)]:
            tk.Button(wifi, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                      cursor="hand2").grid(row=0, column=4 + [("Connect", 0), ("Disconnect All", 1),
                                                                ("Bluetooth Pair", 2), ("Bluetooth Connect", 3)].index((text, 0)),
                                           padx=5, pady=5) if False else None

        # Recreate buttons properly
        btn_frame = tk.Frame(wifi, bg=self.BG2)
        btn_frame.grid(row=1, column=0, columnspan=5, pady=10)
        for text, cmd, color in [("Connect WiFi", self._net_connect, self.GREEN),
                                   ("Disconnect All", self._net_disconnect, self.RED),
                                   ("BT Pair", self._net_bt_pair, self.PURPLE),
                                   ("BT Connect", self._net_bt_connect, self.CYAN)]:
            tk.Button(btn_frame, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                      cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Port forwarding
        fwd = ttk.LabelFrame(frame, text="Port Forwarding", padding=12)
        fwd.pack(fill=tk.X, padx=8, pady=8)

        tk.Label(fwd, text="Local:", bg=self.BG2, fg=self.FG).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.fwd_local = tk.StringVar(value="tcp:8080")
        tk.Entry(fwd, textvariable=self.fwd_local, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=15).grid(row=0, column=1, padx=5, pady=5)
        tk.Label(fwd, text="Remote:", bg=self.BG2, fg=self.FG).grid(row=0, column=2, sticky=tk.W, pady=5)
        self.fwd_remote = tk.StringVar(value="tcp:8080")
        tk.Entry(fwd, textvariable=self.fwd_remote, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=15).grid(row=0, column=3, padx=5, pady=5)

        for text, cmd in [("Forward", self._net_forward), ("List Forwards", self._net_list_fwd),
                           ("Reverse", self._net_reverse), ("List Reverse", self._net_list_reverse)]:
            tk.Button(fwd, text=text, command=cmd, bg=self.BG3, fg=self.BLUE,
                      activebackground=self.BLUE, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                      cursor="hand2").grid(row=0, column=4, padx=5, pady=5) if text == "Forward" else None

        fwd_btns = tk.Frame(fwd, bg=self.BG2)
        fwd_btns.grid(row=1, column=0, columnspan=5, pady=10)
        for text, cmd in [("Forward", self._net_forward), ("List Forwards", self._net_list_fwd),
                           ("Reverse", self._net_reverse), ("List Reverse", self._net_list_reverse)]:
            tk.Button(fwd_btns, text=text, command=cmd, bg=self.BG3, fg=self.BLUE,
                      activebackground=self.BLUE, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                      cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Proxy
        proxy = ttk.LabelFrame(frame, text="Proxy", padding=12)
        proxy.pack(fill=tk.X, padx=8, pady=8)

        tk.Label(proxy, text="Proxy (host:port):", bg=self.BG2, fg=self.FG).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.proxy_addr = tk.StringVar()
        tk.Entry(proxy, textvariable=self.proxy_addr, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=30).grid(row=0, column=1, padx=5, pady=5)
        for text, cmd, color in [("Set", self._net_set_proxy, self.GREEN), ("Remove", self._net_rm_proxy, self.RED)]:
            tk.Button(proxy, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                      cursor="hand2").grid(row=0, column=2, padx=5, pady=5) if text == "Set" else None

        proxy_btns = tk.Frame(proxy, bg=self.BG2)
        proxy_btns.grid(row=0, column=2, padx=5)
        for text, cmd, color in [("Set", self._net_set_proxy, self.GREEN), ("Remove", self._net_rm_proxy, self.RED)]:
            tk.Button(proxy_btns, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                      cursor="hand2").pack(side=tk.LEFT, padx=5)

        self.net_out = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Consolas", 9),
                                                  bg=self.BG2, fg=self.FG, height=15,
                                                  insertbackground=self.FG, relief=tk.FLAT,
                                                  state=tk.DISABLED, padx=10, pady=10)
        self.net_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    # ─── AUTOMATION TAB ───
    def _build_automation_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Automation ")

        # Touch
        touch = ttk.LabelFrame(frame, text="Touch & Input", padding=12)
        touch.pack(fill=tk.X, padx=8, pady=8)

        tk.Label(touch, text="X:", bg=self.BG2, fg=self.FG).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.tap_x = tk.StringVar(value="540")
        tk.Entry(touch, textvariable=self.tap_x, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=8).grid(row=0, column=1, padx=3)
        tk.Label(touch, text="Y:", bg=self.BG2, fg=self.FG).grid(row=0, column=2, sticky=tk.W, pady=5)
        self.tap_y = tk.StringVar(value="960")
        tk.Entry(touch, textvariable=self.tap_y, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=8).grid(row=0, column=3, padx=3)

        for text, cmd in [("Tap", self._auto_tap), ("Long Press", self._auto_longpress)]:
            tk.Button(touch, text=text, command=cmd, bg=self.BG3, fg=self.BLUE,
                      activebackground=self.BLUE, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                      cursor="hand2").grid(row=0, column=4, padx=5) if text == "Tap" else None

        tap_btns = tk.Frame(touch, bg=self.BG2)
        tap_btns.grid(row=0, column=4, padx=5)
        for text, cmd in [("Tap", self._auto_tap), ("Long Press", self._auto_longpress)]:
            tk.Button(tap_btns, text=text, command=cmd, bg=self.BG3, fg=self.BLUE,
                      activebackground=self.BLUE, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                      cursor="hand2").pack(side=tk.LEFT, padx=3)

        # Swipe
        tk.Label(touch, text="Swipe X1 Y1 X2 Y2:", bg=self.BG2, fg=self.FG).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.swipe_vars = [tk.StringVar(value=v) for v in ["540", "1800", "540", "600"]]
        for i, var in enumerate(self.swipe_vars):
            tk.Entry(touch, textvariable=var, font=("Consolas", 10),
                     bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=6).grid(row=1, column=i+1, padx=2)
        tk.Button(touch, text="Swipe", command=self._auto_swipe, bg=self.BG3, fg=self.CYAN,
                  activebackground=self.CYAN, activeforeground="#000",
                  font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                  cursor="hand2").grid(row=1, column=5, padx=5)

        # Text
        tk.Label(touch, text="Text:", bg=self.BG2, fg=self.FG).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.input_text_var = tk.StringVar()
        tk.Entry(touch, textvariable=self.input_text_var, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=40).grid(row=2, column=1, columnspan=4, padx=5, sticky=tk.W)
        tk.Button(touch, text="Send Text", command=self._auto_text, bg=self.BG3, fg=self.GREEN,
                  activebackground=self.GREEN, activeforeground="#000",
                  font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                  cursor="hand2").grid(row=2, column=5, padx=5)

        # Keys
        keys = ttk.LabelFrame(frame, text="Key Events", padding=12)
        keys.pack(fill=tk.X, padx=8, pady=8)

        key_list = [
            ("HOME", "3"), ("BACK", "4"), ("POWER", "26"), ("VOL+", "24"),
            ("VOL-", "25"), ("MENU", "82"), ("ENTER", "66"), ("DEL", "67"),
            ("TAB", "61"), ("ESC", "111"), ("CAMERA", "27"), ("MUTE", "164"),
            ("BRIGHT+", "221"), ("BRIGHT-", "220"), ("MEDIA_PLAY", "126"),
            ("MEDIA_PAUSE", "127"), ("MEDIA_NEXT", "87"), ("MEDIA_PREV", "88"),
        ]
        for i, (name, code) in enumerate(key_list):
            tk.Button(keys, text=name, command=lambda c=code: self._auto_key(c),
                      bg=self.BG3, fg=self.FG, activebackground=self.BLUE,
                      activeforeground="#fff", font=("Segoe UI", 8, "bold"),
                      relief=tk.FLAT, padx=8, pady=5, cursor="hand2",
                      width=10).grid(row=i//6, column=i%6, padx=2, pady=2)

        # Monkey
        monkey = ttk.LabelFrame(frame, text="Monkey Stress Test", padding=12)
        monkey.pack(fill=tk.X, padx=8, pady=8)

        tk.Label(monkey, text="Events:", bg=self.BG2, fg=self.FG).grid(row=0, column=0, sticky=tk.W)
        self.monkey_events = tk.StringVar(value="5000")
        tk.Entry(monkey, textvariable=self.monkey_events, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=10).grid(row=0, column=1, padx=5)
        tk.Label(monkey, text="Package:", bg=self.BG2, fg=self.FG).grid(row=0, column=2, sticky=tk.W)
        self.monkey_pkg = tk.StringVar()
        tk.Entry(monkey, textvariable=self.monkey_pkg, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=30).grid(row=0, column=3, padx=5)
        tk.Button(monkey, text="RUN MONKEY", command=self._auto_monkey,
                  bg=self.RED, fg="#fff", activebackground="#ff6b6b",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=30, pady=8,
                  cursor="hand2").grid(row=0, column=4, padx=15)

        # Dev options
        dev = ttk.LabelFrame(frame, text="Developer Options Quick Toggles", padding=12)
        dev.pack(fill=tk.X, padx=8, pady=8)

        dev_btns = [
            ("Enable Dev Options", self._dev_enable, self.GREEN),
            ("Stay Awake", self._dev_stay_awake, self.BLUE),
            ("Disable Animations", lambda: self._dev_anim(0), self.YELLOW),
            ("Show Touches", self._dev_show_touches, self.CYAN),
            ("Pointer Location", self._dev_pointer, self.PURPLE),
            ("Mock Location", self._dev_mock_loc, self.ORANGE),
            ("Reset DPI", self._dev_reset_dpi, self.BLUE),
            ("Reset Resolution", self._dev_reset_res, self.BLUE),
            ("Open URL...", self._dev_open_url, self.GREEN),
        ]
        for i, (text, cmd, color) in enumerate(dev_btns):
            tk.Button(dev, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=12, pady=6,
                      cursor="hand2").grid(row=i//5, column=i%5, padx=3, pady=3)

        self.auto_out = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Consolas", 9),
                                                   bg=self.BG2, fg=self.FG, height=8,
                                                   insertbackground=self.FG, relief=tk.FLAT,
                                                   state=tk.DISABLED, padx=10, pady=10)
        self.auto_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    # ─── ADVANCED TAB ───
    def _build_advanced_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Advanced ")

        # Properties
        props = ttk.LabelFrame(frame, text="Build.prop / Properties Editor", padding=12)
        props.pack(fill=tk.X, padx=8, pady=8)

        for text, cmd, color in [("Load All Props", self._adv_load_props, self.BLUE),
                                   ("Save Props", self._adv_save_props, self.GREEN)]:
            tk.Button(props, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                      cursor="hand2").grid(row=0, column=0 if text.startswith("L") else 1, padx=5, pady=5)

        tk.Label(props, text="Property:", bg=self.BG2, fg=self.FG).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.prop_key = tk.StringVar()
        tk.Entry(props, textvariable=self.prop_key, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=30).grid(row=1, column=1, padx=5, pady=5)
        tk.Label(props, text="Value:", bg=self.BG2, fg=self.FG).grid(row=1, column=2, sticky=tk.W, pady=5)
        self.prop_val = tk.StringVar()
        tk.Entry(props, textvariable=self.prop_val, font=("Consolas", 10),
                 bg=self.BG3, fg=self.FG, relief=tk.FLAT, width=30).grid(row=1, column=3, padx=5, pady=5)
        tk.Button(props, text="Set Property", command=self._adv_set_prop,
                  bg=self.YELLOW, fg="#000", activebackground="#ffd966",
                  font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                  cursor="hand2").grid(row=1, column=4, padx=10, pady=5)

        # Settings
        sett = ttk.LabelFrame(frame, text="Settings Browser", padding=12)
        sett.pack(fill=tk.X, padx=8, pady=8)

        for text, cmd in [("Global Settings", lambda: self._adv_settings("global")),
                           ("Secure Settings", lambda: self._adv_settings("secure")),
                           ("System Settings", lambda: self._adv_settings("system"))]:
            tk.Button(sett, text=text, command=cmd, bg=self.BG3, fg=self.BLUE,
                      activebackground=self.BLUE, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                      cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Expert tools
        expert = ttk.LabelFrame(frame, text="Expert Tools", padding=12)
        expert.pack(fill=tk.X, padx=8, pady=8)

        expert_btns = [
            ("Dump UI XML", self._adv_dump_ui, self.BLUE),
            ("Extract Contacts DB", self._adv_contacts, self.CYAN),
            ("Extract SMS DB", self._adv_sms, self.CYAN),
            ("WiFi Config (Root)", self._adv_wifi_cfg, self.GREEN),
            ("List Users", self._adv_users, self.PURPLE),
            ("List Accounts", self._adv_accounts, self.PURPLE),
            ("Open URL...", self._adv_open_url, self.GREEN),
            ("Factory Reset", self._adv_factory_reset, self.RED),
            ("Wipe Cache", self._adv_wipe_cache, self.RED),
            ("Full Partition List", self._adv_partition_list, self.ORANGE),
            ("Partition Info", self._adv_partition_info, self.ORANGE),
            ("Media Scan", self._adv_media_scan, self.CYAN),
        ]
        for i, (text, cmd, color) in enumerate(expert_btns):
            tk.Button(expert, text=text, command=cmd, bg=self.BG3, fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=12, pady=6,
                      cursor="hand2").grid(row=i//6, column=i%6, padx=3, pady=3)

        # Full ROM flash
        rom = ttk.LabelFrame(frame, text="Full ROM Flash (Fastboot)", padding=12)
        rom.pack(fill=tk.X, padx=8, pady=8)

        tk.Button(rom, text="Select Flash Package (Folder)", command=self._adv_flash_package,
                  bg=self.RED, fg="#fff", activebackground="#ff6b6b",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=25, pady=10,
                  cursor="hand2").pack(side=tk.LEFT, padx=5)

        tk.Button(rom, text="Flash with --skip-reboot", command=self._adv_flash_skip_reboot,
                  bg=self.ORANGE, fg="#fff", activebackground="#ffaa44",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=25, pady=10,
                  cursor="hand2").pack(side=tk.LEFT, padx=5)

        self.adv_out = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Consolas", 9),
                                                  bg=self.BG2, fg=self.FG, height=15,
                                                  insertbackground=self.FG, relief=tk.FLAT,
                                                  state=tk.DISABLED, padx=10, pady=10)
        self.adv_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    # ==================== LOGIC ====================

    def _log(self, msg, widget=None):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        if widget:
            widget.configure(state=tk.NORMAL)
            widget.insert(tk.END, line)
            widget.see(tk.END)
            widget.configure(state=tk.DISABLED)
        self.status_bar.config(text=f"[{ts}] {msg[:100]}")

    def _get_out(self):
        """Get output widget for current tab"""
        idx = self.notebook.index(self.notebook.select())
        widgets = [self.info_text, self.shell_out, None, None,
                   self.flash_out, self.unlock_out, self.diag_out,
                   self.net_out, self.auto_out, self.adv_out]
        return widgets[idx] if idx < len(widgets) else None

    def _run_async(self, func, callback=None):
        def wrapper():
            try:
                result = func()
                if callback:
                    self.root.after(0, lambda: callback(result))
                else:
                    w = self._get_out()
                    if w:
                        self.root.after(0, lambda: self._log(str(result), w))
                    else:
                        self.root.after(0, lambda: self._log(str(result)))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"Error: {e}", self._get_out()))
        threading.Thread(target=wrapper, daemon=True).start()

    def _check(self) -> bool:
        if not self.selected_device:
            messagebox.showwarning("No Device", "Select a device first!")
            return False
        return True

    def _refresh_devices(self):
        try:
            self.devices = self.core.get_devices()
            self.fastboot_devices = self.core.get_fastboot_devices()

            all_devs = self.devices + self.fastboot_devices
            labels = []
            for d in all_devs:
                status_icon = {"device": "[ADB]", "unauthorized": "[!UNAUTH]", "offline": "[OFFLINE]",
                               "recovery": "[RECOVERY]", "sideload": "[SIDELOAD]", "fastboot": "[FASTBOOT]"}.get(d.status, f"[{d.status.upper()}]")
                label = f"{d.serial} | {status_icon} {d.model} {d.brand} {d.device_name}"
                labels.append(label)

            if not labels:
                labels = ["No devices connected"]

            self.device_combo['values'] = labels

            if all_devs:
                self.device_combo.current(0)
                self._on_device_select(None)
                self.device_status_dot.config(fg=self.GREEN)
            else:
                self.device_status_dot.config(fg=self.RED)

        except Exception as e:
            self.status_bar.config(text=f"Refresh error: {e}")

    def _auto_refresh(self):
        self._refresh_devices()
        self.root.after(6000, self._auto_refresh)

    def _on_device_select(self, event):
        sel = self.device_var.get()
        if "No devices" in sel:
            self.selected_device = None
            self.device_status_dot.config(fg=self.RED)
            return

        serial = sel.split(" | ")[0]
        self.selected_device = serial

        all_devs = self.devices + self.fastboot_devices
        for d in all_devs:
            if d.serial == serial:
                if d.is_fastboot:
                    self.device_status_dot.config(fg=self.ORANGE)
                elif d.status == "unauthorized":
                    self.device_status_dot.config(fg=self.YELLOW)
                else:
                    self.device_status_dot.config(fg=self.GREEN)
                self._update_dashboard(d)
                break

    def _update_dashboard(self, d: DeviceInfo):
        info = f"""
╔══════════════════════════════════════════════════════════════╗
║                    DEVICE INFORMATION                        ║
╠══════════════════════════════════════════════════════════════╣
║ Serial Number:    {d.serial:<42}║
║ Status:           {d.status:<42}║
║ Model:            {d.model:<42}║
║ Brand:            {d.brand:<42}║
║ Device Name:      {d.device_name:<42}║
║ Android Version:  {d.android_version:<42}║
║ SDK Version:      {d.sdk_version:<42}║
║ Security Patch:   {d.security_patch:<42}║
║ Build Number:     {d.build_number:<42}║
║ Build Fingerprint:{d.build_fingerprint:<42}║
║ Product:          {d.product:<42}║
║ Hardware:         {d.hardware:<42}║
║ Chipset:          {d.chipset:<42}║
║ Bootloader:       {d.bootloader:<42}║
║ Baseband:         {d.baseband:<42}║
║ Kernel:           {d.kernel_version:<42}║
║ Battery:          {d.battery_level:<42}║
║ Battery Status:   {d.battery_status:<42}║
║ Battery Health:   {d.battery_health:<42}║
║ Battery Temp:     {d.battery_temp:<42}║
║ IMEI:             {d.imei:<42}║
║ Serial (HW):      {d.serial_number:<42}║
║ Screen:           {d.screen_resolution:<42}║
║ DPI:              {d.screen_density:<42}║
║ RAM:              {d.total_ram:<42}║
║ Storage:          {d.available_storage:<42}║
║ SELinux:          {d.selinux_mode:<42}║
║ Encryption:       {d.encryption_state:<42}║
║ USB Config:       {d.usb_config:<42}║
║ IP Address:       {d.ip_address:<42}║
║ WiFi SSID:        {d.wifi_ssid:<42}║
║ Uptime:           {d.uptime:<42}║
║ Root Access:      {'YES' if d.root_access else 'NO':<42}║
║ Magisk:           {'YES' if d.magisk_installed else 'NO':<42}║
║ TWRP:             {'YES' if d.twrp_installed else 'NO':<42}║
║ Bootloader:       {'UNLOCKED' if d.bootloader_unlocked else 'LOCKED':<42}║
║ Emulator:         {'YES' if d.is_emulator else 'NO':<42}║
╚══════════════════════════════════════════════════════════════╝
""".strip()

        self.info_text.configure(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, info)
        self.info_text.configure(state=tk.DISABLED)

        # Update stats
        stats = {
            "Status": (d.status, self.GREEN if d.status == "device" else self.YELLOW),
            "Model": (d.model, self.FG),
            "Brand": (d.brand, self.FG),
            "Android": (d.android_version, self.FG),
            "SDK": (d.sdk_version, self.FG),
            "Battery": (d.battery_level, self.GREEN),
            "Root": ("YES" if d.root_access else "NO", self.GREEN if d.root_access else self.RED),
            "Bootloader": ("UNLOCKED" if d.bootloader_unlocked else "LOCKED", self.RED if d.bootloader_unlocked else self.GREEN),
            "Chipset": (d.chipset, self.FG),
            "IMEI": (d.imei, self.FG),
            "RAM": (d.total_ram, self.FG),
            "Storage": (d.available_storage, self.FG),
            "SELinux": (d.selinux_mode, self.GREEN if d.selinux_mode == "Enforcing" else self.YELLOW),
            "Resolution": (d.screen_resolution, self.FG),
            "Density": (d.screen_density, self.FG),
            "Uptime": (d.uptime, self.FG),
            "Kernel": (d.kernel_version[:30], self.FG),
            "Magisk": ("YES" if d.magisk_installed else "NO", self.GREEN if d.magisk_installed else self.FG2),
            "TWRP": ("YES" if d.twrp_installed else "NO", self.GREEN if d.twrp_installed else self.FG2),
            "WiFi": (d.wifi_ssid, self.CYAN),
        }
        for key, (val, color) in stats.items():
            if key in self.stat_labels:
                self.stat_labels[key].config(text=str(val), fg=color)

    # ─── Callbacks ───

    def _reboot(self, mode):
        if not self._check():
            return
        self._run_async(lambda: self.core.reboot(mode, self.selected_device))

    def _reboot_edl(self):
        if not self._check():
            return
        if not messagebox.askyesno("EDL Mode", "Reboot to Emergency Download Mode (Qualcomm 9008)?"):
            return
        self._run_async(lambda: self.core.fb_edl(self.selected_device))

    def _wifi_connect_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Connect WiFi ADB")
        dialog.geometry("350x180")
        dialog.configure(bg=self.BG2)
        dialog.transient(self.root)

        tk.Label(dialog, text="IP Address:", bg=self.BG2, fg=self.FG, font=("Segoe UI", 10)).pack(pady=(20, 5))
        ip_var = tk.StringVar()
        tk.Entry(dialog, textvariable=ip_var, font=("Consolas", 12), bg=self.BG3, fg=self.FG,
                 relief=tk.FLAT, width=25).pack(pady=5)
        tk.Label(dialog, text="Port: 5555", bg=self.BG2, fg=self.FG2, font=("Segoe UI", 9)).pack()

        def connect():
            ip = ip_var.get().strip()
            if ip:
                self._run_async(lambda: self.core.connect_wifi(ip, 5555, self.selected_device))
                dialog.destroy()

        tk.Button(dialog, text="Connect", command=connect, bg=self.GREEN, fg="#000",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=30, pady=8, cursor="hand2").pack(pady=15)

    def _open_app_dialog(self):
        if not self._check():
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Open App")
        dialog.geometry("400x150")
        dialog.configure(bg=self.BG2)
        dialog.transient(self.root)

        tk.Label(dialog, text="Package or Activity:", bg=self.BG2, fg=self.FG, font=("Segoe UI", 10)).pack(pady=(20, 5))
        pkg_var = tk.StringVar()
        tk.Entry(dialog, textvariable=pkg_var, font=("Consolas", 12), bg=self.BG3, fg=self.FG,
                 relief=tk.FLAT, width=35).pack(pady=5)

        def open_app():
            pkg = pkg_var.get().strip()
            if pkg:
                self._run_async(lambda: self.core.open_app(pkg, device=self.selected_device))
                dialog.destroy()

        tk.Button(dialog, text="Open", command=open_app, bg=self.GREEN, fg="#000",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=30, pady=8, cursor="hand2").pack(pady=10)

    # Shell
    def _exec_shell(self, event):
        if not self._check():
            return
        cmd = self.shell_input.get().strip()
        if not cmd:
            return
        self.command_history.append(cmd)
        self.history_index = len(self.command_history)
        self.shell_input.delete(0, tk.END)
        self._log(f"$ {cmd}", self.shell_out)

        use_root = self.root_var.get()
        self._run_async(lambda: self.core.root_shell(cmd, self.selected_device) if use_root else self.core.shell(cmd, self.selected_device))

    def _hist_prev(self, event):
        if self.history_index > 0:
            self.history_index -= 1
            self.shell_input.delete(0, tk.END)
            self.shell_input.insert(0, self.command_history[self.history_index])

    def _hist_next(self, event):
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.shell_input.delete(0, tk.END)
            self.shell_input.insert(0, self.command_history[self.history_index])
        elif self.history_index == len(self.command_history) - 1:
            self.history_index += 1
            self.shell_input.delete(0, tk.END)

    def _clear_shell(self):
        self.shell_out.configure(state=tk.NORMAL)
        self.shell_out.delete(1.0, tk.END)
        self.shell_out.configure(state=tk.DISABLED)

    # File Manager
    def _fm_list(self):
        if not self._check():
            return
        path = self.fm_path.get()

        def run():
            out = self.core.list_files(path, self.selected_device)
            self.root.after(0, lambda: self._update_fm(out))

        self._run_async(run)

    def _update_fm(self, output):
        for item in self.fm_tree.get_children():
            self.fm_tree.delete(item)
        for line in output.splitlines():
            parts = line.strip().split(None, 7)
            if len(parts) >= 8 and parts[7] not in [".", ".."]:
                self.fm_tree.insert("", tk.END, values=(
                    parts[0], parts[2], parts[4],
                    f"{parts[5]} {parts[6]}", parts[7]
                ))

    def _fm_dblclick(self, event):
        sel = self.fm_tree.selection()
        if not sel:
            return
        item = self.fm_tree.item(sel[0])
        name = item['values'][4]
        current = self.fm_path.get().rstrip("/")
        new_path = f"{current}/{name}"
        if not name.endswith("."):
            self.fm_path.set(new_path)
            self._fm_list()

    def _fm_up(self):
        current = self.fm_path.get().rstrip("/")
        parent = "/".join(current.split("/")[:-1]) or "/"
        self.fm_path.set(parent)
        self._fm_list()

    def _fm_push(self):
        if not self._check():
            return
        local = filedialog.askopenfilename()
        if local:
            self._run_async(lambda: self.core.push(local, self.fm_path.get(), self.selected_device))

    def _fm_pull(self):
        if not self._check():
            return
        sel = self.fm_tree.selection()
        if sel:
            name = self.fm_tree.item(sel[0])['values'][4]
            remote = f"{self.fm_path.get().rstrip('/')}/{name}"
            local = filedialog.askdirectory()
            if local:
                self._run_async(lambda: self.core.pull(remote, local, self.selected_device))

    def _fm_delete(self):
        if not self._check():
            return
        sel = self.fm_tree.selection()
        if sel:
            name = self.fm_tree.item(sel[0])['values'][4]
            path = f"{self.fm_path.get().rstrip('/')}/{name}"
            if messagebox.askyesno("Delete", f"Delete {name}?"):
                self._run_async(lambda: self.core.delete_file(path, self.selected_device))

    def _fm_mkdir(self):
        if not self._check():
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Create Directory")
        dialog.geometry("350x120")
        dialog.configure(bg=self.BG2)

        tk.Label(dialog, text="Directory Name:", bg=self.BG2, fg=self.FG).pack(pady=(20, 5))
        name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=name_var, font=("Consolas", 11), bg=self.BG3, fg=self.FG,
                 relief=tk.FLAT, width=30).pack(pady=5)

        def create():
            name = name_var.get().strip()
            if name:
                path = f"{self.fm_path.get().rstrip('/')}/{name}"
                self._run_async(lambda: self.core.make_dir(path, self.selected_device))
                dialog.destroy()

        tk.Button(dialog, text="Create", command=create, bg=self.GREEN, fg="#000",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=20, pady=5, cursor="hand2").pack(pady=10)

    def _fm_search(self):
        if not self._check():
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Search Files")
        dialog.geometry("400x150")
        dialog.configure(bg=self.BG2)

        tk.Label(dialog, text="Search Pattern (e.g. *.jpg):", bg=self.BG2, fg=self.FG).pack(pady=(20, 5))
        pattern_var = tk.StringVar(value="*.*")
        tk.Entry(dialog, textvariable=pattern_var, font=("Consolas", 11), bg=self.BG3, fg=self.FG,
                 relief=tk.FLAT, width=30).pack(pady=5)

        def search():
            pattern = pattern_var.get().strip()
            if pattern:
                self._run_async(lambda: self.core.search_files(self.fm_path.get(), pattern, self.selected_device))
                dialog.destroy()

        tk.Button(dialog, text="Search", command=search, bg=self.BLUE, fg="#fff",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=20, pady=5, cursor="hand2").pack(pady=10)

    # App Manager
    def _app_refresh(self):
        if not self._check():
            return
        f = self.app_filter.get()
        s = f == "System"
        t = f == "Third-Party"

        def run():
            apps = self.core.get_packages(self.selected_device, s, t)
            self.root.after(0, lambda: self._update_apps(apps))

        self._run_async(run)

    def _update_apps(self, apps):
        for item in self.app_tree.get_children():
            self.app_tree.delete(item)
        for app in apps:
            self.app_tree.insert("", tk.END, values=(app["name"],))

    def _app_install(self):
        if not self._check():
            return
        apk = filedialog.askopenfilename(filetypes=[("APK", "*.apk"), ("All", "*.*")])
        if apk:
            self._run_async(lambda: self.core.install(apk, self.selected_device))

    def _app_uninstall(self):
        if not self._check():
            return
        sel = self.app_tree.selection()
        if sel:
            pkg = self.app_tree.item(sel[0])['values'][0]
            if messagebox.askyesno("Uninstall", f"Uninstall {pkg}?"):
                self._run_async(lambda: self.core.uninstall(pkg, self.selected_device))

    def _app_backup(self):
        if not self._check():
            return
        sel = self.app_tree.selection()
        if sel:
            pkg = self.app_tree.item(sel[0])['values'][0]
            folder = filedialog.askdirectory()
            if folder:
                self._run_async(lambda: self.core.backup_app(pkg, folder, self.selected_device))

    def _app_clear(self):
        if not self._check():
            return
        sel = self.app_tree.selection()
        if sel:
            pkg = self.app_tree.item(sel[0])['values'][0]
            if messagebox.askyesno("Clear", f"Clear all data for {pkg}?"):
                self._run_async(lambda: self.core.clear_app_data(pkg, self.selected_device))

    def _app_force_stop(self):
        if not self._check():
            return
        sel = self.app_tree.selection()
        if sel:
            pkg = self.app_tree.item(sel[0])['values'][0]
            self._run_async(lambda: self.core.force_stop(pkg, self.selected_device))

    def _app_disable(self):
        if not self._check():
            return
        sel = self.app_tree.selection()
        if sel:
            pkg = self.app_tree.item(sel[0])['values'][0]
            if messagebox.askyesno("Disable", f"Disable {pkg}?"):
                self._run_async(lambda: self.core.disable_app(pkg, self.selected_device))

    def _app_enable(self):
        if not self._check():
            return
        sel = self.app_tree.selection()
        if sel:
            pkg = self.app_tree.item(sel[0])['values'][0]
            self._run_async(lambda: self.core.enable_app(pkg, self.selected_device))

    # Flash
    def _browse_flash(self):
        path = filedialog.askopenfilename(filetypes=[("Image", "*.img *.bin *.mbn"), ("All", "*.*")])
        if path:
            self.flash_file.set(path)

    def _browse_sideload(self):
        path = filedialog.askopenfilename(filetypes=[("ZIP", "*.zip"), ("All", "*.*")])
        if path:
            self.sideload_file.set(path)

    def _flash_image(self):
        if not self.selected_device:
            messagebox.showwarning("Fastboot", "Device must be in fastboot mode!")
            return
        part = self.flash_part.get()
        img = self.flash_file.get()
        if not img or not os.path.exists(img):
            messagebox.showerror("Error", "Select a valid image file!")
            return
        if not messagebox.askyesno("DANGER", f"Flash {partition} with {img}?\nThis can BRICK your device!"):
            return
        self._run_async(lambda: self.core.fb_flash(part, img, self.selected_device), lambda r: self._log(r, self.flash_out))

    def _quick_flash(self, partition):
        if not self.selected_device:
            messagebox.showwarning("Fastboot", "Device must be in fastboot mode!")
            return
        img = filedialog.askopenfilename(title=f"Select {partition} image",
                                          filetypes=[("Image", "*.img *.bin *.mbn"), ("All", "*.*")])
        if img:
            if not messagebox.askyesno("DANGER", f"Flash {partition} with {os.path.basename(img)}?"):
                return
            self._run_async(lambda: self.core.fb_flash(partition, img, self.selected_device),
                            lambda r: self._log(r, self.flash_out))

    def _sideload(self):
        zf = self.sideload_file.get()
        if not zf or not os.path.exists(zf):
            messagebox.showerror("Error", "Select a valid ZIP file!")
            return
        self._run_async(lambda: self.core.sideload(zf, self.selected_device),
                        lambda r: self._log(r, self.flash_out))

    def _fb_getvar(self, var):
        if not self.selected_device:
            return
        self._run_async(lambda: self.core.fb_getvar(var, self.selected_device),
                        lambda r: self._log(r, self.flash_out))

    def _fb_erase_dialog(self):
        if not self.selected_device:
            return
        part = tk.simpledialog.askstring("Erase", "Partition name:") if hasattr(tk, 'simpledialog') else None
        if not part:
            part = messagebox.askstring("Erase Partition", "Enter partition name:")
        if part:
            if messagebox.askyesno("DANGER", f"Erase {part}?"):
                self._run_async(lambda: self.core.fb_erase(part, self.selected_device),
                                lambda r: self._log(r, self.flash_out))

    def _fb_format_dialog(self):
        if not self.selected_device:
            return
        part = messagebox.askstring("Format Partition", "Enter partition name:")
        if part:
            if messagebox.askyesno("DANGER", f"Format {part}?"):
                self._run_async(lambda: self.core.fb_format(part, self.selected_device),
                                lambda r: self._log(r, self.flash_out))

    def _fb_boot_dialog(self):
        if not self.selected_device:
            return
        img = filedialog.askopenfilename(title="Select boot image")
        if img:
            self._run_async(lambda: self.core.fb_boot(img, self.selected_device),
                            lambda r: self._log(r, self.flash_out))

    def _fb_update_dialog(self):
        if not self.selected_device:
            return
        zf = filedialog.askopenfilename(title="Select update ZIP", filetypes=[("ZIP", "*.zip")])
        if zf:
            self._run_async(lambda: self.core.fb_update(zf, self.selected_device),
                            lambda r: self._log(r, self.flash_out))

    # Unlock & Root
    def _bl_check(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.fb_getvar("unlocked", self.selected_device),
                        lambda r: self._log(r, self.unlock_out))

    def _bl_oem_unlock(self):
        if not messagebox.askyesno("WARNING", "This WILL WIPE ALL DATA. Continue?"):
            return
        self._run_async(lambda: self.core.fb_oem_unlock(self.selected_device),
                        lambda r: self._log(r, self.unlock_out))

    def _bl_oem_lock(self):
        if not messagebox.askyesno("WARNING", "Relocking may brick custom ROM devices. Continue?"):
            return
        self._run_async(lambda: self.core.fb_oem_lock(self.selected_device),
                        lambda r: self._log(r, self.unlock_out))

    def _bl_flashing_unlock(self):
        if not messagebox.askyesno("WARNING", "This WILL WIPE ALL DATA. Continue?"):
            return
        self._run_async(lambda: self.core.fb_flashing_unlock(self.selected_device),
                        lambda r: self._log(r, self.unlock_out))

    def _bl_flashing_lock(self):
        if not messagebox.askyesno("WARNING", "Relocking may brick custom ROM devices. Continue?"):
            return
        self._run_async(lambda: self.core.fb_flashing_lock(self.selected_device),
                        lambda r: self._log(r, self.unlock_out))

    def _root_check(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.shell("su -c id", self.selected_device),
                        lambda r: self._log(r, self.unlock_out))

    def _root_magisk(self):
        if not self._check():
            return
        apk = filedialog.askopenfilename(filetypes=[("APK", "*.apk")])
        if apk:
            self._run_async(lambda: self.core.push(apk, "/sdcard/magisk.apk", self.selected_device),
                            lambda r: self._log(r, self.unlock_out))

    def _root_remount(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.remount(self.selected_device),
                        lambda r: self._log(r, self.unlock_out))

    def _root_disable_verity(self):
        if not self._check():
            return
        if not messagebox.askyesno("WARNING", "Disable dm-verity? This reduces security."):
            return
        self._run_async(lambda: self.core.disable_verity(self.selected_device),
                        lambda r: self._log(r, self.unlock_out))

    def _root_enable_verity(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.enable_verity(self.selected_device),
                        lambda r: self._log(r, self.unlock_out))

    def _set_selinux(self, mode):
        if not self._check():
            return
        self._run_async(lambda: self.core.set_selinux(mode, self.selected_device),
                        lambda r: self._log(r, self.unlock_out))

    def _bypass(self, method):
        if not self._check():
            return
        if not messagebox.askyesno("Legal", "Do you OWN this device? For educational/forensic use only!"):
            return
        methods = {
            "swipe": lambda: self.core.bypass_swipe(self.selected_device),
            "null_pin": lambda: self.core.bypass_null_pin(self.selected_device),
            "settings_crash": lambda: self.core.bypass_settings_crash(self.selected_device),
            "delete_keys": lambda: self.core.bypass_delete_gesture(self.selected_device),
            "frp": lambda: self.core.bypass_frp_deletion(self.selected_device),
        }
        func = methods.get(method)
        if func:
            self._run_async(func, lambda r: self._log(r, self.unlock_out))

    # Diagnostics
    def _diag_logcat(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_logcat(self.selected_device, 500),
                        lambda r: self._diag_write(r))

    def _diag_dmesg(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_dmesg(self.selected_device),
                        lambda r: self._diag_write(r))

    def _diag_procs(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_processes(self.selected_device),
                        lambda r: self._diag_write(r))

    def _diag_battery(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_battery_stats(self.selected_device),
                        lambda r: self._diag_write(r))

    def _diag_memory(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_memory_info(self.selected_device),
                        lambda r: self._diag_write(r))

    def _diag_cpu(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_cpu_info(self.selected_device),
                        lambda r: self._diag_write(r))

    def _diag_thermal(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_thermal_zones(self.selected_device),
                        lambda r: self._diag_write(r))

    def _diag_disk(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_disk_usage(self.selected_device),
                        lambda r: self._diag_write(r))

    def _diag_mounts(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_mount_info(self.selected_device),
                        lambda r: self._diag_write(r))

    def _diag_kernel(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_kernel_info(self.selected_device),
                        lambda r: self._diag_write(r))

    def _diag_partitions(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_partitions(self.selected_device),
                        lambda r: self._diag_write(r))

    def _diag_services(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_running_services(self.selected_device),
                        lambda r: self._diag_write(r))

    def _diag_current_app(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_current_app(self.selected_device),
                        lambda r: self._diag_write(r))

    def _diag_write(self, text):
        self.diag_out.configure(state=tk.NORMAL)
        self.diag_out.delete(1.0, tk.END)
        self.diag_out.insert(tk.END, text)
        self.diag_out.configure(state=tk.DISABLED)

    def _diag_clear(self):
        self.diag_out.configure(state=tk.NORMAL)
        self.diag_out.delete(1.0, tk.END)
        self.diag_out.configure(state=tk.DISABLED)

    # Network
    def _net_connect(self):
        ip = self.wifi_ip.get().strip()
        if not ip:
            messagebox.showerror("Error", "Enter IP address!")
            return
        self._run_async(lambda: self.core.connect_wifi(ip, int(self.wifi_port.get()), self.selected_device),
                        lambda r: self._net_write(r))

    def _net_disconnect(self):
        self._run_async(lambda: self.core.disconnect_all(),
                        lambda r: self._net_write(r))

    def _net_bt_pair(self):
        addr = self.wifi_ip.get().strip()
        if not addr:
            messagebox.showerror("Error", "Enter BT address!")
            return
        self._run_async(lambda: self.core.bt_pair(addr, self.selected_device),
                        lambda r: self._net_write(r))

    def _net_bt_connect(self):
        addr = self.wifi_ip.get().strip()
        if not addr:
            return
        self._run_async(lambda: self.core.bt_connect(addr, self.selected_device),
                        lambda r: self._net_write(r))

    def _net_forward(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.forward_port(self.fwd_local.get(), self.fwd_remote.get(), self.selected_device),
                        lambda r: self._net_write(r))

    def _net_list_fwd(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.list_forwards(self.selected_device),
                        lambda r: self._net_write(r))

    def _net_reverse(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.reverse_forward(self.fwd_remote.get(), self.fwd_local.get(), self.selected_device),
                        lambda r: self._net_write(r))

    def _net_list_reverse(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.list_reverse_forwards(self.selected_device),
                        lambda r: self._net_write(r))

    def _net_set_proxy(self):
        if not self._check():
            return
        proxy = self.proxy_addr.get().strip()
        if proxy:
            self._run_async(lambda: self.core.set_proxy(proxy, self.selected_device),
                            lambda r: self._net_write(r))

    def _net_rm_proxy(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.remove_proxy(self.selected_device),
                        lambda r: self._net_write(r))

    def _net_write(self, text):
        self.net_out.configure(state=tk.NORMAL)
        self.net_out.delete(1.0, tk.END)
        self.net_out.insert(tk.END, text)
        self.net_out.configure(state=tk.DISABLED)

    # Automation
    def _auto_tap(self):
        if not self._check():
            return
        x, y = int(self.tap_x.get()), int(self.tap_y.get())
        self._run_async(lambda: self.core.tap(x, y, self.selected_device))

    def _auto_longpress(self):
        if not self._check():
            return
        x, y = int(self.tap_x.get()), int(self.tap_y.get())
        self._run_async(lambda: self.core.long_press(x, y, 1000, self.selected_device))

    def _auto_swipe(self):
        if not self._check():
            return
        coords = [int(v.get()) for v in self.swipe_vars]
        self._run_async(lambda: self.core.swipe(*coords, 300, self.selected_device))

    def _auto_text(self):
        if not self._check():
            return
        text = self.input_text_var.get()
        if text:
            self._run_async(lambda: self.core.input_text(text, self.selected_device))

    def _auto_key(self, code):
        if not self._check():
            return
        self._run_async(lambda: self.core.input_key(code, self.selected_device))

    def _auto_monkey(self):
        if not self._check():
            return
        events = int(self.monkey_events.get())
        pkg = self.monkey_pkg.get().strip() or None
        if not messagebox.askyesno("Monkey", f"Run {events} random events?"):
            return
        self._run_async(lambda: self.core.monkey_test(pkg, events, self.selected_device),
                        lambda r: self._log(r, self.auto_out))

    # Dev options
    def _dev_enable(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.enable_dev_options(self.selected_device))

    def _dev_stay_awake(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.enable_stay_awake(self.selected_device))

    def _dev_anim(self, scale):
        if not self._check():
            return
        self._run_async(lambda: self.core.set_animation_scale(scale, self.selected_device))

    def _dev_show_touches(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.enable_show_touches(self.selected_device))

    def _dev_pointer(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.enable_pointer_location(self.selected_device))

    def _dev_mock_loc(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.enable_mock_location(self.selected_device))

    def _dev_reset_dpi(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.reset_dpi(self.selected_device))

    def _dev_reset_res(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.reset_resolution(self.selected_device))

    def _dev_open_url(self):
        if not self._check():
            return
        url = messagebox.askstring("Open URL", "Enter URL:")
        if url:
            self._run_async(lambda: self.core.open_url(url, self.selected_device))

    # Advanced
    def _adv_load_props(self):
        if not self._check():
            return
        def run():
            props = self.core.get_device_props(self.selected_device)
            text = "\n".join(f"{k}={v}" for k, v in sorted(props.items()))
            self.root.after(0, lambda: self._adv_write(text))
        self._run_async(run)

    def _adv_save_props(self):
        text = self.adv_out.get(1.0, tk.END)
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if path:
            with open(path, 'w') as f:
                f.write(text)
            self._log(f"Saved to {path}", self.adv_out)

    def _adv_set_prop(self):
        if not self._check():
            return
        key = self.prop_key.get().strip()
        val = self.prop_val.get().strip()
        if key:
            self._run_async(lambda: self.core.set_prop(key, val, self.selected_device),
                            lambda r: self._adv_write(r))

    def _adv_settings(self, ns):
        if not self._check():
            return
        self._run_async(lambda: self.core.shell(f"settings list {ns}", self.selected_device, timeout=15),
                        lambda r: self._adv_write(r))

    def _adv_dump_ui(self):
        if not self._check():
            return
        folder = filedialog.askdirectory()
        if folder:
            path = os.path.join(folder, "ui_dump.xml")
            self._run_async(lambda: self.core.dump_ui(path, self.selected_device),
                            lambda r: self._adv_write(r))

    def _adv_contacts(self):
        if not self._check():
            return
        folder = filedialog.askdirectory()
        if folder:
            path = os.path.join(folder, "contacts.db")
            self._run_async(lambda: self.core.pull("/data/data/com.android.providers.contacts/databases/contacts2.db", path, self.selected_device),
                            lambda r: self._adv_write(r))

    def _adv_sms(self):
        if not self._check():
            return
        folder = filedialog.askdirectory()
        if folder:
            path = os.path.join(folder, "sms.db")
            self._run_async(lambda: self.core.pull("/data/data/com.android.providers.telephony/databases/mmssms.db", path, self.selected_device),
                            lambda r: self._adv_write(r))

    def _adv_wifi_cfg(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.root_shell("cat /data/misc/wifi/wpa_supplicant.conf", self.selected_device),
                        lambda r: self._adv_write(r))

    def _adv_users(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.list_users(self.selected_device),
                        lambda r: self._adv_write(r))

    def _adv_accounts(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.list_accounts(self.selected_device),
                        lambda r: self._adv_write(r))

    def _adv_open_url(self):
        if not self._check():
            return
        url = messagebox.askstring("Open URL", "Enter URL:")
        if url:
            self._run_async(lambda: self.core.open_url(url, self.selected_device))

    def _adv_factory_reset(self):
        if not self._check():
            return
        if not messagebox.askyesno("DANGER", "FACTORY RESET - ALL DATA WILL BE LOST!\nAre you ABSOLUTELY sure?"):
            return
        if not messagebox.askyesno("FINAL WARNING", "This cannot be undone. Proceed?"):
            return
        self._run_async(lambda: self.core.wipe_data(self.selected_device),
                        lambda r: self._adv_write(r))

    def _adv_wipe_cache(self):
        if not self._check():
            return
        if not messagebox.askyesno("Warning", "Wipe cache partition?"):
            return
        self._run_async(lambda: self.core.wipe_cache(self.selected_device),
                        lambda r: self._adv_write(r))

    def _adv_partition_list(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_partition_list(self.selected_device),
                        lambda r: self._adv_write(r))

    def _adv_partition_info(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.get_partitions(self.selected_device),
                        lambda r: self._adv_write(r))

    def _adv_media_scan(self):
        if not self._check():
            return
        path = messagebox.askstring("Media Scan", "Path to scan (e.g. /sdcard/DCIM):")
        if path:
            self._run_async(lambda: self.core.media_scan(path, self.selected_device),
                            lambda r: self._adv_write(r))

    def _adv_flash_package(self):
        if not self.selected_device:
            messagebox.showwarning("Fastboot", "Device must be in fastboot mode!")
            return
        folder = filedialog.askdirectory(title="Select ROM package folder")
        if not folder:
            return
        # Find .img files
        imgs = {}
        for f in os.listdir(folder):
            if f.endswith(".img"):
                part = os.path.splitext(f)[0]
                imgs[part] = os.path.join(folder, f)
        if not imgs:
            messagebox.showinfo("Info", "No .img files found in selected folder")
            return
        summary = "\n".join(f"  {k}: {os.path.basename(v)}" for k, v in imgs.items())
        if not messagebox.askyesno("DANGER", f"Flash these partitions?\n\n{summary}\n\nTHIS CAN BRICK YOUR DEVICE!"):
            return
        def flash_all():
            results = []
            for part, img in imgs.items():
                result = self.core.fb_flash(part, img, self.selected_device)
                results.append(f"{part}: {result}")
            return "\n".join(results)
        self._run_async(flash_all, lambda r: self._adv_write(r))

    def _adv_flash_skip_reboot(self):
        self._adv_flash_package()

    def _adv_write(self, text):
        self.adv_out.configure(state=tk.NORMAL)
        self.adv_out.delete(1.0, tk.END)
        self.adv_out.insert(tk.END, text)
        self.adv_out.configure(state=tk.DISABLED)

    # Dashboard quick actions
    def _screenshot(self):
        if not self._check():
            return
        folder = filedialog.askdirectory()
        if folder:
            path = os.path.join(folder, f"screenshot_{int(time.time())}.png")
            self._run_async(lambda: self.core.screenshot(path, self.selected_device))

    def _screen_record(self):
        if not self._check():
            return
        folder = filedialog.askdirectory()
        if folder:
            path = os.path.join(folder, f"screenrecord_{int(time.time())}.mp4")
            self._run_async(lambda: self.core.screenrecord(path, 10, self.selected_device))

    def _dump_ui_action(self):
        if not self._check():
            return
        folder = filedialog.askdirectory()
        if folder:
            path = os.path.join(folder, "ui_dump.xml")
            self._run_async(lambda: self.core.dump_ui(path, self.selected_device))

    def _clear_cache(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.shell("pm trim-caches 1G", self.selected_device))

    def _emergency_info(self):
        if not self._check():
            return
        def run():
            info = []
            info.append("=== EMERGENCY DEVICE INFO ===")
            info.append(self.core.shell("getprop ro.product.model", self.selected_device))
            info.append(self.core.shell("getprop ro.build.fingerprint", self.selected_device))
            info.append(self.core.shell("getprop gsm.version.baseband", self.selected_device))
            info.append(self.core.shell("dumpsys telephony.registry", self.selected_device))
            return "\n".join(info)
        self._run_async(run)

    def _wake_screen(self):
        if not self._check():
            return
        self._run_async(lambda: self.core.wake_screen(self.selected_device))


def main():
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    app = ADBExpertGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
