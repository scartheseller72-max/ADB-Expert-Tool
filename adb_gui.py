"""
ADB Expert GUI - Professional Android Debug Bridge Interface
Features: Device Management, Shell, File Manager, App Manager, 
          Flash/Unlock/Root Tools, Diagnostics, Network, Automation
Author: ADB Expert Tool
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
        self.root.title("ADB Expert Tool v2.0 - Professional Android Control Center")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Theme colors - Dark Professional
        self.bg_primary = "#0d1117"
        self.bg_secondary = "#161b22"
        self.bg_tertiary = "#21262d"
        self.fg_primary = "#c9d1d9"
        self.fg_secondary = "#8b949e"
        self.accent = "#58a6ff"
        self.accent_hover = "#79b8ff"
        self.success = "#238636"
        self.warning = "#f0883e"
        self.danger = "#da3633"
        self.info = "#2f81f7"
        
        self.root.configure(bg=self.bg_primary)
        
        # Initialize ADB Core
        adb_path = detect_adb_path()
        self.core = ADBCore(adb_path)
        self.selected_device = None
        self.devices = []
        
        # History and state
        self.command_history = []
        self.history_index = -1
        self.log_buffer = []
        self.automation_recording = False
        self.automation_steps = []
        
        # Setup styles
        self._setup_styles()
        
        # Build UI
        self._build_ui()
        
        # Start refresh timer
        self._refresh_devices()
        self.root.after(5000, self._auto_refresh)
    
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors for ttk widgets
        style.configure("TNotebook", background=self.bg_primary, borderwidth=0)
        style.configure("TNotebook.Tab", 
                       background=self.bg_secondary,
                       foreground=self.fg_primary,
                       padding=[15, 8],
                       font=('Segoe UI', 10, 'bold'))
        style.map("TNotebook.Tab",
                 background=[("selected", self.accent), ("active", self.bg_tertiary)],
                 foreground=[("selected", "#ffffff"), ("active", self.fg_primary)])
        
        style.configure("TFrame", background=self.bg_primary)
        style.configure("TLabel", background=self.bg_primary, foreground=self.fg_primary, font=('Segoe UI', 10))
        style.configure("TButton", 
                       background=self.bg_tertiary, 
                       foreground=self.fg_primary,
                       borderwidth=0,
                       padding=8,
                       font=('Segoe UI', 9))
        style.map("TButton",
                 background=[("active", self.bg_secondary), ("pressed", self.accent)],
                 foreground=[("pressed", "#ffffff")])
        
        style.configure("Accent.TButton",
                       background=self.accent,
                       foreground="#ffffff",
                       font=('Segoe UI', 9, 'bold'))
        style.map("Accent.TButton",
                 background=[("active", self.accent_hover)])
        
        style.configure("Danger.TButton",
                       background=self.danger,
                       foreground="#ffffff",
                       font=('Segoe UI', 9, 'bold'))
        
        style.configure("Success.TButton",
                       background=self.success,
                       foreground="#ffffff",
                       font=('Segoe UI', 9, 'bold'))
        
        style.configure("TLabelframe", background=self.bg_secondary, borderwidth=2, relief="solid")
        style.configure("TLabelframe.Label", background=self.bg_secondary, foreground=self.accent, font=('Segoe UI', 11, 'bold'))
        
        style.configure("Treeview",
                       background=self.bg_secondary,
                       foreground=self.fg_primary,
                       fieldbackground=self.bg_secondary,
                       borderwidth=0,
                       rowheight=25)
        style.configure("Treeview.Heading",
                       background=self.bg_tertiary,
                       foreground=self.fg_primary,
                       font=('Segoe UI', 9, 'bold'))
        style.map("Treeview",
                 background=[("selected", self.accent)])
    
    def _build_ui(self):
        # Top bar - Device selection and status
        self._build_top_bar()
        
        # Notebook (tabs)
        self.notebook = ttk.Notebook(self.root, padding=5)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self._build_dashboard_tab()
        self._build_shell_tab()
        self._build_file_manager_tab()
        self._build_app_manager_tab()
        self._build_flash_tab()
        self._build_unlock_tab()
        self._build_diagnostics_tab()
        self._build_network_tab()
        self._build_automation_tab()
        self._build_advanced_tab()
        
        # Bottom status bar
        self._build_status_bar()
    
    def _build_top_bar(self):
        top_frame = tk.Frame(self.root, bg=self.bg_secondary, height=60)
        top_frame.pack(fill=tk.X, padx=0, pady=0)
        top_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(top_frame, text="ADB EXPERT TOOL", 
                              bg=self.bg_secondary, fg=self.accent,
                              font=('Segoe UI', 14, 'bold'))
        title_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        # Device selector
        tk.Label(top_frame, text="Device:", bg=self.bg_secondary, 
                fg=self.fg_secondary, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(30, 5))
        
        self.device_var = tk.StringVar(value="No device selected")
        self.device_combo = ttk.Combobox(top_frame, textvariable=self.device_var,
                                        state="readonly", width=50, font=('Consolas', 10))
        self.device_combo.pack(side=tk.LEFT, padx=5, pady=12)
        self.device_combo.bind("<<ComboboxSelected>>", self._on_device_selected)
        
        # Refresh button
        refresh_btn = tk.Button(top_frame, text="Refresh", command=self._refresh_devices,
                               bg=self.bg_tertiary, fg=self.fg_primary,
                               activebackground=self.accent, activeforeground="#ffffff",
                               font=('Segoe UI', 9), relief=tk.FLAT, padx=15, cursor="hand2")
        refresh_btn.pack(side=tk.LEFT, padx=5, pady=12)
        
        # Quick actions
        tk.Button(top_frame, text="Reboot", command=lambda: self._quick_reboot(""),
                 bg=self.bg_tertiary, fg=self.fg_primary,
                 activebackground=self.warning, activeforeground="#ffffff",
                 font=('Segoe UI', 9), relief=tk.FLAT, padx=15, cursor="hand2").pack(side=tk.RIGHT, padx=5, pady=12)
        
        tk.Button(top_frame, text="Bootloader", command=lambda: self._quick_reboot("bootloader"),
                 bg=self.bg_tertiary, fg=self.fg_primary,
                 activebackground=self.danger, activeforeground="#ffffff",
                 font=('Segoe UI', 9), relief=tk.FLAT, padx=15, cursor="hand2").pack(side=tk.RIGHT, padx=5, pady=12)
        
        tk.Button(top_frame, text="Recovery", command=lambda: self._quick_reboot("recovery"),
                 bg=self.bg_tertiary, fg=self.fg_primary,
                 activebackground=self.warning, activeforeground="#ffffff",
                 font=('Segoe UI', 9), relief=tk.FLAT, padx=15, cursor="hand2").pack(side=tk.RIGHT, padx=5, pady=12)
    
    def _build_status_bar(self):
        self.status_bar = tk.Label(self.root, text="Ready | ADB Path: " + self.core.adb_path,
                                  bg=self.bg_secondary, fg=self.fg_secondary,
                                  font=('Consolas', 9), anchor=tk.W, padx=10)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    # ==================== DASHBOARD TAB ====================
    def _build_dashboard_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Dashboard ")
        
        # Left panel - Device Info
        left_frame = ttk.LabelFrame(frame, text="Device Information", padding=15)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.device_info_text = scrolledtext.ScrolledText(
            left_frame, wrap=tk.WORD, font=('Consolas', 10),
            bg=self.bg_secondary, fg=self.fg_primary,
            insertbackground=self.fg_primary, relief=tk.FLAT,
            state=tk.DISABLED, padx=10, pady=10
        )
        self.device_info_text.pack(fill=tk.BOTH, expand=True)
        
        # Right panel - Quick Stats & Actions
        right_frame = tk.Frame(frame, bg=self.bg_primary)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Stats cards
        stats_frame = ttk.LabelFrame(right_frame, text="Quick Stats", padding=15)
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.stats_labels = {}
        stats = ["Status", "Model", "Android", "Battery", "Root", "Bootloader"]
        for i, stat in enumerate(stats):
            tk.Label(stats_frame, text=f"{stat}:", font=('Segoe UI', 10, 'bold'),
                    bg=self.bg_secondary, fg=self.accent).grid(row=i, column=0, sticky=tk.W, pady=3)
            lbl = tk.Label(stats_frame, text="N/A", font=('Consolas', 10),
                          bg=self.bg_secondary, fg=self.fg_primary)
            lbl.grid(row=i, column=1, sticky=tk.W, padx=10, pady=3)
            self.stats_labels[stat] = lbl
        
        # Quick Actions
        actions_frame = ttk.LabelFrame(right_frame, text="Quick Actions", padding=15)
        actions_frame.pack(fill=tk.X, pady=10)
        
        btn_data = [
            ("Screenshot", self._take_screenshot, self.info),
            ("Screen Record", self._screen_record, self.info),
            ("Clear Cache", self._clear_cache, self.warning),
            ("Emergency Info", self._emergency_info, self.danger),
        ]
        for i, (text, cmd, color) in enumerate(btn_data):
            tk.Button(actions_frame, text=text, command=cmd,
                     bg=self.bg_tertiary, fg=color,
                     activebackground=color, activeforeground="#ffffff",
                     font=('Segoe UI', 9, 'bold'), relief=tk.FLAT,
                     padx=20, pady=8, cursor="hand2",
                     width=15).grid(row=i//2, column=i%2, padx=5, pady=5)
    
    # ==================== SHELL TAB ====================
    def _build_shell_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Shell ")
        
        # Shell output
        self.shell_output = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=('Consolas', 10),
            bg=self.bg_secondary, fg=self.fg_primary,
            insertbackground=self.fg_primary, relief=tk.FLAT,
            state=tk.DISABLED, padx=10, pady=10
        )
        self.shell_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
        
        # Command input area
        input_frame = tk.Frame(frame, bg=self.bg_primary, height=50)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        input_frame.pack_propagate(False)
        
        tk.Label(input_frame, text="ADB>", bg=self.bg_primary, fg=self.accent,
                font=('Consolas', 11, 'bold')).pack(side=tk.LEFT, padx=(10, 5))
        
        self.shell_input = tk.Entry(input_frame, font=('Consolas', 10),
                                   bg=self.bg_secondary, fg=self.fg_primary,
                                   insertbackground=self.accent, relief=tk.FLAT,
                                   highlightthickness=1, highlightcolor=self.accent,
                                   highlightbackground=self.bg_tertiary)
        self.shell_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=8)
        self.shell_input.bind("<Return>", self._execute_shell)
        self.shell_input.bind("<Up>", self._history_prev)
        self.shell_input.bind("<Down>", self._history_next)
        
        root_cb = tk.Checkbutton(input_frame, text="Root", variable=tk.BooleanVar(),
                                bg=self.bg_primary, fg=self.fg_primary,
                                selectcolor=self.bg_secondary, activebackground=self.bg_primary,
                                activeforeground=self.warning, font=('Segoe UI', 9))
        root_cb.pack(side=tk.LEFT, padx=5)
        self.shell_root_var = tk.BooleanVar(value=False)
        root_cb.config(variable=self.shell_root_var)
        
        tk.Button(input_frame, text="Execute", command=lambda: self._execute_shell(None),
                 bg=self.accent, fg="#ffffff", activebackground=self.accent_hover,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20,
                 cursor="hand2").pack(side=tk.RIGHT, padx=5, pady=8)
        
        tk.Button(input_frame, text="Clear", command=self._clear_shell,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.danger,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=15, cursor="hand2").pack(side=tk.RIGHT, padx=5, pady=8)
    
    # ==================== FILE MANAGER TAB ====================
    def _build_file_manager_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" File Manager ")
        
        # Toolbar
        toolbar = tk.Frame(frame, bg=self.bg_primary, height=40)
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        toolbar.pack_propagate(False)
        
        self.fm_path_var = tk.StringVar(value="/sdcard/")
        tk.Entry(toolbar, textvariable=self.fm_path_var, font=('Consolas', 10),
                bg=self.bg_secondary, fg=self.fg_primary, relief=tk.FLAT,
                highlightthickness=1, highlightcolor=self.accent).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        tk.Button(toolbar, text="List", command=self._fm_list,
                 bg=self.accent, fg="#ffffff", activebackground=self.accent_hover,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15,
                 cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(toolbar, text="Push", command=self._fm_push,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.success,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(toolbar, text="Pull", command=self._fm_pull,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.info,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(toolbar, text="Delete", command=self._fm_delete,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.danger,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        # File list
        columns = ("Permissions", "Owner", "Size", "Name")
        self.fm_tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.fm_tree.heading(col, text=col)
            self.fm_tree.column(col, width=200 if col == "Name" else 100)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.fm_tree.yview)
        self.fm_tree.configure(yscrollcommand=scrollbar.set)
        
        self.fm_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=5)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y, pady=5)
        
        self.fm_tree.bind("<Double-1>", self._fm_double_click)
    
    # ==================== APP MANAGER TAB ====================
    def _build_app_manager_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" App Manager ")
        
        # Toolbar
        toolbar = tk.Frame(frame, bg=self.bg_primary, height=40)
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        toolbar.pack_propagate(False)
        
        self.app_filter = tk.StringVar(value="All")
        tk.OptionMenu(toolbar, self.app_filter, "All", "System", "Third-Party").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(toolbar, text="Refresh List", command=self._refresh_apps,
                 bg=self.accent, fg="#ffffff", activebackground=self.accent_hover,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15,
                 cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(toolbar, text="Install APK", command=self._install_apk,
                 bg=self.success, fg="#ffffff", activebackground=self.success,
                 activeforeground="#ffffff", font=('Segoe UI', 9, 'bold'),
                 relief=tk.FLAT, padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(toolbar, text="Uninstall", command=self._uninstall_app,
                 bg=self.danger, fg="#ffffff", activebackground=self.danger,
                 activeforeground="#ffffff", font=('Segoe UI', 9, 'bold'),
                 relief=tk.FLAT, padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(toolbar, text="Backup", command=self._backup_app,
                 bg=self.info, fg="#ffffff", activebackground=self.info,
                 activeforeground="#ffffff", font=('Segoe UI', 9, 'bold'),
                 relief=tk.FLAT, padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(toolbar, text="Clear Data", command=self._clear_app_data,
                 bg=self.warning, fg="#ffffff", activebackground=self.warning,
                 activeforeground="#ffffff", font=('Segoe UI', 9, 'bold'),
                 relief=tk.FLAT, padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        # App list
        columns = ("Package Name",)
        self.app_tree = ttk.Treeview(frame, columns=columns, show="headings", height=25)
        self.app_tree.heading("Package Name", text="Package Name")
        self.app_tree.column("Package Name", width=600)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.app_tree.yview)
        self.app_tree.configure(yscrollcommand=scrollbar.set)
        
        self.app_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=5)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y, pady=5)
        
        # App info panel
        self.app_info_text = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=('Consolas', 9),
            bg=self.bg_secondary, fg=self.fg_primary, width=50,
            insertbackground=self.fg_primary, relief=tk.FLAT,
            state=tk.DISABLED, padx=10, pady=10
        )
        self.app_info_text.pack(side=tk.RIGHT, fill=tk.BOTH, padx=10, pady=5)
    
    # ==================== FLASH & RECOVERY TAB ====================
    def _build_flash_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Flash & Recovery ")
        
        # Flash section
        flash_frame = ttk.LabelFrame(frame, text="Fastboot Flash", padding=15)
        flash_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(flash_frame, text="Partition:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.flash_partition_var = tk.StringVar(value="boot")
        tk.Entry(flash_frame, textvariable=self.flash_partition_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=20).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(flash_frame, text="Image File:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.flash_file_var = tk.StringVar()
        tk.Entry(flash_frame, textvariable=self.flash_file_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=50).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(flash_frame, text="Browse", command=self._browse_flash_file,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.accent,
                 activeforeground="#ffffff", relief=tk.FLAT, padx=10, cursor="hand2").grid(row=1, column=2, padx=5)
        
        tk.Button(flash_frame, text="FLASH IMAGE", command=self._flash_image,
                 bg=self.danger, fg="#ffffff", activebackground="#ff4444",
                 font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=30, pady=8,
                 cursor="hand2").grid(row=2, column=1, pady=10)
        
        # Sideload section
        sideload_frame = ttk.LabelFrame(frame, text="Recovery Sideload (OTA/ZIP)", padding=15)
        sideload_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(sideload_frame, text="ZIP File:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.sideload_file_var = tk.StringVar()
        tk.Entry(sideload_frame, textvariable=self.sideload_file_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=50).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(sideload_frame, text="Browse", command=self._browse_sideload_file,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.accent,
                 activeforeground="#ffffff", relief=tk.FLAT, padx=10, cursor="hand2").grid(row=0, column=2, padx=5)
        
        tk.Button(sideload_frame, text="SIDELOAD ZIP", command=self._sideload_zip,
                 bg=self.warning, fg="#ffffff", activebackground="#ffaa44",
                 font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=30, pady=8,
                 cursor="hand2").grid(row=1, column=1, pady=10)
        
        # Flash output
        self.flash_output = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=('Consolas', 9),
            bg=self.bg_secondary, fg=self.fg_primary, height=15,
            insertbackground=self.fg_primary, relief=tk.FLAT,
            state=tk.DISABLED, padx=10, pady=10
        )
        self.flash_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # ==================== UNLOCK & ROOT TAB ====================
    def _build_unlock_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Unlock & Root ")
        
        # WARNING banner
        warning_banner = tk.Label(frame, 
                                 text="WARNING: These operations can PERMANENTLY damage your device or void warranty. Proceed with caution!",
                                 bg=self.danger, fg="#ffffff", font=('Segoe UI', 11, 'bold'),
                                 pady=10)
        warning_banner.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        # Bootloader section
        bl_frame = ttk.LabelFrame(frame, text="Bootloader Control", padding=15)
        bl_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(bl_frame, text="Check Unlock Status", command=self._check_bootloader_status,
                 bg=self.info, fg="#ffffff", activebackground=self.info,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=0, column=0, padx=5, pady=5)
        
        tk.Button(bl_frame, text="OEM UNLOCK (Danger)", command=self._oem_unlock,
                 bg=self.danger, fg="#ffffff", activebackground="#ff4444",
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=0, column=1, padx=5, pady=5)
        
        tk.Button(bl_frame, text="OEM LOCK (Relock)", command=self._oem_lock,
                 bg=self.warning, fg="#ffffff", activebackground="#ffaa44",
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=0, column=2, padx=5, pady=5)
        
        # Root tools section
        root_frame = ttk.LabelFrame(frame, text="Root Tools", padding=15)
        root_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(root_frame, text="Check Root Status", command=self._check_root,
                 bg=self.info, fg="#ffffff", activebackground=self.info,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=0, column=0, padx=5, pady=5)
        
        tk.Button(root_frame, text="Push Magisk", command=self._push_magisk,
                 bg=self.success, fg="#ffffff", activebackground=self.success,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=0, column=1, padx=5, pady=5)
        
        tk.Button(root_frame, text="Remount RW", command=self._remount_rw,
                 bg=self.warning, fg="#ffffff", activebackground="#ffaa44",
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=0, column=2, padx=5, pady=5)
        
        tk.Button(root_frame, text="Disable Verity", command=self._disable_verity,
                 bg=self.danger, fg="#ffffff", activebackground="#ff4444",
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=1, column=0, padx=5, pady=5)
        
        tk.Button(root_frame, text="Enable Verity", command=self._enable_verity,
                 bg=self.info, fg="#ffffff", activebackground=self.info,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=1, column=1, padx=5, pady=5)
        
        # Lock bypass section (for owned devices)
        bypass_frame = ttk.LabelFrame(frame, text="Lock Screen Tools (Educational - Own Device Only)", padding=15)
        bypass_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(bypass_frame, text="Swipe Unlock", command=lambda: self._bypass_lock("swipe"),
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.warning,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=20, pady=8, cursor="hand2").grid(row=0, column=0, padx=5, pady=5)
        
        tk.Button(bypass_frame, text="Crash Lock UI", command=lambda: self._bypass_lock("crash"),
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.warning,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=20, pady=8, cursor="hand2").grid(row=0, column=1, padx=5, pady=5)
        
        tk.Button(bypass_frame, text="Null PIN Attempt", command=lambda: self._bypass_lock("null_pin"),
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.warning,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=20, pady=8, cursor="hand2").grid(row=0, column=2, padx=5, pady=5)
        
        # Output
        self.unlock_output = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=('Consolas', 9),
            bg=self.bg_secondary, fg=self.fg_primary, height=15,
            insertbackground=self.fg_primary, relief=tk.FLAT,
            state=tk.DISABLED, padx=10, pady=10
        )
        self.unlock_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # ==================== DIAGNOSTICS TAB ====================
    def _build_diagnostics_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Diagnostics ")
        
        # Controls
        ctrl_frame = tk.Frame(frame, bg=self.bg_primary, height=40)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=5)
        ctrl_frame.pack_propagate(False)
        
        tk.Button(ctrl_frame, text="Logcat", command=self._show_logcat,
                 bg=self.accent, fg="#ffffff", activebackground=self.accent_hover,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=15,
                 cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(ctrl_frame, text="dmesg", command=self._show_dmesg,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.info,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(ctrl_frame, text="Processes", command=self._show_processes,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.info,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(ctrl_frame, text="Battery", command=self._show_battery,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.info,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(ctrl_frame, text="Memory", command=self._show_memory,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.info,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(ctrl_frame, text="CPU Info", command=self._show_cpu,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.info,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(ctrl_frame, text="Thermal", command=self._show_thermal,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.warning,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(ctrl_frame, text="Clear Log", command=self._clear_diagnostics,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.danger,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=15, cursor="hand2").pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Output
        self.diag_output = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=('Consolas', 9),
            bg=self.bg_secondary, fg=self.fg_primary,
            insertbackground=self.fg_primary, relief=tk.FLAT,
            state=tk.DISABLED, padx=10, pady=10
        )
        self.diag_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    # ==================== NETWORK TAB ====================
    def _build_network_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Network ")
        
        # Wireless ADB
        wifi_frame = ttk.LabelFrame(frame, text="Wireless ADB", padding=15)
        wifi_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(wifi_frame, text="IP Address:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.wifi_ip_var = tk.StringVar()
        tk.Entry(wifi_frame, textvariable=self.wifi_ip_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=20).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(wifi_frame, text="Port:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=0, column=2, sticky=tk.W, pady=5)
        self.wifi_port_var = tk.StringVar(value="5555")
        tk.Entry(wifi_frame, textvariable=self.wifi_port_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=8).grid(row=0, column=3, padx=5, pady=5)
        
        tk.Button(wifi_frame, text="Connect", command=self._connect_wifi,
                 bg=self.success, fg="#ffffff", activebackground=self.success,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20,
                 cursor="hand2").grid(row=0, column=4, padx=10, pady=5)
        
        tk.Button(wifi_frame, text="Disconnect", command=self._disconnect_wifi,
                 bg=self.danger, fg="#ffffff", activebackground=self.danger,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20,
                 cursor="hand2").grid(row=0, column=5, padx=10, pady=5)
        
        # Port forwarding
        fwd_frame = ttk.LabelFrame(frame, text="Port Forwarding", padding=15)
        fwd_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(fwd_frame, text="Local:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.fwd_local_var = tk.StringVar(value="tcp:8080")
        tk.Entry(fwd_frame, textvariable=self.fwd_local_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(fwd_frame, text="Remote:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=0, column=2, sticky=tk.W, pady=5)
        self.fwd_remote_var = tk.StringVar(value="tcp:8080")
        tk.Entry(fwd_frame, textvariable=self.fwd_remote_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=15).grid(row=0, column=3, padx=5, pady=5)
        
        tk.Button(fwd_frame, text="Forward", command=self._forward_port,
                 bg=self.accent, fg="#ffffff", activebackground=self.accent_hover,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20,
                 cursor="hand2").grid(row=0, column=4, padx=10, pady=5)
        
        tk.Button(fwd_frame, text="List Forwards", command=self._list_forwards,
                 bg=self.info, fg="#ffffff", activebackground=self.info,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20,
                 cursor="hand2").grid(row=0, column=5, padx=10, pady=5)
        
        # Proxy
        proxy_frame = ttk.LabelFrame(frame, text="Proxy Settings", padding=15)
        proxy_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(proxy_frame, text="Proxy (host:port):", bg=self.bg_secondary, fg=self.fg_primary).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.proxy_var = tk.StringVar()
        tk.Entry(proxy_frame, textvariable=self.proxy_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=30).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Button(proxy_frame, text="Set Proxy", command=self._set_proxy,
                 bg=self.accent, fg="#ffffff", activebackground=self.accent_hover,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20,
                 cursor="hand2").grid(row=0, column=2, padx=10, pady=5)
        
        tk.Button(proxy_frame, text="Remove Proxy", command=self._remove_proxy,
                 bg=self.warning, fg="#ffffff", activebackground="#ffaa44",
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20,
                 cursor="hand2").grid(row=0, column=3, padx=10, pady=5)
        
        # Network info
        self.net_output = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=('Consolas', 9),
            bg=self.bg_secondary, fg=self.fg_primary, height=20,
            insertbackground=self.fg_primary, relief=tk.FLAT,
            state=tk.DISABLED, padx=10, pady=10
        )
        self.net_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # ==================== AUTOMATION TAB ====================
    def _build_automation_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Automation ")
        
        # Touch controls
        touch_frame = ttk.LabelFrame(frame, text="Touch & Input", padding=15)
        touch_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Tap coordinates
        tk.Label(touch_frame, text="X:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.tap_x_var = tk.StringVar(value="500")
        tk.Entry(touch_frame, textvariable=self.tap_x_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=8).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(touch_frame, text="Y:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=0, column=2, sticky=tk.W, pady=5)
        self.tap_y_var = tk.StringVar(value="1000")
        tk.Entry(touch_frame, textvariable=self.tap_y_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=8).grid(row=0, column=3, padx=5, pady=5)
        
        tk.Button(touch_frame, text="Tap", command=self._tap_screen,
                 bg=self.accent, fg="#ffffff", activebackground=self.accent_hover,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20,
                 cursor="hand2").grid(row=0, column=4, padx=10, pady=5)
        
        # Swipe
        tk.Label(touch_frame, text="Swipe:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.swipe_vars = [tk.StringVar(value="300"), tk.StringVar(value="1000"),
                          tk.StringVar(value="300"), tk.StringVar(value="300")]
        labels = ["X1", "Y1", "X2", "Y2"]
        for i, (var, lbl) in enumerate(zip(self.swipe_vars, labels)):
            tk.Label(touch_frame, text=lbl+":", bg=self.bg_secondary, fg=self.fg_primary).grid(row=1, column=i*2+1, sticky=tk.W)
            tk.Entry(touch_frame, textvariable=var, font=('Consolas', 10),
                    bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=6).grid(row=1, column=i*2+2, padx=3)
        
        tk.Button(touch_frame, text="Swipe", command=self._swipe_screen,
                 bg=self.info, fg="#ffffff", activebackground=self.info,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20,
                 cursor="hand2").grid(row=1, column=9, padx=10, pady=5)
        
        # Text input
        tk.Label(touch_frame, text="Text:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.input_text_var = tk.StringVar()
        tk.Entry(touch_frame, textvariable=self.input_text_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=40).grid(row=2, column=1, columnspan=6, padx=5, pady=5, sticky=tk.W)
        
        tk.Button(touch_frame, text="Send Text", command=self._input_text,
                 bg=self.success, fg="#ffffff", activebackground=self.success,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20,
                 cursor="hand2").grid(row=2, column=7, columnspan=3, padx=10, pady=5)
        
        # Key events
        key_frame = ttk.LabelFrame(frame, text="Key Events", padding=15)
        key_frame.pack(fill=tk.X, padx=10, pady=10)
        
        keys = [
            ("HOME", "3"), ("BACK", "4"), ("POWER", "26"), ("VOL+", "24"),
            ("VOL-", "25"), ("MENU", "82"), ("ENTER", "66"), ("DEL", "67")
        ]
        for i, (name, code) in enumerate(keys):
            tk.Button(key_frame, text=name, command=lambda c=code: self._send_key(c),
                     bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.accent,
                     activeforeground="#ffffff", font=('Segoe UI', 9, 'bold'),
                     relief=tk.FLAT, padx=15, pady=8, cursor="hand2",
                     width=8).grid(row=i//4, column=i%4, padx=5, pady=5)
        
        # Macro recording
        macro_frame = ttk.LabelFrame(frame, text="Macro Recording", padding=15)
        macro_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.record_btn = tk.Button(macro_frame, text="Start Recording", command=self._toggle_recording,
                                   bg=self.success, fg="#ffffff", activebackground=self.success,
                                   font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=30, pady=10,
                                   cursor="hand2")
        self.record_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(macro_frame, text="Play Macro", command=self._play_macro,
                 bg=self.accent, fg="#ffffff", activebackground=self.accent_hover,
                 font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=30, pady=10,
                 cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        tk.Button(macro_frame, text="Save Macro", command=self._save_macro,
                 bg=self.info, fg="#ffffff", activebackground=self.info,
                 font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=30, pady=10,
                 cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        tk.Button(macro_frame, text="Load Macro", command=self._load_macro,
                 bg=self.info, fg="#ffffff", activebackground=self.info,
                 font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=30, pady=10,
                 cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        # Monkey test
        monkey_frame = ttk.LabelFrame(frame, text="Monkey Stress Test", padding=15)
        monkey_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(monkey_frame, text="Events:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=0, column=0, sticky=tk.W)
        self.monkey_events_var = tk.StringVar(value="1000")
        tk.Entry(monkey_frame, textvariable=self.monkey_events_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=10).grid(row=0, column=1, padx=5)
        
        tk.Label(monkey_frame, text="Package (optional):", bg=self.bg_secondary, fg=self.fg_primary).grid(row=0, column=2, sticky=tk.W)
        self.monkey_pkg_var = tk.StringVar()
        tk.Entry(monkey_frame, textvariable=self.monkey_pkg_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=30).grid(row=0, column=3, padx=5)
        
        tk.Button(monkey_frame, text="RUN MONKEY", command=self._run_monkey,
                 bg=self.danger, fg="#ffffff", activebackground="#ff4444",
                 font=('Segoe UI', 10, 'bold'), relief=tk.FLAT, padx=30, pady=10,
                 cursor="hand2").grid(row=0, column=4, padx=15)
        
        # Output
        self.auto_output = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=('Consolas', 9),
            bg=self.bg_secondary, fg=self.fg_primary, height=10,
            insertbackground=self.fg_primary, relief=tk.FLAT,
            state=tk.DISABLED, padx=10, pady=10
        )
        self.auto_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # ==================== ADVANCED TAB ====================
    def _build_advanced_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" Advanced ")
        
        # Build.prop editor
        prop_frame = ttk.LabelFrame(frame, text="Build.prop / Properties", padding=15)
        prop_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(prop_frame, text="Load Properties", command=self._load_properties,
                 bg=self.accent, fg="#ffffff", activebackground=self.accent_hover,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=0, column=0, padx=5, pady=5)
        
        tk.Button(prop_frame, text="Save Properties", command=self._save_properties,
                 bg=self.success, fg="#ffffff", activebackground=self.success,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(prop_frame, text="Property:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.prop_key_var = tk.StringVar()
        tk.Entry(prop_frame, textvariable=self.prop_key_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=30).grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(prop_frame, text="Value:", bg=self.bg_secondary, fg=self.fg_primary).grid(row=1, column=2, sticky=tk.W, pady=5)
        self.prop_val_var = tk.StringVar()
        tk.Entry(prop_frame, textvariable=self.prop_val_var, font=('Consolas', 10),
                bg=self.bg_tertiary, fg=self.fg_primary, relief=tk.FLAT, width=30).grid(row=1, column=3, padx=5, pady=5)
        
        tk.Button(prop_frame, text="Set Property", command=self._set_property,
                 bg=self.warning, fg="#ffffff", activebackground="#ffaa44",
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=1, column=4, padx=10, pady=5)
        
        # Partitions
        part_frame = ttk.LabelFrame(frame, text="Partition Information", padding=15)
        part_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(part_frame, text="Show Partitions", command=self._show_partitions,
                 bg=self.accent, fg="#ffffff", activebackground=self.accent_hover,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=0, column=0, padx=5, pady=5)
        
        tk.Button(part_frame, text="Disk Usage", command=self._show_disk_usage,
                 bg=self.info, fg="#ffffff", activebackground=self.info,
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=0, column=1, padx=5, pady=5)
        
        # Expert tools
        expert_frame = ttk.LabelFrame(frame, text="Expert Tools", padding=15)
        expert_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(expert_frame, text="Dump UI Hierarchy", command=self._dump_ui,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.accent,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=20, pady=8, cursor="hand2").grid(row=0, column=0, padx=5, pady=5)
        
        tk.Button(expert_frame, text="Extract Contacts DB", command=self._extract_contacts,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.accent,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=20, pady=8, cursor="hand2").grid(row=0, column=1, padx=5, pady=5)
        
        tk.Button(expert_frame, text="Extract SMS DB", command=self._extract_sms,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.accent,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=20, pady=8, cursor="hand2").grid(row=0, column=2, padx=5, pady=5)
        
        tk.Button(expert_frame, text="WiFi Config", command=self._get_wifi_config,
                 bg=self.bg_tertiary, fg=self.fg_primary, activebackground=self.accent,
                 activeforeground="#ffffff", font=('Segoe UI', 9), relief=tk.FLAT,
                 padx=20, pady=8, cursor="hand2").grid(row=0, column=3, padx=5, pady=5)
        
        tk.Button(expert_frame, text="Factory Reset", command=self._factory_reset,
                 bg=self.danger, fg="#ffffff", activebackground="#ff4444",
                 font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                 cursor="hand2").grid(row=0, column=4, padx=5, pady=5)
        
        # Output
        self.adv_output = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=('Consolas', 9),
            bg=self.bg_secondary, fg=self.fg_primary, height=20,
            insertbackground=self.fg_primary, relief=tk.FLAT,
            state=tk.DISABLED, padx=10, pady=10
        )
        self.adv_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # ==================== CALLBACKS & LOGIC ====================
    
    def _log(self, message: str, tag=""):
        """Log to appropriate output area"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        
        # Determine which output to write to based on current tab
        current_tab = self.notebook.index(self.notebook.select())
        outputs = [
            self.device_info_text, self.shell_output, None, None,
            self.flash_output, self.unlock_output, self.diag_output,
            self.net_output, self.auto_output, self.adv_output
        ]
        target = outputs[current_tab] if current_tab < len(outputs) else None
        
        if target:
            target.configure(state=tk.NORMAL)
            target.insert(tk.END, line, tag)
            target.see(tk.END)
            target.configure(state=tk.DISABLED)
        
        self.status_bar.config(text=f"{message[:80]}...")
    
    def _run_async(self, func, callback=None):
        """Run a function in background thread"""
        def wrapper():
            try:
                result = func()
                if callback:
                    self.root.after(0, lambda: callback(result))
                else:
                    self.root.after(0, lambda: self._log(result))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"Error: {str(e)}", "error"))
        
        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
    
    def _refresh_devices(self):
        try:
            self.devices = self.core.get_devices()
            fastboot_devices = self.core.get_fastboot_devices()
            
            device_list = []
            for d in self.devices:
                label = f"{d.serial} | {d.model} ({d.status})"
                device_list.append(label)
            
            for d in fastboot_devices:
                label = f"{d['serial']} | FASTBOOT MODE"
                device_list.append(label)
            
            if not device_list:
                device_list = ["No devices connected"]
            
            self.device_combo['values'] = device_list
            
            if self.devices and not self.selected_device:
                self.device_combo.current(0)
                self._on_device_selected(None)
            
            self._update_dashboard()
        except Exception as e:
            self.status_bar.config(text=f"Refresh error: {str(e)}")
    
    def _auto_refresh(self):
        self._refresh_devices()
        self.root.after(5000, self._auto_refresh)
    
    def _on_device_selected(self, event):
        selected = self.device_var.get()
        if "No devices" in selected:
            self.selected_device = None
            return
        
        serial = selected.split(" | ")[0]
        self.selected_device = serial
        
        # Find device info
        for d in self.devices:
            if d.serial == serial:
                self._update_dashboard()
                break
        
        self.status_bar.config(text=f"Selected device: {serial}")
    
    def _update_dashboard(self):
        if not self.devices:
            return
        
        device = None
        for d in self.devices:
            if d.serial == self.selected_device:
                device = d
                break
        
        if not device:
            return
        
        # Update info text
        info = f"""
Serial:         {device.serial}
Status:         {device.status}
Model:          {device.model}
Brand:          {device.brand}
Product:        {device.product}
Android Ver:    {device.android_version}
SDK:            {device.sdk_version}
Battery:        {device.battery_level}
IMEI:           {device.imei}
Root Access:    {'Yes' if device.root_access else 'No'}
Bootloader:     {'Unlocked' if device.bootloader_unlocked else 'Locked/Unknown'}
        """
        
        self.device_info_text.configure(state=tk.NORMAL)
        self.device_info_text.delete(1.0, tk.END)
        self.device_info_text.insert(tk.END, info.strip())
        self.device_info_text.configure(state=tk.DISABLED)
        
        # Update stats
        self.stats_labels["Status"].config(text=device.status, fg=self.success if device.status == "device" else self.warning)
        self.stats_labels["Model"].config(text=device.model)
        self.stats_labels["Android"].config(text=device.android_version)
        self.stats_labels["Battery"].config(text=device.battery_level)
        self.stats_labels["Root"].config(text="Yes" if device.root_access else "No", 
                                         fg=self.success if device.root_access else self.danger)
        self.stats_labels["Bootloader"].config(text="Unlocked" if device.bootloader_unlocked else "Locked",
                                                fg=self.danger if device.bootloader_unlocked else self.success)
    
    def _quick_reboot(self, mode):
        if not self._check_device():
            return
        self._run_async(lambda: self.core.reboot(mode, self.selected_device))
    
    def _check_device(self) -> bool:
        if not self.selected_device:
            messagebox.showwarning("No Device", "Please select a device first!")
            return False
        return True
    
    def _execute_shell(self, event):
        if not self._check_device():
            return
        
        command = self.shell_input.get().strip()
        if not command:
            return
        
        self.command_history.append(command)
        self.history_index = len(self.command_history)
        self.shell_input.delete(0, tk.END)
        
        self._log(f">>> {command}", "command")
        
        def run_cmd():
            if self.shell_root_var.get():
                return self.core.root_shell(command, self.selected_device)
            return self.core.shell(command, self.selected_device)
        
        self._run_async(run_cmd)
    
    def _history_prev(self, event):
        if self.history_index > 0:
            self.history_index -= 1
            self.shell_input.delete(0, tk.END)
            self.shell_input.insert(0, self.command_history[self.history_index])
    
    def _history_next(self, event):
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.shell_input.delete(0, tk.END)
            self.shell_input.insert(0, self.command_history[self.history_index])
        elif self.history_index == len(self.command_history) - 1:
            self.history_index += 1
            self.shell_input.delete(0, tk.END)
    
    def _clear_shell(self):
        self.shell_output.configure(state=tk.NORMAL)
        self.shell_output.delete(1.0, tk.END)
        self.shell_output.configure(state=tk.DISABLED)
    
    # File Manager
    def _fm_list(self):
        if not self._check_device():
            return
        path = self.fm_path_var.get()
        
        def run():
            out = self.core.shell(f"ls -la {path}", self.selected_device)
            self.root.after(0, lambda: self._update_fm_list(out))
        
        self._run_async(run)
    
    def _update_fm_list(self, output):
        for item in self.fm_tree.get_children():
            self.fm_tree.delete(item)
        
        for line in output.splitlines():
            parts = line.strip().split(None, 8)
            if len(parts) >= 9 and parts[8] not in [".", ".."]:
                self.fm_tree.insert("", tk.END, values=(
                    parts[0], parts[2], parts[4], parts[8]
                ))
    
    def _fm_double_click(self, event):
        selected = self.fm_tree.selection()
        if not selected:
            return
        
        item = self.fm_tree.item(selected[0])
        name = item['values'][3]
        current = self.fm_path_var.get()
        new_path = os.path.join(current, name).replace("\\", "/")
        
        if name.endswith("/"):
            self.fm_path_var.set(new_path)
            self._fm_list()
    
    def _fm_push(self):
        if not self._check_device():
            return
        local = filedialog.askopenfilename()
        if local:
            remote = self.fm_path_var.get()
            self._run_async(lambda: self.core.push(local, remote, self.selected_device))
    
    def _fm_pull(self):
        if not self._check_device():
            return
        selected = self.fm_tree.selection()
        if selected:
            item = self.fm_tree.item(selected[0])
            name = item['values'][3]
            remote = os.path.join(self.fm_path_var.get(), name).replace("\\", "/")
            local = filedialog.askdirectory()
            if local:
                self._run_async(lambda: self.core.pull(remote, local, self.selected_device))
    
    def _fm_delete(self):
        if not self._check_device():
            return
        selected = self.fm_tree.selection()
        if selected:
            item = self.fm_tree.item(selected[0])
            name = item['values'][3]
            path = os.path.join(self.fm_path_var.get(), name).replace("\\", "/")
            if messagebox.askyesno("Confirm Delete", f"Delete {name}?"):
                self._run_async(lambda: self.core.shell(f"rm -rf {path}", self.selected_device))
    
    # App Manager
    def _refresh_apps(self):
        if not self._check_device():
            return
        
        filter_type = self.app_filter.get()
        system_only = filter_type == "System"
        third_only = filter_type == "Third-Party"
        
        def run():
            apps = self.core.get_packages(self.selected_device, system_only, third_only)
            self.root.after(0, lambda: self._update_app_list(apps))
        
        self._run_async(run)
    
    def _update_app_list(self, apps):
        for item in self.app_tree.get_children():
            self.app_tree.delete(item)
        
        for app in apps:
            self.app_tree.insert("", tk.END, values=(app["name"],))
    
    def _install_apk(self):
        if not self._check_device():
            return
        apk = filedialog.askopenfilename(filetypes=[("APK files", "*.apk")])
        if apk:
            self._run_async(lambda: self.core.install(apk, self.selected_device))
    
    def _uninstall_app(self):
        if not self._check_device():
            return
        selected = self.app_tree.selection()
        if selected:
            pkg = self.app_tree.item(selected[0])['values'][0]
            if messagebox.askyesno("Confirm", f"Uninstall {pkg}?"):
                self._run_async(lambda: self.core.uninstall(pkg, self.selected_device))
    
    def _backup_app(self):
        if not self._check_device():
            return
        selected = self.app_tree.selection()
        if selected:
            pkg = self.app_tree.item(selected[0])['values'][0]
            folder = filedialog.askdirectory()
            if folder:
                self._run_async(lambda: self.core.backup_app(pkg, folder, self.selected_device))
    
    def _clear_app_data(self):
        if not self._check_device():
            return
        selected = self.app_tree.selection()
        if selected:
            pkg = self.app_tree.item(selected[0])['values'][0]
            if messagebox.askyesno("Confirm", f"Clear data for {pkg}?"):
                self._run_async(lambda: self.core.clear_app_data(pkg, self.selected_device))
    
    # Flash & Recovery
    def _browse_flash_file(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.img *.bin"), ("All files", "*.*")])
        if path:
            self.flash_file_var.set(path)
    
    def _browse_sideload_file(self):
        path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")])
        if path:
            self.sideload_file_var.set(path)
    
    def _flash_image(self):
        if not self.selected_device:
            messagebox.showwarning("Warning", "Device must be in fastboot mode!")
            return
        partition = self.flash_partition_var.get()
        image = self.flash_file_var.get()
        if not image or not os.path.exists(image):
            messagebox.showerror("Error", "Please select a valid image file!")
            return
        
        if not messagebox.askyesno("DANGER", f"Flash {partition} with {image}? This can brick your device!"):
            return
        
        def run():
            result = self.core.flash_partition(partition, image, self.selected_device)
            self.root.after(0, lambda: self._log(result))
        
        self._run_async(run)
    
    def _sideload_zip(self):
        zip_file = self.sideload_file_var.get()
        if not zip_file or not os.path.exists(zip_file):
            messagebox.showerror("Error", "Please select a valid ZIP file!")
            return
        
        def run():
            result = self.core.sideload(zip_file, self.selected_device)
            self.root.after(0, lambda: self._log(result))
        
        self._run_async(run)
    
    # Unlock & Root
    def _check_bootloader_status(self):
        if not self._check_device():
            return
        def run():
            out = self.core.shell("getprop ro.boot.flash.locked", self.selected_device)
            self.root.after(0, lambda: self._log(f"Bootloader lock status: {out}"))
        self._run_async(run)
    
    def _oem_unlock(self):
        if not messagebox.askyesno("WARNING", "This will WIPE ALL DATA and unlock the bootloader. Continue?"):
            return
        self._run_async(lambda: self.core.oem_unlock(self.selected_device))
    
    def _oem_lock(self):
        if not messagebox.askyesno("WARNING", "Relocking bootloader may brick custom ROM devices. Continue?"):
            return
        self._run_async(lambda: self.core.oem_lock(self.selected_device))
    
    def _check_root(self):
        if not self._check_device():
            return
        def run():
            out = self.core.shell("su -c id", self.selected_device)
            self.root.after(0, lambda: self._log(f"Root check: {out}"))
        self._run_async(run)
    
    def _push_magisk(self):
        if not self._check_device():
            return
        apk = filedialog.askopenfilename(filetypes=[("APK files", "*.apk")])
        if apk:
            self._run_async(lambda: self.core.push(apk, "/sdcard/magisk.apk", self.selected_device))
    
    def _remount_rw(self):
        if not self._check_device():
            return
        self._run_async(lambda: self.core.remount_system(self.selected_device))
    
    def _disable_verity(self):
        if not self._check_device():
            return
        if not messagebox.askyesno("WARNING", "Disable dm-verity? This reduces security."):
            return
        self._run_async(lambda: self.core.disable_verity(self.selected_device))
    
    def _enable_verity(self):
        if not self._check_device():
            return
        self._run_async(lambda: self.core.enable_verity(self.selected_device))
    
    def _bypass_lock(self, method):
        if not self._check_device():
            return
        if not messagebox.askyesno("Legal Warning", "Do you own this device? These tools are for owned devices only."):
            return
        self._run_async(lambda: self.core.bypass_lock(method, self.selected_device))
    
    # Diagnostics
    def _show_logcat(self):
        if not self._check_device():
            return
        def run():
            out = self.core.get_logcat(self.selected_device, 500)
            self.root.after(0, lambda: self._update_diag(out))
        self._run_async(run)
    
    def _show_dmesg(self):
        if not self._check_device():
            return
        def run():
            out = self.core.get_dmesg(self.selected_device)
            self.root.after(0, lambda: self._update_diag(out))
        self._run_async(run)
    
    def _show_processes(self):
        if not self._check_device():
            return
        def run():
            procs = self.core.get_processes(self.selected_device)
            text = f"{'PID':<8}{'PPID':<8}{'Name':<30}\n{'='*50}\n"
            for p in procs[:50]:
                text += f"{p['pid']:<8}{p['ppid']:<8}{p['name']:<30}\n"
            self.root.after(0, lambda: self._update_diag(text))
        self._run_async(run)
    
    def _show_battery(self):
        if not self._check_device():
            return
        def run():
            stats = self.core.get_battery_stats(self.selected_device)
            text = "\n".join(f"{k}: {v}" for k, v in stats.items())
            self.root.after(0, lambda: self._update_diag(text))
        self._run_async(run)
    
    def _show_memory(self):
        if not self._check_device():
            return
        def run():
            info = self.core.get_memory_info(self.selected_device)
            text = "\n".join(f"{k}: {v}" for k, v in info.items())
            self.root.after(0, lambda: self._update_diag(text))
        self._run_async(run)
    
    def _show_cpu(self):
        if not self._check_device():
            return
        def run():
            info = self.core.get_cpu_info(self.selected_device)
            text = f"CPUs: {len(info['processors'])}\n\n"
            for p in info['processors'][:4]:
                text += f"Processor {p.get('processor', 'N/A')}: {p.get('Hardware', 'N/A')}\n"
            self.root.after(0, lambda: self._update_diag(text))
        self._run_async(run)
    
    def _show_thermal(self):
        if not self._check_device():
            return
        def run():
            zones = self.core.get_thermal_zones(self.selected_device)
            text = f"{'Zone':<8}{'Type':<40}{'Temp (C)':<10}\n{'='*60}\n"
            for z in zones:
                text += f"{z['zone']:<8}{z['type']:<40}{z['temp_celsius']:<10}\n"
            self.root.after(0, lambda: self._update_diag(text))
        self._run_async(run)
    
    def _update_diag(self, text):
        self.diag_output.configure(state=tk.NORMAL)
        self.diag_output.delete(1.0, tk.END)
        self.diag_output.insert(tk.END, text)
        self.diag_output.configure(state=tk.DISABLED)
    
    def _clear_diagnostics(self):
        self.diag_output.configure(state=tk.NORMAL)
        self.diag_output.delete(1.0, tk.END)
        self.diag_output.configure(state=tk.DISABLED)
    
    # Network
    def _connect_wifi(self):
        ip = self.wifi_ip_var.get()
        port = self.wifi_port_var.get()
        if not ip:
            messagebox.showerror("Error", "Enter IP address")
            return
        self._run_async(lambda: self.core.connect_wireless(ip, int(port), self.selected_device))
    
    def _disconnect_wifi(self):
        self._run_async(lambda: self.core.disconnect_wireless())
    
    def _forward_port(self):
        if not self._check_device():
            return
        local = self.fwd_local_var.get()
        remote = self.fwd_remote_var.get()
        self._run_async(lambda: self.core.forward_port(local, remote, self.selected_device))
    
    def _list_forwards(self):
        if not self._check_device():
            return
        self._run_async(lambda: self.core.list_forwards(self.selected_device))
    
    def _set_proxy(self):
        if not self._check_device():
            return
        proxy = self.proxy_var.get()
        self._run_async(lambda: self.core.set_proxy(proxy, self.selected_device))
    
    def _remove_proxy(self):
        if not self._check_device():
            return
        self._run_async(lambda: self.core.remove_proxy(self.selected_device))
    
    # Automation
    def _tap_screen(self):
        if not self._check_device():
            return
        x, y = self.tap_x_var.get(), self.tap_y_var.get()
        self._run_async(lambda: self.core.tap(int(x), int(y), self.selected_device))
    
    def _swipe_screen(self):
        if not self._check_device():
            return
        coords = [int(v.get()) for v in self.swipe_vars]
        self._run_async(lambda: self.core.swipe(*coords, 300, self.selected_device))
    
    def _input_text(self):
        if not self._check_device():
            return
        text = self.input_text_var.get()
        self._run_async(lambda: self.core.input_text(text, self.selected_device))
    
    def _send_key(self, keycode):
        if not self._check_device():
            return
        self._run_async(lambda: self.core.input_key(keycode, self.selected_device))
    
    def _toggle_recording(self):
        self.automation_recording = not self.automation_recording
        if self.automation_recording:
            self.automation_steps = []
            self.record_btn.config(text="Stop Recording", bg=self.danger)
        else:
            self.record_btn.config(text="Start Recording", bg=self.success)
            self._log(f"Recorded {len(self.automation_steps)} steps")
    
    def _play_macro(self):
        if not self.automation_steps:
            messagebox.showinfo("Info", "No macro recorded")
            return
        
        def run():
            for step in self.automation_steps:
                if step["type"] == "tap":
                    self.core.tap(step["x"], step["y"], self.selected_device)
                elif step["type"] == "swipe":
                    self.core.swipe(step["x1"], step["y1"], step["x2"], step["y2"], 300, self.selected_device)
                elif step["type"] == "text":
                    self.core.input_text(step["text"], self.selected_device)
                time.sleep(0.5)
            self.root.after(0, lambda: self._log("Macro playback complete"))
        
        self._run_async(run)
    
    def _save_macro(self):
        if not self.automation_steps:
            return
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if path:
            with open(path, 'w') as f:
                json.dump(self.automation_steps, f)
            self._log(f"Macro saved to {path}")
    
    def _load_macro(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if path:
            with open(path, 'r') as f:
                self.automation_steps = json.load(f)
            self._log(f"Loaded {len(self.automation_steps)} steps")
    
    def _run_monkey(self):
        if not self._check_device():
            return
        events = int(self.monkey_events_var.get())
        pkg = self.monkey_pkg_var.get() or None
        
        if not messagebox.askyesno("Warning", f"Run {events} random events? This may cause unexpected behavior."):
            return
        
        self._run_async(lambda: self.core.monkey_test(pkg, events, self.selected_device))
    
    # Advanced
    def _load_properties(self):
        if not self._check_device():
            return
        def run():
            props = self.core.get_device_props(self.selected_device)
            text = "\n".join(f"{k}={v}" for k, v in sorted(props.items()))
            self.root.after(0, lambda: self._update_adv(text))
        self._run_async(run)
    
    def _save_properties(self):
        text = self.adv_output.get(1.0, tk.END)
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, 'w') as f:
                f.write(text)
            self._log(f"Properties saved to {path}")
    
    def _set_property(self):
        if not self._check_device():
            return
        key = self.prop_key_var.get()
        val = self.prop_val_var.get()
        if key:
            self._run_async(lambda: self.core.set_prop(key, val, self.selected_device))
    
    def _show_partitions(self):
        if not self._check_device():
            return
        def run():
            parts = self.core.get_partitions(self.selected_device)
            text = f"{'Major':<8}{'Minor':<8}{'Blocks':<12}{'Name':<20}\n{'='*50}\n"
            for p in parts:
                text += f"{p['major']:<8}{p['minor']:<8}{p['blocks']:<12}{p['name']:<20}\n"
            self.root.after(0, lambda: self._update_adv(text))
        self._run_async(run)
    
    def _show_disk_usage(self):
        if not self._check_device():
            return
        def run():
            parts = self.core.get_partition_info(self.selected_device)
            text = f"{'Filesystem':<25}{'Size':<10}{'Used':<10}{'Available':<10}{'Use%':<8}{'Mount':<20}\n{'='*80}\n"
            for p in parts:
                text += f"{p['filesystem']:<25}{p['size']:<10}{p['used']:<10}{p['available']:<10}{p['use_percent']:<8}{p['mount']:<20}\n"
            self.root.after(0, lambda: self._update_adv(text))
        self._run_async(run)
    
    def _update_adv(self, text):
        self.adv_output.configure(state=tk.NORMAL)
        self.adv_output.delete(1.0, tk.END)
        self.adv_output.insert(tk.END, text)
        self.adv_output.configure(state=tk.DISABLED)
    
    def _dump_ui(self):
        if not self._check_device():
            return
        folder = filedialog.askdirectory()
        if folder:
            path = os.path.join(folder, "ui_dump.xml")
            self._run_async(lambda: self.core.dump_ui_hierarchy(path, self.selected_device))
    
    def _extract_contacts(self):
        if not self._check_device():
            return
        folder = filedialog.askdirectory()
        if folder:
            path = os.path.join(folder, "contacts.db")
            self._run_async(lambda: self.core.extract_db(
                "/data/data/com.android.providers.contacts/databases/contacts2.db",
                path, self.selected_device
            ))
    
    def _extract_sms(self):
        if not self._check_device():
            return
        folder = filedialog.askdirectory()
        if folder:
            path = os.path.join(folder, "sms.db")
            self._run_async(lambda: self.core.extract_db(
                "/data/data/com.android.providers.telephony/databases/mmssms.db",
                path, self.selected_device
            ))
    
    def _get_wifi_config(self):
        if not self._check_device():
            return
        self._run_async(lambda: self.core.get_wifi_config(self.selected_device))
    
    def _factory_reset(self):
        if not self._check_device():
            return
        if not messagebox.askyesno("DANGER", "This will FACTORY RESET the device. All data will be lost! Continue?"):
            return
        self._run_async(lambda: self.core.wipe_data(self.selected_device))
    
    # Quick dashboard actions
    def _take_screenshot(self):
        if not self._check_device():
            return
        folder = filedialog.askdirectory()
        if folder:
            path = os.path.join(folder, f"screenshot_{int(time.time())}.png")
            self._run_async(lambda: self.core.screenshot(path, self.selected_device))
    
    def _screen_record(self):
        if not self._check_device():
            return
        folder = filedialog.askdirectory()
        if folder:
            path = os.path.join(folder, f"screenrecord_{int(time.time())}.mp4")
            self._run_async(lambda: self.core.screenrecord(path, 10, self.selected_device))
    
    def _clear_cache(self):
        if not self._check_device():
            return
        def run():
            out = self.core.shell("pm trim-caches 1G", self.selected_device)
            return out
        self._run_async(run)
    
    def _emergency_info(self):
        if not self._check_device():
            return
        def run():
            info = []
            info.append("=== EMERGENCY DEVICE INFO ===")
            info.append(self.core.shell("getprop ro.product.model", self.selected_device))
            info.append(self.core.shell("getprop ro.build.fingerprint", self.selected_device))
            info.append(self.core.shell("getprop gsm.version.baseband", self.selected_device))
            info.append(self.core.shell("dumpsys telephony.registry | grep 'mServiceState'", self.selected_device))
            return "\n".join(info)
        self._run_async(run)


def main():
    root = tk.Tk()
    
    # Try to set DPI awareness on Windows for sharper text
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = ADBExpertGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
