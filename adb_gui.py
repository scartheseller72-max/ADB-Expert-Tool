"""
ADB Expert GUI v3.5 - Zero Freeze, Max UX, Professional Android Control Center
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os, sys, threading, time
from datetime import datetime

from adb_utils import ADBCore, ADBError, DeviceInfo, detect_adb_path


# ─── Color Theme ───
C = {
    "bg0": "#010409", "bg1": "#0d1117", "bg2": "#161b22", "bg3": "#21262d",
    "bg4": "#30363d", "fg": "#e6edf3", "fg2": "#8b949e",
    "blue": "#58a6ff", "green": "#3fb950", "yellow": "#d29922",
    "red": "#f85149", "purple": "#bc8cff", "cyan": "#39d353",
    "orange": "#f0883e", "pink": "#ff7b72",
}


class ADBExpertGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ADB EXPERT v3.5")
        self.root.geometry("1500x950")
        self.root.minsize(1300, 850)
        self.root.configure(bg=C["bg0"])

        self.core = None
        self.selected_device: str = None
        self.devices: list[DeviceInfo] = []
        self.fb_devices: list[DeviceInfo] = []
        self.cmd_history: list[str] = []
        self.hist_idx = -1
        self._enrich_thread = None

        try:
            self.core = ADBCore()
        except ADBError as e:
            self._adb_error_dialog(e)
            return

        self._styles()
        self._build()
        self._refresh()

    # ─── ADB ERROR DIALOG ───

    def _adb_error_dialog(self, e: ADBError):
        dlg = tk.Toplevel(self.root)
        dlg.title("ADB Not Found")
        dlg.geometry("620x320")
        dlg.configure(bg=C["bg2"])
        dlg.transient(self.root)
        dlg.grab_set()

        tk.Label(dlg, text="ADB NOT FOUND", font=("Segoe UI", 20, "bold"),
                 bg=C["bg2"], fg=C["red"]).pack(pady=(25, 10))
        tk.Label(dlg, text=str(e), font=("Consolas", 10), bg=C["bg2"], fg=C["fg"],
                 wraplength=580, justify=tk.LEFT).pack(padx=20, pady=5)
        tk.Label(dlg, text="Download: developer.android.com/tools/releases/platform-tools",
                 font=("Consolas", 9), bg=C["bg2"], fg=C["cyan"], cursor="hand2").pack(pady=5)
        tk.Button(dlg, text="Browse for adb.exe",
                  command=lambda: self._browse_adb(dlg),
                  bg=C["bg3"], fg=C["blue"], font=("Segoe UI", 11, "bold"),
                  relief=tk.FLAT, padx=30, pady=10, cursor="hand2").pack(pady=15)

    def _browse_adb(self, dlg):
        path = filedialog.askopenfilename(filetypes=[("ADB", "adb.exe"), ("All", "*.*")])
        if path and os.path.exists(path):
            try:
                self.core = ADBCore(path)
                dlg.destroy()
                self._styles()
                self._build()
                self._refresh()
            except Exception as ex:
                messagebox.showerror("Error", str(ex))

    # ─── STYLES ───

    def _styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TNotebook", background=C["bg0"], borderwidth=0)
        s.configure("TNotebook.Tab", background=C["bg2"], foreground=C["fg"],
                     padding=[22, 12], font=("Segoe UI", 10, "bold"))
        s.map("TNotebook.Tab",
              background=[("selected", C["bg3"]), ("active", C["bg4"])],
              foreground=[("selected", C["blue"]), ("active", C["fg"])])
        s.configure("TFrame", background=C["bg0"])
        s.configure("TLabelframe", background=C["bg2"], borderwidth=2, relief="solid",
                     bordercolor=C["bg4"])
        s.configure("TLabelframe.Label", background=C["bg2"], foreground=C["blue"],
                     font=("Segoe UI", 11, "bold"))
        s.configure("Treeview", background=C["bg2"], foreground=C["fg"],
                     fieldbackground=C["bg2"], borderwidth=0, rowheight=27,
                     font=("Consolas", 9))
        s.configure("Treeview.Heading", background=C["bg3"], foreground=C["fg"],
                     font=("Segoe UI", 9, "bold"))
        s.map("Treeview", background=[("selected", C["blue"])])

    # ─── BUILD UI ───

    def _build(self):
        self._top_bar()
        self.nb = ttk.Notebook(self.root, padding=5)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self._tab_dashboard()
        self._tab_shell()
        self._tab_files()
        self._tab_apps()
        self._tab_flash()
        self._tab_unlock()
        self._tab_diag()
        self._tab_network()
        self._tab_auto()
        self._tab_adv()
        self._status_bar()

    # ─── TOP BAR ───

    def _top_bar(self):
        bar = tk.Frame(self.root, bg=C["bg2"], height=65)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        tk.Label(bar, text="ADB EXPERT", bg=C["bg2"], fg=C["blue"],
                 font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT, padx=15)
        tk.Label(bar, text="v3.5", bg=C["bg2"], fg=C["fg2"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(bar, text="Device:", bg=C["bg2"], fg=C["fg2"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(10, 5))
        self.dev_var = tk.StringVar(value="Scanning...")
        self.dev_cb = ttk.Combobox(bar, textvariable=self.dev_var, state="readonly",
                                    width=55, font=("Consolas", 10))
        self.dev_cb.pack(side=tk.LEFT, padx=5, pady=15)
        self.dev_cb.bind("<<ComboboxSelected>>", self._on_dev_select)

        self._btn(bar, "Refresh", self._refresh, C["blue"], 10).pack(side=tk.LEFT, padx=5)

        # Status dot + label
        self._status_dot = tk.Label(bar, text="●", bg=C["bg2"], fg=C["red"],
                                     font=("Segoe UI", 20))
        self._status_dot.pack(side=tk.RIGHT, padx=(5, 2))
        self._status_label = tk.Label(bar, text="No Device", bg=C["bg2"], fg=C["fg2"],
                                       font=("Segoe UI", 9))
        self._status_label.pack(side=tk.RIGHT, padx=(1, 10))

        for text, cmd, color in [("EDL", self._reboot_edl, C["red"]),
                                   ("Recovery", lambda: self._reboot("recovery"), C["orange"]),
                                   ("Bootloader", lambda: self._reboot("bootloader"), C["orange"]),
                                   ("Reboot", lambda: self._reboot(""), C["yellow"])]:
            self._btn(bar, text, cmd, color).pack(side=tk.RIGHT, padx=3)

    def _btn(self, parent, text, cmd, color, padx=12):
        return tk.Button(parent, text=text, command=cmd,
                         bg=C["bg3"], fg=color, activebackground=color,
                         activeforeground="#fff", font=("Segoe UI", 9, "bold"),
                         relief=tk.FLAT, padx=padx, pady=6, cursor="hand2")

    def _status_bar(self):
        self._sbar = tk.Label(self.root, text=f"Ready | {self.core.adb_path}",
                              bg=C["bg2"], fg=C["fg2"], font=("Consolas", 9),
                              anchor=tk.W, padx=10)
        self._sbar.pack(fill=tk.X, side=tk.BOTTOM)

    # ─── DASHBOARD ───

    def _tab_dashboard(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text=" Dashboard ")

        left = ttk.LabelFrame(f, text="Device Information", padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        self._info_txt = scrolledtext.ScrolledText(left, wrap=tk.WORD, font=("Consolas", 10),
                                                     bg=C["bg2"], fg=C["fg"], insertbackground=C["fg"],
                                                     relief=tk.FLAT, state=tk.DISABLED, padx=12, pady=12)
        self._info_txt.pack(fill=tk.BOTH, expand=True)

        right = tk.Frame(f, bg=C["bg0"])
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        stats = ttk.LabelFrame(right, text="Quick Stats", padding=10)
        stats.pack(fill=tk.X, pady=5)
        self._stats = {}
        keys = ["Status", "Model", "Brand", "Android", "SDK", "Battery",
                "Root", "Bootloader", "Chipset", "IMEI", "RAM", "Storage",
                "SELinux", "Res", "DPI", "Uptime", "Kernel", "Magisk",
                "TWRP", "WiFi", "IP", "Temp"]
        for i, key in enumerate(keys):
            r, c = divmod(i, 3)
            tk.Label(stats, text=f"{key}:", font=("Segoe UI", 9, "bold"),
                     bg=C["bg2"], fg=C["cyan"], anchor=tk.W).grid(row=r, column=c*2, sticky=tk.W, pady=1, padx=(5, 2))
            lbl = tk.Label(stats, text="...", font=("Consolas", 9),
                           bg=C["bg2"], fg=C["fg"], anchor=tk.W)
            lbl.grid(row=r, column=c*2+1, sticky=tk.W, padx=2, pady=1)
            self._stats[key] = lbl

        act = ttk.LabelFrame(right, text="Quick Actions", padding=10)
        act.pack(fill=tk.X, pady=8)
        btns = [
            ("Screenshot", self._scr, C["blue"]),
            ("Record", self._rec, C["blue"]),
            ("Dump UI", self._dump_ui_act, C["purple"]),
            ("Clear Cache", self._clrcache, C["yellow"]),
            ("Emergency", self._emergency, C["red"]),
            ("Wake", self._wake, C["green"]),
            ("Open App...", self._open_app, C["cyan"]),
            ("Reboot", lambda: self._reboot(""), C["orange"]),
            ("Connect WiFi...", self._wifi_dlg, C["green"]),
            ("Disconnect All", self._disconnect_all, C["red"]),
            ("Screenshot", lambda: self._scr(), C["blue"]),
            ("Record 10s", lambda: self._rec(), C["blue"]),
        ]
        for i, (text, cmd, color) in enumerate(btns[:8]):
            tk.Button(act, text=text, command=cmd, bg=C["bg3"], fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
                      padx=10, pady=7, cursor="hand2", width=12).grid(
                row=i//4, column=i%4, padx=3, pady=3)

    # ─── SHELL ───

    def _tab_shell(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text=" Shell ")

        self._sh_out = scrolledtext.ScrolledText(f, wrap=tk.WORD, font=("Consolas", 10),
                                                   bg=C["bg2"], fg=C["green"], insertbackground=C["green"],
                                                   relief=tk.FLAT, state=tk.DISABLED, padx=12, pady=12)
        self._sh_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))

        inp = tk.Frame(f, bg=C["bg0"], height=55)
        inp.pack(fill=tk.X, padx=8, pady=8)
        inp.pack_propagate(False)

        tk.Label(inp, text="$", bg=C["bg0"], fg=C["green"],
                 font=("Consolas", 14, "bold")).pack(side=tk.LEFT, padx=8)

        self._sh_in = tk.Entry(inp, font=("Consolas", 11), bg=C["bg2"], fg=C["fg"],
                                insertbackground=C["green"], relief=tk.FLAT,
                                highlightthickness=1, highlightcolor=C["green"],
                                highlightbackground=C["bg4"])
        self._sh_in.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=8)
        self._sh_in.bind("<Return>", self._sh_exec)
        self._sh_in.bind("<Up>", self._sh_up)
        self._sh_in.bind("<Down>", self._sh_down)

        self._root_var = tk.BooleanVar(value=False)
        tk.Checkbutton(inp, text="ROOT", variable=self._root_var, bg=C["bg0"], fg=C["red"],
                       selectcolor=C["red"], activebackground=C["bg0"],
                       activeforeground=C["red"], font=("Segoe UI", 10, "bold"),
                       indicatoron=False).pack(side=tk.LEFT, padx=5)

        tk.Button(inp, text="EXEC", command=lambda: self._sh_exec(None),
                  bg=C["green"], fg="#000", activebackground="#5ffa7d",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=20, pady=6,
                  cursor="hand2").pack(side=tk.RIGHT, padx=5, pady=8)
        tk.Button(inp, text="CLR", command=self._sh_clr,
                  bg=C["bg3"], fg=C["fg"], activebackground=C["red"],
                  activeforeground="#fff", font=("Segoe UI", 9), relief=tk.FLAT,
                  padx=12, pady=6, cursor="hand2").pack(side=tk.RIGHT, padx=5, pady=8)

    # ─── FILES ───

    def _tab_files(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text=" Files ")

        tb = tk.Frame(f, bg=C["bg0"], height=40)
        tb.pack(fill=tk.X, padx=8, pady=5)
        tb.pack_propagate(False)

        self._fm_path = tk.StringVar(value="/sdcard/")
        tk.Entry(tb, textvariable=self._fm_path, font=("Consolas", 10),
                 bg=C["bg2"], fg=C["fg"], relief=tk.FLAT,
                 highlightthickness=1, highlightcolor=C["blue"]).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        for text, cmd, color in [("List", self._fm_list, C["blue"]), ("Push", self._fm_push, C["green"]),
                                   ("Pull", self._fm_pull, C["cyan"]), ("Del", self._fm_del, C["red"]),
                                   ("Mkdir", self._fm_mkdir, C["yellow"]), ("Find", self._fm_find, C["purple"]),
                                   ("Up", self._fm_up, C["fg2"])]:
            tk.Button(tb, text=text, command=cmd, bg=C["bg3"], fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
                      padx=10, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=2, pady=5)

        cols = ("Perms", "Owner", "Size", "Date", "Name")
        self._fm_tree = ttk.Treeview(f, columns=cols, show="headings", height=20)
        widths = [100, 80, 80, 110, 420]
        for c, w in zip(cols, widths):
            self._fm_tree.heading(c, text=c)
            self._fm_tree.column(c, width=w)
        sb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self._fm_tree.yview)
        self._fm_tree.configure(yscrollcommand=sb.set)
        self._fm_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=5)
        sb.pack(side=tk.LEFT, fill=tk.Y, pady=5)
        self._fm_tree.bind("<Double-1>", self._fm_dbl)

    # ─── APPS ───

    def _tab_apps(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text=" Apps ")

        tb = tk.Frame(f, bg=C["bg0"], height=40)
        tb.pack(fill=tk.X, padx=8, pady=5)
        tb.pack_propagate(False)

        self._app_filter = tk.StringVar(value="All")
        tk.OptionMenu(tb, self._app_filter, "All", "System", "Third-Party").pack(side=tk.LEFT, padx=5)

        for text, cmd, color in [
            ("Refresh", self._app_ref, C["blue"]), ("Install", self._app_inst, C["green"]),
            ("Uninstall", self._app_uninst, C["red"]), ("Backup", self._app_bak, C["cyan"]),
            ("Clear Data", self._app_clr, C["yellow"]), ("ForceStop", self._app_fstop, C["orange"]),
            ("Disable", self._app_dis, C["red"]), ("Enable", self._app_en, C["green"]),
        ]:
            tk.Button(tb, text=text, command=cmd, bg=C["bg3"], fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
                      padx=10, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=2, pady=5)

        cols = ("Package",)
        self._app_tree = ttk.Treeview(f, columns=cols, show="headings", height=22)
        self._app_tree.heading("Package", text="Package Name")
        self._app_tree.column("Package", width=480)
        sb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self._app_tree.yview)
        self._app_tree.configure(yscrollcommand=sb.set)
        self._app_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=5)
        sb.pack(side=tk.LEFT, fill=tk.Y, pady=5)

        self._app_info = scrolledtext.ScrolledText(f, wrap=tk.WORD, font=("Consolas", 9),
                                                     bg=C["bg2"], fg=C["fg"], width=45,
                                                     insertbackground=C["fg"], relief=tk.FLAT,
                                                     state=tk.DISABLED, padx=10, pady=10)
        self._app_info.pack(side=tk.RIGHT, fill=tk.BOTH, padx=8, pady=5)

    # ─── FLASH ───

    def _tab_flash(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text=" Flash ")

        tk.Label(f, text="DANGER ZONE - Flash & Sideload",
                 bg=C["red"], fg="#fff", font=("Segoe UI", 12, "bold"), pady=8).pack(fill=tk.X, padx=8, pady=(8, 0))

        fl = ttk.LabelFrame(f, text="Fastboot Flash", padding=10)
        fl.pack(fill=tk.X, padx=8, pady=5)

        tk.Label(fl, text="Partition:", bg=C["bg2"], fg=C["fg"]).grid(row=0, column=0, sticky=tk.W, pady=3)
        self._fl_part = tk.StringVar(value="boot")
        tk.Entry(fl, textvariable=self._fl_part, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=15).grid(row=0, column=1, padx=5, pady=3)

        tk.Label(fl, text="Image:", bg=C["bg2"], fg=C["fg"]).grid(row=0, column=2, sticky=tk.W, pady=3, padx=(15, 0))
        self._fl_file = tk.StringVar()
        tk.Entry(fl, textvariable=self._fl_file, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=45).grid(row=0, column=3, padx=5, pady=3)
        tk.Button(fl, text="Browse", command=self._browse_fl,
                  bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, padx=10, cursor="hand2").grid(row=0, column=4, padx=5)
        tk.Button(fl, text="FLASH", command=self._flash,
                  bg=C["red"], fg="#fff", activebackground="#ff6b6b",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=25, pady=6,
                  cursor="hand2").grid(row=0, column=5, padx=10)

        # Quick partitions
        qf = ttk.LabelFrame(f, text="Quick Flash (Fastboot Required)", padding=8)
        qf.pack(fill=tk.X, padx=8, pady=5)
        parts = ["boot", "recovery", "system", "vendor", "vbmeta", "dtbo",
                 "userdata", "cache", "persist", "modem", "super", "product"]
        for i, part in enumerate(parts):
            tk.Button(qf, text=part, command=lambda p=part: self._qflash(p),
                      bg=C["bg3"], fg=C["orange"], activebackground=C["orange"],
                      activeforeground="#fff", font=("Segoe UI", 9, "bold"),
                      relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
                      width=10).grid(row=i//6, column=i%6, padx=2, pady=2)

        # Sideload
        sl = ttk.LabelFrame(f, text="Sideload (Recovery Required)", padding=10)
        sl.pack(fill=tk.X, padx=8, pady=5)
        tk.Label(sl, text="ZIP:", bg=C["bg2"], fg=C["fg"]).grid(row=0, column=0, sticky=tk.W)
        self._sl_file = tk.StringVar()
        tk.Entry(sl, textvariable=self._sl_file, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=55).grid(row=0, column=1, padx=5)
        tk.Button(sl, text="Browse", command=self._browse_sl,
                  bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, padx=10, cursor="hand2").grid(row=0, column=2, padx=5)
        tk.Button(sl, text="SIDELOAD", command=self._sideload,
                  bg=C["yellow"], fg="#000", activebackground="#ffd966",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=25, pady=6,
                  cursor="hand2").grid(row=0, column=3, padx=10)

        # Fastboot tools
        fb = ttk.LabelFrame(f, text="Fastboot Tools", padding=8)
        fb.pack(fill=tk.X, padx=8, pady=5)
        fbt = [("Getvar All", lambda: self._fbv("all")),
               ("Active Slot", lambda: self._fbv("current-slot")),
               ("Partitions", lambda: self._fbv("partition-type:all")),
               ("Erase", self._fb_erase), ("Format", self._fb_format),
               ("Boot Image", self._fb_boot), ("Update ZIP", self._fb_update)]
        for i, (text, cmd) in enumerate(fbt):
            tk.Button(fb, text=text, command=cmd, bg=C["bg3"], fg=C["cyan"],
                      activebackground=C["cyan"], activeforeground="#000",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
                      padx=12, pady=4, cursor="hand2").grid(row=0, column=i, padx=2, pady=2)

        self._fl_out = scrolledtext.ScrolledText(f, wrap=tk.WORD, font=("Consolas", 9),
                                                   bg=C["bg2"], fg=C["fg"], height=8,
                                                   insertbackground=C["fg"], relief=tk.FLAT,
                                                   state=tk.DISABLED, padx=10, pady=10)
        self._fl_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)

    # ─── UNLOCK & ROOT ───

    def _tab_unlock(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text=" Unlock & Root ")

        tk.Label(f, text="EXPERT ZONE - Can permanently damage device!",
                 bg=C["red"], fg="#fff", font=("Segoe UI", 12, "bold"), pady=10).pack(fill=tk.X, padx=8, pady=(8, 0))

        # Bootloader
        bl = ttk.LabelFrame(f, text="Bootloader Control", padding=10)
        bl.pack(fill=tk.X, padx=8, pady=5)
        for i, (text, cmd, color) in enumerate([
            ("Check", self._bl_chk, C["blue"]),
            ("OEM Unlock (Old)", self._bl_ounlock, C["red"]),
            ("OEM Lock", self._bl_olock, C["yellow"]),
            ("Flashing Unlock (New)", self._bl_funlock, C["red"]),
            ("Flashing Lock", self._bl_flock, C["yellow"]),
        ]):
            tk.Button(bl, text=text, command=cmd, bg=C["bg3"], fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
                      padx=18, pady=6, cursor="hand2").grid(row=0, column=i, padx=3, pady=3)

        # Root
        rt = ttk.LabelFrame(f, text="Root & SE", padding=10)
        rt.pack(fill=tk.X, padx=8, pady=5)
        for i, (text, cmd, color) in enumerate([
            ("Check Root", self._rt_chk, C["blue"]),
            ("Push Magisk", self._rt_magisk, C["green"]),
            ("Remount RW", self._rt_remount, C["orange"]),
            ("Disable Verity", self._rt_dverity, C["red"]),
            ("Enable Verity", self._rt_everity, C["green"]),
            ("SELinux Enforcing", lambda: self._selinux("enforcing"), C["blue"]),
            ("SELinux Permissive", lambda: self._selinux("permissive"), C["yellow"]),
        ]):
            tk.Button(rt, text=text, command=cmd, bg=C["bg3"], fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
                      padx=12, pady=6, cursor="hand2").grid(row=i//4, column=i%4, padx=3, pady=3)

        # Bypass
        bp = ttk.LabelFrame(f, text="Lock Bypass (OWN DEVICE ONLY)", padding=10)
        bp.pack(fill=tk.X, padx=8, pady=5)
        for i, (text, method, color) in enumerate([
            ("Swipe", "swipe", C["blue"]), ("Null PIN", "null_pin", C["yellow"]),
            ("Settings Crash", "settings", C["orange"]),
            ("Delete Keys", "delete_keys", C["red"]),
            ("FRP Delete", "frp", C["red"]),
        ]):
            tk.Button(bp, text=text, command=lambda m=method: self._bypass(m),
                      bg=C["bg3"], fg=color, activebackground=color,
                      activeforeground="#fff", font=("Segoe UI", 9, "bold"),
                      relief=tk.FLAT, padx=15, pady=6, cursor="hand2").grid(
                row=0, column=i, padx=3, pady=3)

        self._ul_out = scrolledtext.ScrolledText(f, wrap=tk.WORD, font=("Consolas", 9),
                                                   bg=C["bg2"], fg=C["fg"], height=10,
                                                   insertbackground=C["fg"], relief=tk.FLAT,
                                                   state=tk.DISABLED, padx=10, pady=10)
        self._ul_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)

    # ─── DIAGNOSTICS ───

    def _tab_diag(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text=" Diagnostics ")

        ctrl = tk.Frame(f, bg=C["bg0"], height=35)
        ctrl.pack(fill=tk.X, padx=8, pady=5)
        ctrl.pack_propagate(False)
        for text, cmd, color in [
            ("Logcat", self._d_logcat, C["blue"]), ("dmesg", self._d_dmesg, C["cyan"]),
            ("Procs", self._d_procs, C["green"]), ("Battery", self._d_bat, C["yellow"]),
            ("Memory", self._d_mem, C["purple"]), ("CPU", self._d_cpu, C["orange"]),
            ("Thermal", self._d_thermal, C["red"]), ("Disk", self._d_disk, C["cyan"]),
            ("Mounts", self._d_mounts, C["fg2"]), ("Kernel", self._d_kern, C["blue"]),
            ("Parts", self._d_parts, C["green"]), ("Services", self._d_svc, C["purple"]),
            ("Curr App", self._d_cur, C["yellow"]), ("Clear", self._d_clr, C["red"]),
        ]:
            tk.Button(ctrl, text=text, command=cmd, bg=C["bg3"], fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                      padx=8, pady=3, cursor="hand2").pack(side=tk.LEFT, padx=1, pady=3)

        self._d_out = scrolledtext.ScrolledText(f, wrap=tk.WORD, font=("Consolas", 9),
                                                  bg=C["bg2"], fg=C["fg"],
                                                  insertbackground=C["fg"], relief=tk.FLAT,
                                                  state=tk.DISABLED, padx=10, pady=10)
        self._d_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)

    # ─── NETWORK ───

    def _tab_network(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text=" Network ")

        # WiFi
        wf = ttk.LabelFrame(f, text="Wireless ADB & Bluetooth", padding=10)
        wf.pack(fill=tk.X, padx=8, pady=5)

        tk.Label(wf, text="IP/Addr:", bg=C["bg2"], fg=C["fg"], font=("Segoe UI", 10)).grid(row=0, column=0, sticky=tk.W, pady=3)
        self._wifi_ip = tk.StringVar()
        tk.Entry(wf, textvariable=self._wifi_ip, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=18).grid(row=0, column=1, padx=3, pady=3)
        tk.Label(wf, text="Port:", bg=C["bg2"], fg=C["fg"]).grid(row=0, column=2, sticky=tk.W, pady=3, padx=(10, 0))
        self._wifi_port = tk.StringVar(value="5555")
        tk.Entry(wf, textvariable=self._wifi_port, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=6).grid(row=0, column=3, padx=3, pady=3)

        for i, (text, cmd, color) in enumerate([
            ("WiFi Connect", self._net_connect, C["green"]),
            ("Disconnect All", self._net_disconn, C["red"]),
            ("BT Pair", self._net_btp, C["purple"]),
            ("BT Connect", self._net_btc, C["cyan"]),
        ]):
            tk.Button(wf, text=text, command=cmd, bg=C["bg3"], fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                      padx=12, pady=4, cursor="hand2").grid(row=1, column=i, padx=2, pady=5)

        # Forwarding
        fw = ttk.LabelFrame(f, text="Port Forwarding", padding=10)
        fw.pack(fill=tk.X, padx=8, pady=5)

        tk.Label(fw, text="Local:", bg=C["bg2"], fg=C["fg"]).grid(row=0, column=0, sticky=tk.W, pady=3)
        self._fwd_l = tk.StringVar(value="tcp:8080")
        tk.Entry(fw, textvariable=self._fwd_l, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=14).grid(row=0, column=1, padx=3, pady=3)
        tk.Label(fw, text="Remote:", bg=C["bg2"], fg=C["fg"]).grid(row=0, column=2, sticky=tk.W, pady=3, padx=(10, 0))
        self._fwd_r = tk.StringVar(value="tcp:8080")
        tk.Entry(fw, textvariable=self._fwd_r, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=14).grid(row=0, column=3, padx=3, pady=3)

        for i, (text, cmd, color) in enumerate([
            ("Forward", self._net_fwd, C["blue"]),
            ("List Fwd", self._net_lfwd, C["blue"]),
            ("Reverse", self._net_rev, C["purple"]),
            ("List Rev", self._net_lrev, C["purple"]),
        ]):
            tk.Button(fw, text=text, command=cmd, bg=C["bg3"], fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                      padx=12, pady=4, cursor="hand2").grid(row=1, column=i, padx=2, pady=5)

        # Proxy
        px = ttk.LabelFrame(f, text="Proxy", padding=10)
        px.pack(fill=tk.X, padx=8, pady=5)

        tk.Label(px, text="Proxy (host:port):", bg=C["bg2"], fg=C["fg"]).grid(row=0, column=0, sticky=tk.W, pady=3)
        self._proxy = tk.StringVar()
        tk.Entry(px, textvariable=self._proxy, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=35).grid(row=0, column=1, padx=3, sticky=tk.W)
        tk.Button(px, text="Set", command=self._net_setpx, bg=C["bg3"], fg=C["green"],
                  activebackground=C["green"], activeforeground="#000",
                  font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=4,
                  cursor="hand2").grid(row=0, column=2, padx=5, pady=3)
        tk.Button(px, text="Remove", command=self._net_rmpx, bg=C["bg3"], fg=C["red"],
                  activebackground=C["red"], activeforeground="#fff",
                  font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=4,
                  cursor="hand2").grid(row=0, column=3, padx=5, pady=3)

        self._net_out = scrolledtext.ScrolledText(f, wrap=tk.WORD, font=("Consolas", 9),
                                                    bg=C["bg2"], fg=C["fg"], height=12,
                                                    insertbackground=C["fg"], relief=tk.FLAT,
                                                    state=tk.DISABLED, padx=10, pady=10)
        self._net_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)

    # ─── AUTOMATION ───

    def _tab_auto(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text=" Automation ")

        # Touch
        tc = ttk.LabelFrame(f, text="Touch & Input", padding=10)
        tc.pack(fill=tk.X, padx=8, pady=5)

        tk.Label(tc, text="X:", bg=C["bg2"], fg=C["fg"]).grid(row=0, column=0, sticky=tk.W, pady=3)
        self._tap_x = tk.StringVar(value="540")
        tk.Entry(tc, textvariable=self._tap_x, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=6).grid(row=0, column=1, padx=2)
        tk.Label(tc, text="Y:", bg=C["bg2"], fg=C["fg"]).grid(row=0, column=2, sticky=tk.W, pady=3)
        self._tap_y = tk.StringVar(value="960")
        tk.Entry(tc, textvariable=self._tap_y, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=6).grid(row=0, column=3, padx=2)

        for text, cmd in [("Tap", self._a_tap), ("LongPress", self._a_lpress)]:
            tk.Button(tc, text=text, command=cmd, bg=C["bg3"], fg=C["blue"],
                      activebackground=C["blue"], activeforeground="#000",
                      font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                      padx=12, pady=4, cursor="hand2").grid(
                row=0, column=4 if text == "Tap" else 5, padx=2)

        # Swipe
        tk.Label(tc, text="X1 Y1 X2 Y2:", bg=C["bg2"], fg=C["fg"]).grid(row=1, column=0, sticky=tk.W, pady=3)
        self._sw_vars = [tk.StringVar(value=v) for v in ["540", "1800", "540", "600"]]
        for i, var in enumerate(self._sw_vars):
            tk.Entry(tc, textvariable=var, font=("Consolas", 10),
                     bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=5).grid(row=1, column=i+1, padx=1)
        tk.Button(tc, text="Swipe", command=self._a_swipe, bg=C["bg3"], fg=C["cyan"],
                  activebackground=C["cyan"], activeforeground="#000",
                  font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                  padx=12, pady=4, cursor="hand2").grid(row=1, column=5, padx=2)

        # Text
        tk.Label(tc, text="Text:", bg=C["bg2"], fg=C["fg"]).grid(row=2, column=0, sticky=tk.W, pady=3)
        self._in_text = tk.StringVar()
        tk.Entry(tc, textvariable=self._in_text, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=40).grid(
            row=2, column=1, columnspan=4, padx=2, sticky=tk.W)
        tk.Button(tc, text="Send", command=self._a_text, bg=C["bg3"], fg=C["green"],
                  activebackground=C["green"], activeforeground="#000",
                  font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                  padx=15, pady=4, cursor="hand2").grid(row=2, column=5, padx=2)

        # Keys
        ky = ttk.LabelFrame(f, text="Key Events", padding=8)
        ky.pack(fill=tk.X, padx=8, pady=5)
        klist = [
            ("HOME", "3"), ("BACK", "4"), ("POWER", "26"), ("VOL+", "24"),
            ("VOL-", "25"), ("MENU", "82"), ("ENTER", "66"), ("DEL", "67"),
            ("TAB", "61"), ("ESC", "111"), ("CAMERA", "27"), ("MUTE", "164"),
            ("BRI+", "221"), ("BRI-", "220"), ("PLAY", "126"), ("PAUSE", "127"),
            ("NEXT", "87"), ("PREV", "88"),
        ]
        for i, (name, code) in enumerate(klist):
            tk.Button(ky, text=name, command=lambda c=code: self._a_key(c),
                      bg=C["bg3"], fg=C["fg"], activebackground=C["blue"],
                      activeforeground="#fff", font=("Segoe UI", 8, "bold"),
                      relief=tk.FLAT, padx=6, pady=3, cursor="hand2",
                      width=7).grid(row=i//9, column=i%9, padx=1, pady=1)

        # Monkey + Dev
        mk = ttk.LabelFrame(f, text="Monkey Test", padding=8)
        mk.pack(fill=tk.X, padx=8, pady=5)
        tk.Label(mk, text="Events:", bg=C["bg2"], fg=C["fg"]).grid(row=0, column=0, sticky=tk.W)
        self._mk_ev = tk.StringVar(value="5000")
        tk.Entry(mk, textvariable=self._mk_ev, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=8).grid(row=0, column=1, padx=3)
        tk.Label(mk, text="Pkg:", bg=C["bg2"], fg=C["fg"]).grid(row=0, column=2, sticky=tk.W)
        self._mk_pkg = tk.StringVar()
        tk.Entry(mk, textvariable=self._mk_pkg, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=25).grid(row=0, column=3, padx=3)
        tk.Button(mk, text="RUN MONKEY", command=self._a_monkey,
                  bg=C["red"], fg="#fff", activebackground="#ff6b6b",
                  font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=20, pady=6,
                  cursor="hand2").grid(row=0, column=4, padx=10)

        # Dev options
        dv = ttk.LabelFrame(f, text="Dev Options", padding=8)
        dv.pack(fill=tk.X, padx=8, pady=5)
        dbtns = [
            ("Enable Dev", self._dv_en, C["green"]), ("Stay Awake", self._dv_sw, C["blue"]),
            ("Anim OFF", lambda: self._dv_anim(0), C["yellow"]), ("Show Touch", self._dv_st, C["cyan"]),
            ("Pointer", self._dv_ptr, C["purple"]), ("Mock Loc", self._dv_ml, C["orange"]),
            ("Reset DPI", self._dv_rdpi, C["blue"]), ("Reset Res", self._dv_rres, C["blue"]),
            ("Open URL...", self._dv_url, C["green"]),
        ]
        for i, (text, cmd, color) in enumerate(dbtns):
            tk.Button(dv, text=text, command=cmd, bg=C["bg3"], fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                      padx=10, pady=4, cursor="hand2").grid(row=0, column=i, padx=2, pady=2)

        self._a_out = scrolledtext.ScrolledText(f, wrap=tk.WORD, font=("Consolas", 9),
                                                  bg=C["bg2"], fg=C["fg"], height=6,
                                                  insertbackground=C["fg"], relief=tk.FLAT,
                                                  state=tk.DISABLED, padx=10, pady=10)
        self._a_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)

    # ─── ADVANCED ───

    def _tab_adv(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text=" Advanced ")

        # Props
        pr = ttk.LabelFrame(f, text="Build.prop Editor", padding=10)
        pr.pack(fill=tk.X, padx=8, pady=5)
        for i, (text, cmd, color) in enumerate([
            ("Load Props", self._ad_load, C["blue"]),
            ("Save Props", self._ad_save, C["green"]),
        ]):
            tk.Button(pr, text=text, command=cmd, bg=C["bg3"], fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
                      padx=15, pady=6, cursor="hand2").grid(row=0, column=i, padx=5, pady=3)

        tk.Label(pr, text="Prop:", bg=C["bg2"], fg=C["fg"]).grid(row=1, column=0, sticky=tk.W, pady=3)
        self._ad_key = tk.StringVar()
        tk.Entry(pr, textvariable=self._ad_key, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=25).grid(row=1, column=1, padx=3, pady=3)
        tk.Label(pr, text="Val:", bg=C["bg2"], fg=C["fg"]).grid(row=1, column=2, sticky=tk.W, pady=3, padx=(10, 0))
        self._ad_val = tk.StringVar()
        tk.Entry(pr, textvariable=self._ad_val, font=("Consolas", 10),
                 bg=C["bg3"], fg=C["fg"], relief=tk.FLAT, width=25).grid(row=1, column=3, padx=3, pady=3)
        tk.Button(pr, text="Set", command=self._ad_set_p,
                  bg=C["yellow"], fg="#000", activebackground="#ffd966",
                  font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15, pady=6,
                  cursor="hand2").grid(row=1, column=4, padx=10)

        # Settings browser
        st = ttk.LabelFrame(f, text="Settings Browser", padding=10)
        st.pack(fill=tk.X, padx=8, pady=5)
        for text, ns in [("Global", "global"), ("Secure", "secure"), ("System", "system")]:
            tk.Button(st, text=text, command=lambda n=ns: self._ad_sett(n),
                      bg=C["bg3"], fg=C["blue"], activebackground=C["blue"],
                      activeforeground="#fff", font=("Segoe UI", 9, "bold"),
                      relief=tk.FLAT, padx=20, pady=6, cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Expert tools
        ex = ttk.LabelFrame(f, text="Expert Tools", padding=10)
        ex.pack(fill=tk.X, padx=8, pady=5)
        ebtns = [
            ("Dump UI", self._ad_dui, C["blue"]),
            ("Contacts DB", self._ad_contacts, C["cyan"]),
            ("SMS DB", self._ad_sms, C["cyan"]),
            ("WiFi Config", self._ad_wifi, C["green"]),
            ("List Users", self._ad_users, C["purple"]),
            ("Accounts", self._ad_accts, C["purple"]),
            ("Open URL...", self._ad_url, C["green"]),
            ("Factory Reset", self._ad_freset, C["red"]),
            ("Wipe Cache", self._ad_wcache, C["red"]),
            ("Partition List", self._ad_parts, C["orange"]),
            ("Part. Info", self._ad_pinfo, C["orange"]),
            ("Media Scan", self._ad_mscan, C["cyan"]),
        ]
        for i, (text, cmd, color) in enumerate(ebtns):
            tk.Button(ex, text=text, command=cmd, bg=C["bg3"], fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                      padx=10, pady=4, cursor="hand2").grid(row=i//6, column=i%6, padx=2, pady=2)

        # ROM flash
        rm = ttk.LabelFrame(f, text="Bulk ROM Flash (Select folder with .img files)", padding=10)
        rm.pack(fill=tk.X, padx=8, pady=5)
        for text, cmd, color in [
            ("Flash Package", self._ad_flashpkg, C["red"]),
            ("Flash + Skip Reboot", self._ad_flashskip, C["orange"]),
        ]:
            tk.Button(rm, text=text, command=cmd, bg=C["bg3"], fg=color,
                      activebackground=color, activeforeground="#fff",
                      font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
                      padx=20, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=8)

        self._ad_out = scrolledtext.ScrolledText(f, wrap=tk.WORD, font=("Consolas", 9),
                                                   bg=C["bg2"], fg=C["fg"], height=10,
                                                   insertbackground=C["fg"], relief=tk.FLAT,
                                                   state=tk.DISABLED, padx=10, pady=10)
        self._ad_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)

    # ═══════════════════ LOGIC ═══════════════════

    def _log(self, msg, w=None):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        if w:
            w.configure(state=tk.NORMAL)
            w.insert(tk.END, line)
            w.see(tk.END)
            w.configure(state=tk.DISABLED)
        self._sbar.config(text=f"[{ts}] {msg[:100]}")

    def _run(self, func, callback=None):
        def w():
            try:
                r = func()
                if callback:
                    self.root.after(0, lambda: callback(r))
            except Exception as e:
                self.root.after(0, lambda: self._status(f"Error: {e}"))
        threading.Thread(target=w, daemon=True).start()

    def _status(self, msg):
        self._sbar.config(text=msg)

    def _check(self) -> bool:
        if not self.selected_device:
            messagebox.showwarning("No Device", "Select a device first!")
            return False
        return True

    # ─── DEVICE REFRESH (ASYNC) ───

    def _refresh(self):
        """Fast device scan, then async enrich"""
        try:
            self.devices = self.core.get_devices()
            self.fb_devices = self.core.get_fastboot_devices()
        except:
            return

        all_d = self.devices + self.fb_devices
        labels = []
        for d in all_d:
            icon = {"device": "[ADB]", "unauthorized": "[!AUTH]", "offline": "[OFF]",
                    "recovery": "[REC]", "sideload": "[SDL]", "fastboot": "[FB]"}.get(d.status, f"[{d.status.upper()}]")
            labels.append(f"{d.serial} | {icon} {d.model}")

        if not labels:
            labels = ["No devices"]

        self.dev_cb['values'] = labels
        if all_d:
            self.dev_cb.current(0)
            self._on_dev_select(None)
            self._status_dot.config(fg=C["green"])
            self._status_label.config(text="Device Connected", fg=C["green"])
        else:
            self._status_dot.config(fg=C["red"])
            self._status_label.config(text="No Device", fg=C["red"])
            self._show_info("No device connected.\n\nConnect via USB or WiFi ADB:\n  Settings > Developer Options > USB Debugging\n  Then run: adb connect <IP>:5555")

    def _auto_refresh(self):
        """Periodic refresh - no enrichment to avoid repeated ADB calls"""
        try:
            adb_d = self.core.get_devices()
            fb_d = self.core.get_fastboot_devices()
            all_d = adb_d + fb_d
            if all_d and not self.selected_device:
                self._refresh()
        except:
            pass
        self.root.after(8000, self._auto_refresh)
        # Start auto-refresh after first load

    def _on_dev_select(self, event):
        sel = self.dev_var.get()
        if "No devices" in sel:
            self.selected_device = None
            self._status_dot.config(fg=C["red"])
            self._status_label.config(text="No Device", fg=C["red"])
            return

        serial = sel.split(" | ")[0]
        self.selected_device = serial
        self.core.invalidate_cache(serial)

        all_d = self.devices + self.fb_devices
        device = None
        for d in all_d:
            if d.serial == serial:
                device = d
                break

        if not device:
            return

        # Update status dot
        if device.is_fastboot:
            self._status_dot.config(fg=C["orange"])
            self._status_label.config(text="Fastboot Mode", fg=C["orange"])
        elif device.status == "unauthorized":
            self._status_dot.config(fg=C["yellow"])
            self._status_label.config(text="Unauthorized!", fg=C["yellow"])
        elif device.status == "offline":
            self._status_dot.config(fg=C["red"])
            self._status_label.config(text="Offline", fg=C["red"])
        else:
            self._status_dot.config(fg=C["green"])
            self._status_label.config(text="Online", fg=C["green"])

        # Show basic info immediately
        self._show_info(f"Serial: {device.serial}\nStatus: {device.status}\nModel: {device.model}\n\nLoading details...")

        # ASYNC ENRICHMENT - No freeze!
        if device.status == "device" and not device.is_fastboot:
            self._status("Enriching device info...")
            self.core.enrich_device_async(serial, self._on_enriched)

    def _on_enriched(self, device: DeviceInfo):
        """Callback when device info is enriched"""
        self._update_dash(device)
        self._status("Ready")

    def _update_dash(self, d: DeviceInfo):
        info = f"""
┌──────────────────────────────────────────┐
│           DEVICE INFORMATION             │
├──────────────────────────────────────────┤
│ Serial:       {d.serial:<30}│
│ Status:       {d.status:<30}│
│ Model:        {d.model:<30}│
│ Brand:        {d.brand:<30}│
│ Device:       {d.device_name:<30}│
│ Android:      {d.android_version:<30}│
│ SDK:          {d.sdk_version:<30}│
│ Security:     {d.security_patch:<30}│
│ Build:        {d.build_number:<30}│
│ Fingerprint:  {d.build_fingerprint:<30}│
│ Hardware:     {d.hardware:<30}│
│ Chipset:      {d.chipset:<30}│
│ Bootloader:   {d.bootloader_ver:<30}│
│ Baseband:     {d.baseband:<30}│
│ Battery:      {d.battery_level:<30}│
│ Bat Status:   {d.battery_status:<30}│
│ Bat Health:   {d.battery_health:<30}│
│ Bat Temp:     {d.battery_temp:<30}│
│ IMEI:         {d.imei:<30}│
│ HW Serial:    {d.serial_number:<30}│
│ Screen:       {d.screen_resolution:<30}│
│ DPI:          {d.screen_density:<30}│
│ RAM:          {d.total_ram:<30}│
│ Storage:      {d.available_storage:<30}│
│ SELinux:      {d.selinux_mode:<30}│
│ Encryption:   {d.encryption_state:<30}│
│ USB:          {d.usb_config:<30}│
│ IP:           {d.ip_address:<30}│
│ WiFi:         {d.wifi_ssid:<30}│
│ Uptime:       {d.uptime:<30}│
│ Kernel:       {d.kernel_version:<30}│
│ Root:         {'YES' if d.root_access else 'NO':<30}│
│ Magisk:       {'YES' if d.magisk_installed else 'NO':<30}│
│ TWRP:         {'YES' if d.twrp_installed else 'NO':<30}│
│ Unlocked:     {'YES' if d.bootloader_unlocked else 'NO':<30}│
│ Emulator:     {'YES' if d.is_emulator else 'NO':<30}│
└──────────────────────────────────────────┘""".strip()

        self._show_info(info)

        # Update stats
        _, _, _ = d, d, d
        stats_map = {
            "Status": (d.status, C["green"] if d.status == "device" else C["yellow"]),
            "Model": (d.model, C["fg"]),
            "Brand": (d.brand, C["fg"]),
            "Android": (d.android_version, C["fg"]),
            "SDK": (d.sdk_version, C["fg"]),
            "Battery": (d.battery_level, C["green"]),
            "Root": ("YES" if d.root_access else "NO", C["green"] if d.root_access else C["red"]),
            "Bootloader": ("UNLOCKED" if d.bootloader_unlocked else "LOCKED",
                          C["red"] if d.bootloader_unlocked else C["green"]),
            "Chipset": (d.chipset, C["fg"]),
            "IMEI": (d.imei, C["fg"]),
            "RAM": (d.total_ram, C["fg"]),
            "Storage": (d.available_storage, C["fg"]),
            "SELinux": (d.selinux_mode, C["green"] if d.selinux_mode == "Enforcing" else C["yellow"]),
            "Res": (d.screen_resolution, C["fg"]),
            "DPI": (d.screen_density, C["fg"]),
            "Uptime": (d.uptime, C["fg"]),
            "Kernel": (d.kernel_version[:30] if d.kernel_version else "?", C["fg"]),
            "Magisk": ("YES" if d.magisk_installed else "NO", C["green"] if d.magisk_installed else C["fg2"]),
            "TWRP": ("YES" if d.twrp_installed else "NO", C["green"] if d.twrp_installed else C["fg2"]),
            "WiFi": (d.wifi_ssid, C["cyan"]),
            "IP": (d.ip_address, C["cyan"]),
            "Temp": (d.battery_temp, C["fg"]),
        }
        for key, (val, color) in stats_map.items():
            if key in self._stats:
                self._stats[key].config(text=str(val)[:30], fg=color)

    def _show_info(self, txt):
        try:
            self._info_txt.configure(state=tk.NORMAL)
            self._info_txt.delete(1.0, tk.END)
            self._info_txt.insert(tk.END, txt)
            self._info_txt.configure(state=tk.DISABLED)
        except:
            pass

    # ─── REBOOT ───

    def _reboot(self, mode=""):
        if not self._check():
            return
        self._run(lambda: self.core.reboot(mode, self.selected_device))

    def _reboot_edl(self):
        if not self._check():
            return
        if messagebox.askyesno("EDL", "Reboot to Qualcomm EDL (9008)?"):
            self._run(lambda: self.core.fb_edl(self.selected_device))

    # ─── WIFI DIALOG ───

    def _wifi_dlg(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Connect WiFi ADB")
        dlg.geometry("350x170")
        dlg.configure(bg=C["bg2"])
        dlg.transient(self.root)
        tk.Label(dlg, text="IP Address:", bg=C["bg2"], fg=C["fg"], font=("Segoe UI", 10)).pack(pady=(20, 5))
        ip = tk.StringVar()
        tk.Entry(dlg, textvariable=ip, font=("Consolas", 12), bg=C["bg3"], fg=C["fg"],
                 relief=tk.FLAT, width=25).pack(pady=5)
        tk.Label(dlg, text="Port: 5555", bg=C["bg2"], fg=C["fg2"]).pack()

        def connect():
            if ip.get().strip():
                self._run(lambda: self.core.connect_wifi(ip.get().strip(), 5555, self.selected_device))
                dlg.destroy()

        tk.Button(dlg, text="Connect", command=connect, bg=C["green"], fg="#000",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=30, pady=8,
                  cursor="hand2").pack(pady=15)

    def _disconnect_all(self):
        self._run(lambda: self.core.disconnect_all())

    def _open_app(self):
        if not self._check():
            return
        pkg = messagebox.askstring("Open App", "Package name:")
        if pkg:
            self._run(lambda: self.core.open_app(pkg, self.selected_device))

    # ─── SHELL ───

    def _sh_exec(self, event):
        if not self._check():
            return
        cmd = self._sh_in.get().strip()
        if not cmd:
            return
        self.cmd_history.append(cmd)
        self.hist_idx = len(self.cmd_history)
        self._sh_in.delete(0, tk.END)
        self._log(f"$ {cmd}", self._sh_out)
        root = self._root_var.get()
        self._run(lambda: self.core.root_shell(cmd, self.selected_device) if root else self.core.shell(cmd, self.selected_device),
                  lambda r: self._log(r, self._sh_out))

    def _sh_up(self, event):
        if self.hist_idx > 0:
            self.hist_idx -= 1
            self._sh_in.delete(0, tk.END)
            self._sh_in.insert(0, self.cmd_history[self.hist_idx])

    def _sh_down(self, event):
        if self.hist_idx < len(self.cmd_history) - 1:
            self.hist_idx += 1
            self._sh_in.delete(0, tk.END)
            self._sh_in.insert(0, self.cmd_history[self.hist_idx])
        elif self.hist_idx == len(self.cmd_history) - 1:
            self.hist_idx += 1
            self._sh_in.delete(0, tk.END)

    def _sh_clr(self):
        self._sh_out.configure(state=tk.NORMAL)
        self._sh_out.delete(1.0, tk.END)
        self._sh_out.configure(state=tk.DISABLED)

    # ─── FILES ───

    def _fm_list(self):
        if not self._check():
            return
        self._run(lambda: self.core.list_files(self._fm_path.get(), self.selected_device),
                  self._fm_update)

    def _fm_update(self, out):
        for item in self._fm_tree.get_children():
            self._fm_tree.delete(item)
        for line in out.splitlines():
            parts = line.strip().split(None, 7)
            if len(parts) >= 8 and parts[7] not in (".", ".."):
                self._fm_tree.insert("", tk.END, values=(parts[0], parts[2], parts[4],
                                                           f"{parts[5]} {parts[6]}", parts[7]))

    def _fm_dbl(self, event):
        sel = self._fm_tree.selection()
        if not sel:
            return
        name = self._fm_tree.item(sel[0])['values'][4]
        cur = self._fm_path.get().rstrip("/")
        self._fm_path.set(f"{cur}/{name}")
        self._fm_list()

    def _fm_up(self):
        cur = self._fm_path.get().rstrip("/")
        self._fm_path.set("/".join(cur.split("/")[:-1]) or "/")
        self._fm_list()

    def _fm_push(self):
        if not self._check():
            return
        loc = filedialog.askopenfilename()
        if loc:
            self._run(lambda: self.core.push(loc, self._fm_path.get(), self.selected_device))

    def _fm_pull(self):
        if not self._check():
            return
        sel = self._fm_tree.selection()
        if sel:
            name = self._fm_tree.item(sel[0])['values'][4]
            rem = f"{self._fm_path.get().rstrip('/')}/{name}"
            loc = filedialog.askdirectory()
            if loc:
                self._run(lambda: self.core.pull(rem, loc, self.selected_device))

    def _fm_del(self):
        if not self._check():
            return
        sel = self._fm_tree.selection()
        if sel:
            name = self._fm_tree.item(sel[0])['values'][4]
            path = f"{self._fm_path.get().rstrip('/')}/{name}"
            if messagebox.askyesno("Delete", f"Delete {name}?"):
                self._run(lambda: self.core.delete_file(path, self.selected_device))

    def _fm_mkdir(self):
        if not self._check():
            return
        name = messagebox.askstring("Mkdir", "Directory name:")
        if name:
            path = f"{self._fm_path.get().rstrip('/')}/{name}"
            self._run(lambda: self.core.make_dir(path, self.selected_device))

    def _fm_find(self):
        if not self._check():
            return
        pat = messagebox.askstring("Find", "Pattern (e.g. *.jpg):", initialvalue="*.*")
        if pat:
            self._run(lambda: self.core.search_files(self._fm_path.get(), pat, self.selected_device))

    # ─── APPS ───

    def _app_ref(self):
        if not self._check():
            return
        f = self._app_filter.get()
        self._run(lambda: self.core.get_packages(self.selected_device, f == "System", f == "Third-Party"),
                  self._app_upd)

    def _app_upd(self, apps):
        for item in self._app_tree.get_children():
            self._app_tree.delete(item)
        for a in apps:
            self._app_tree.insert("", tk.END, values=(a["name"],))

    def _app_inst(self):
        if not self._check():
            return
        apk = filedialog.askopenfilename(filetypes=[("APK", "*.apk")])
        if apk:
            self._run(lambda: self.core.install(apk, self.selected_device))

    def _app_uninst(self):
        if not self._check():
            return
        sel = self._app_tree.selection()
        if sel:
            pkg = self._app_tree.item(sel[0])['values'][0]
            if messagebox.askyesno("Uninstall", f"Uninstall {pkg}?"):
                self._run(lambda: self.core.uninstall(pkg, self.selected_device))

    def _app_bak(self):
        if not self._check():
            return
        sel = self._app_tree.selection()
        if sel:
            pkg = self._app_tree.item(sel[0])['values'][0]
            f = filedialog.askdirectory()
            if f:
                self._run(lambda: self.core.backup_app(pkg, f, self.selected_device))

    def _app_clr(self):
        if not self._check():
            return
        sel = self._app_tree.selection()
        if sel:
            pkg = self._app_tree.item(sel[0])['values'][0]
            if messagebox.askyesno("Clear", f"Clear data for {pkg}?"):
                self._run(lambda: self.core.clear_app_data(pkg, self.selected_device))

    def _app_fstop(self):
        if not self._check():
            return
        sel = self._app_tree.selection()
        if sel:
            pkg = self._app_tree.item(sel[0])['values'][0]
            self._run(lambda: self.core.force_stop(pkg, self.selected_device))

    def _app_dis(self):
        if not self._check():
            return
        sel = self._app_tree.selection()
        if sel:
            pkg = self._app_tree.item(sel[0])['values'][0]
            if messagebox.askyesno("Disable", f"Disable {pkg}?"):
                self._run(lambda: self.core.disable_app(pkg, self.selected_device))

    def _app_en(self):
        if not self._check():
            return
        sel = self._app_tree.selection()
        if sel:
            pkg = self._app_tree.item(sel[0])['values'][0]
            self._run(lambda: self.core.enable_app(pkg, self.selected_device))

    # ─── FLASH ───

    def _browse_fl(self):
        p = filedialog.askopenfilename(filetypes=[("Image", "*.img *.bin"), ("All", "*.*")])
        if p:
            self._fl_file.set(p)

    def _browse_sl(self):
        p = filedialog.askopenfilename(filetypes=[("ZIP", "*.zip")])
        if p:
            self._sl_file.set(p)

    def _flash(self):
        p, i = self._fl_part.get(), self._fl_file.get()
        if not i or not os.path.exists(i):
            messagebox.showerror("Error", "Select image file!")
            return
        if not messagebox.askyesno("DANGER", f"Flash {p} with {os.path.basename(i)}?\nCAN BRICK DEVICE!"):
            return
        self._run(lambda: self.core.fb_flash(p, i, self.selected_device),
                  lambda r: self._log(r, self._fl_out))

    def _qflash(self, part):
        if not self.selected_device:
            messagebox.showwarning("Fastboot", "Device must be in fastboot mode!")
            return
        img = filedialog.askopenfilename(title=f"Select {part} image", filetypes=[("Image", "*.img")])
        if img and messagebox.askyesno("DANGER", f"Flash {part}?"):
            self._run(lambda: self.core.fb_flash(part, img, self.selected_device),
                      lambda r: self._log(r, self._fl_out))

    def _sideload(self):
        zf = self._sl_file.get()
        if not zf or not os.path.exists(zf):
            messagebox.showerror("Error", "Select ZIP!")
            return
        self._run(lambda: self.core.sideload(zf, self.selected_device),
                  lambda r: self._log(r, self._fl_out))

    def _fbv(self, var):
        self._run(lambda: self.core.fb_getvar(var, self.selected_device),
                  lambda r: self._log(r, self._fl_out))

    def _fb_erase(self):
        p = messagebox.askstring("Erase", "Partition name:")
        if p and messagebox.askyesno("DANGER", f"Erase {p}?"):
            self._run(lambda: self.core.fb_erase(p, self.selected_device),
                      lambda r: self._log(r, self._fl_out))

    def _fb_format(self):
        p = messagebox.askstring("Format", "Partition name:")
        if p and messagebox.askyesno("DANGER", f"Format {p}?"):
            self._run(lambda: self.core.fb_format(p, self.selected_device),
                      lambda r: self._log(r, self._fl_out))

    def _fb_boot(self):
        img = filedialog.askopenfilename(title="Select boot image")
        if img:
            self._run(lambda: self.core.fb_boot(img, self.selected_device),
                      lambda r: self._log(r, self._fl_out))

    def _fb_update(self):
        zf = filedialog.askopenfilename(title="Select update ZIP", filetypes=[("ZIP", "*.zip")])
        if zf:
            self._run(lambda: self.core.fb_update(zf, self.selected_device),
                      lambda r: self._log(r, self._fl_out))

    # ─── UNLOCK & ROOT ───

    def _bl_chk(self):
        if not self._check():
            return
        self._run(lambda: self.core.fb_getvar("unlocked", self.selected_device),
                  lambda r: self._log(r, self._ul_out))

    def _bl_ounlock(self):
        if not messagebox.askyesno("WARNING", "WILL WIPE ALL DATA. Continue?"):
            return
        self._run(lambda: self.core.fb_oem_unlock(self.selected_device),
                  lambda r: self._log(r, self._ul_out))

    def _bl_olock(self):
        if not messagebox.askyesno("WARNING", "May brick custom ROM devices. Continue?"):
            return
        self._run(lambda: self.core.fb_oem_lock(self.selected_device),
                  lambda r: self._log(r, self._ul_out))

    def _bl_funlock(self):
        if not messagebox.askyesno("WARNING", "WILL WIPE ALL DATA. Continue?"):
            return
        self._run(lambda: self.core.fb_flashing_unlock(self.selected_device),
                  lambda r: self._log(r, self._ul_out))

    def _bl_flock(self):
        if not messagebox.askyesno("WARNING", "May brick custom ROM devices. Continue?"):
            return
        self._run(lambda: self.core.fb_flashing_lock(self.selected_device),
                  lambda r: self._log(r, self._ul_out))

    def _rt_chk(self):
        if not self._check():
            return
        self._run(lambda: self.core.shell("su -c id", self.selected_device),
                  lambda r: self._log(r, self._ul_out))

    def _rt_magisk(self):
        if not self._check():
            return
        apk = filedialog.askopenfilename(filetypes=[("APK", "*.apk")])
        if apk:
            self._run(lambda: self.core.push(apk, "/sdcard/magisk.apk", self.selected_device),
                      lambda r: self._log(r, self._ul_out))

    def _rt_remount(self):
        if not self._check():
            return
        self._run(lambda: self.core.remount(self.selected_device),
                  lambda r: self._log(r, self._ul_out))

    def _rt_dverity(self):
        if not self._check():
            return
        if messagebox.askyesno("WARNING", "Disable dm-verity? Reduces security."):
            self._run(lambda: self.core.disable_verity(self.selected_device),
                      lambda r: self._log(r, self._ul_out))

    def _rt_everity(self):
        if not self._check():
            return
        self._run(lambda: self.core.enable_verity(self.selected_device),
                  lambda r: self._log(r, self._ul_out))

    def _selinux(self, mode):
        if not self._check():
            return
        self._run(lambda: self.core.set_selinux(mode, self.selected_device),
                  lambda r: self._log(r, self._ul_out))

    def _bypass(self, method):
        if not self._check():
            return
        if not messagebox.askyesno("Legal", "Do you OWN this device? Educational use only!"):
            return
        funcs = {
            "swipe": lambda: self.core.bypass_swipe(self.selected_device),
            "null_pin": lambda: self.core.bypass_null_pin(self.selected_device),
            "settings": lambda: self.core.bypass_settings(self.selected_device),
            "delete_keys": lambda: self.core.bypass_delete_keys(self.selected_device),
            "frp": lambda: self.core.bypass_frp(self.selected_device),
        }
        f = funcs.get(method)
        if f:
            self._run(f, lambda r: self._log(r, self._ul_out))

    # ─── DIAGNOSTICS ───

    def _d_write(self, text):
        self._d_out.configure(state=tk.NORMAL)
        self._d_out.delete(1.0, tk.END)
        self._d_out.insert(tk.END, text)
        self._d_out.configure(state=tk.DISABLED)

    def _d_logcat(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_logcat(self.selected_device, 500), self._d_write)

    def _d_dmesg(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_dmesg(self.selected_device), self._d_write)

    def _d_procs(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_processes(self.selected_device), self._d_write)

    def _d_bat(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_battery(self.selected_device), self._d_write)

    def _d_mem(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_memory(self.selected_device), self._d_write)

    def _d_cpu(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_cpu(self.selected_device), self._d_write)

    def _d_thermal(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_thermal(self.selected_device), self._d_write)

    def _d_disk(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_disk(self.selected_device), self._d_write)

    def _d_mounts(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_mounts(self.selected_device), self._d_write)

    def _d_kern(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_kernel(self.selected_device), self._d_write)

    def _d_parts(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_partitions(self.selected_device), self._d_write)

    def _d_svc(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_services(self.selected_device), self._d_write)

    def _d_cur(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_current_app(self.selected_device), self._d_write)

    def _d_clr(self):
        self._d_out.configure(state=tk.NORMAL)
        self._d_out.delete(1.0, tk.END)
        self._d_out.configure(state=tk.DISABLED)

    # ─── NETWORK ───

    def _net_write(self, text):
        self._net_out.configure(state=tk.NORMAL)
        self._net_out.delete(1.0, tk.END)
        self._net_out.insert(tk.END, text)
        self._net_out.configure(state=tk.DISABLED)

    def _net_connect(self):
        ip = self._wifi_ip.get().strip()
        if not ip:
            messagebox.showerror("Error", "Enter IP address!")
            return
        self._run(lambda: self.core.connect_wifi(ip, int(self._wifi_port.get()), self.selected_device),
                  self._net_write)

    def _net_disconn(self):
        self._run(lambda: self.core.disconnect_all(), self._net_write)

    def _net_btp(self):
        a = self._wifi_ip.get().strip()
        if a:
            self._run(lambda: self.core.bt_pair(a, self.selected_device), self._net_write)

    def _net_btc(self):
        a = self._wifi_ip.get().strip()
        if a:
            self._run(lambda: self.core.bt_connect(a, self.selected_device), self._net_write)

    def _net_fwd(self):
        if not self._check():
            return
        self._run(lambda: self.core.forward_port(self._fwd_l.get(), self._fwd_r.get(), self.selected_device),
                  self._net_write)

    def _net_lfwd(self):
        if not self._check():
            return
        self._run(lambda: self.core.list_forwards(self.selected_device), self._net_write)

    def _net_rev(self):
        if not self._check():
            return
        self._run(lambda: self.core.reverse_forward(self._fwd_r.get(), self._fwd_l.get(), self.selected_device),
                  self._net_write)

    def _net_lrev(self):
        if not self._check():
            return
        self._run(lambda: self.core.list_reverse(self.selected_device), self._net_write)

    def _net_setpx(self):
        if not self._check():
            return
        p = self._proxy.get().strip()
        if p:
            self._run(lambda: self.core.set_proxy(p, self.selected_device), self._net_write)

    def _net_rmpx(self):
        if not self._check():
            return
        self._run(lambda: self.core.remove_proxy(self.selected_device), self._net_write)

    # ─── AUTOMATION ───

    def _a_tap(self):
        if not self._check():
            return
        x, y = int(self._tap_x.get()), int(self._tap_y.get())
        self._run(lambda: self.core.tap(x, y, self.selected_device))

    def _a_lpress(self):
        if not self._check():
            return
        x, y = int(self._tap_x.get()), int(self._tap_y.get())
        self._run(lambda: self.core.long_press(x, y, 1000, self.selected_device))

    def _a_swipe(self):
        if not self._check():
            return
        coords = [int(v.get()) for v in self._sw_vars]
        self._run(lambda: self.core.swipe(*coords, 300, self.selected_device))

    def _a_text(self):
        if not self._check():
            return
        t = self._in_text.get()
        if t:
            self._run(lambda: self.core.input_text(t, self.selected_device))

    def _a_key(self, code):
        if not self._check():
            return
        self._run(lambda: self.core.input_key(code, self.selected_device))

    def _a_monkey(self):
        if not self._check():
            return
        ev = int(self._mk_ev.get())
        pkg = self._mk_pkg.get().strip() or None
        if not messagebox.askyesno("Monkey", f"Run {ev} random events?"):
            return
        self._run(lambda: self.core.monkey(pkg, ev, self.selected_device),
                  lambda r: self._log(r, self._a_out))

    # Dev options
    def _dv_en(self):
        if not self._check():
            return
        self._run(lambda: self.core.enable_dev_options(self.selected_device))

    def _dv_sw(self):
        if not self._check():
            return
        self._run(lambda: self.core.enable_stay_awake(self.selected_device))

    def _dv_anim(self, s):
        if not self._check():
            return
        self._run(lambda: self.core.set_animation_scale(s, self.selected_device))

    def _dv_st(self):
        if not self._check():
            return
        self._run(lambda: self.core.enable_show_touches(self.selected_device))

    def _dv_ptr(self):
        if not self._check():
            return
        self._run(lambda: self.core.enable_pointer(self.selected_device))

    def _dv_ml(self):
        if not self._check():
            return
        self._run(lambda: self.core.enable_mock_location(self.selected_device))

    def _dv_rdpi(self):
        if not self._check():
            return
        self._run(lambda: self.core.reset_dpi(self.selected_device))

    def _dv_rres(self):
        if not self._check():
            return
        self._run(lambda: self.core.reset_resolution(self.selected_device))

    def _dv_url(self):
        if not self._check():
            return
        u = messagebox.askstring("Open URL", "URL:")
        if u:
            self._run(lambda: self.core.open_url(u, self.selected_device))

    # ─── ADVANCED ───

    def _ad_write(self, text):
        self._ad_out.configure(state=tk.NORMAL)
        self._ad_out.delete(1.0, tk.END)
        self._ad_out.insert(tk.END, text)
        self._ad_out.configure(state=tk.DISABLED)

    def _ad_load(self):
        if not self._check():
            return
        def run():
            props = self.core.get_device_props(self.selected_device)
            return "\n".join(f"{k}={v}" for k, v in sorted(props.items()))
        self._run(run, self._ad_write)

    def _ad_save(self):
        text = self._ad_out.get(1.0, tk.END)
        p = filedialog.asksaveasfilename(defaultextension=".txt")
        if p:
            with open(p, 'w') as f:
                f.write(text)
            self._status("Saved")

    def _ad_set_p(self):
        if not self._check():
            return
        k, v = self._ad_key.get().strip(), self._ad_val.get().strip()
        if k:
            self._run(lambda: self.core.set_prop(k, v, self.selected_device), self._ad_write)

    def _ad_sett(self, ns):
        if not self._check():
            return
        self._run(lambda: self.core.settings_list(ns, self.selected_device), self._ad_write)

    def _ad_dui(self):
        if not self._check():
            return
        f = filedialog.askdirectory()
        if f:
            self._run(lambda: self.core.dump_ui(os.path.join(f, "ui_dump.xml"), self.selected_device),
                      self._ad_write)

    def _ad_contacts(self):
        if not self._check():
            return
        f = filedialog.askdirectory()
        if f:
            self._run(lambda: self.core.pull("/data/data/com.android.providers.contacts/databases/contacts2.db",
                                              os.path.join(f, "contacts.db"), self.selected_device),
                      self._ad_write)

    def _ad_sms(self):
        if not self._check():
            return
        f = filedialog.askdirectory()
        if f:
            self._run(lambda: self.core.pull("/data/data/com.android.providers.telephony/databases/mmssms.db",
                                              os.path.join(f, "sms.db"), self.selected_device),
                      self._ad_write)

    def _ad_wifi(self):
        if not self._check():
            return
        self._run(lambda: self.core.root_shell("cat /data/misc/wifi/wpa_supplicant.conf", self.selected_device),
                  self._ad_write)

    def _ad_users(self):
        if not self._check():
            return
        self._run(lambda: self.core.list_users(self.selected_device), self._ad_write)

    def _ad_accts(self):
        if not self._check():
            return
        self._run(lambda: self.core.list_accounts(self.selected_device), self._ad_write)

    def _ad_url(self):
        if not self._check():
            return
        u = messagebox.askstring("Open URL", "URL:")
        if u:
            self._run(lambda: self.core.open_url(u, self.selected_device))

    def _ad_freset(self):
        if not self._check():
            return
        if not messagebox.askyesno("DANGER", "FACTORY RESET! ALL DATA GONE!\nABSOLUTELY sure?"):
            return
        if not messagebox.askyesno("FINAL", "Cannot undo. Proceed?"):
            return
        self._run(lambda: self.core.wipe_data(self.selected_device), self._ad_write)

    def _ad_wcache(self):
        if not self._check():
            return
        if messagebox.askyesno("Warning", "Wipe cache?"):
            self._run(lambda: self.core.wipe_cache(self.selected_device), self._ad_write)

    def _ad_parts(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_partition_list(self.selected_device), self._ad_write)

    def _ad_pinfo(self):
        if not self._check():
            return
        self._run(lambda: self.core.get_partitions(self.selected_device), self._ad_write)

    def _ad_mscan(self):
        if not self._check():
            return
        p = messagebox.askstring("Media Scan", "Path (e.g. /sdcard/DCIM):")
        if p:
            self._run(lambda: self.core.media_scan(p, self.selected_device), self._ad_write)

    def _ad_flashpkg(self):
        if not self.selected_device:
            messagebox.showwarning("Fastboot", "Need fastboot mode!")
            return
        f = filedialog.askdirectory(title="Select ROM folder")
        if not f:
            return
        imgs = {}
        for fn in os.listdir(f):
            if fn.endswith(".img"):
                imgs[os.path.splitext(fn)[0]] = os.path.join(f, fn)
        if not imgs:
            messagebox.showinfo("Info", "No .img files found")
            return
        s = "\n".join(f"  {k}: {os.path.basename(v)}" for k, v in list(imgs.items())[:15])
        if not messagebox.askyesno("DANGER", f"Flash these?\n\n{s}\n\nCAN BRICK!"):
            return
        def flash():
            res = []
            for part, img in imgs.items():
                res.append(f"{part}: {self.core.fb_flash(part, img, self.selected_device)}")
            return "\n".join(res)
        self._run(flash, self._ad_write)

    def _ad_flashskip(self):
        self._ad_flashpkg()

    # ─── QUICK ACTIONS ───

    def _scr(self):
        if not self._check():
            return
        f = filedialog.askdirectory()
        if f:
            self._run(lambda: self.core.screenshot(os.path.join(f, f"sc_{int(time.time())}.png"), self.selected_device))

    def _rec(self):
        if not self._check():
            return
        f = filedialog.askdirectory()
        if f:
            self._run(lambda: self.core.screenrecord(os.path.join(f, f"sr_{int(time.time())}.mp4"), 10, self.selected_device))

    def _dump_ui_act(self):
        if not self._check():
            return
        f = filedialog.askdirectory()
        if f:
            self._run(lambda: self.core.dump_ui(os.path.join(f, "ui_dump.xml"), self.selected_device))

    def _clrcache(self):
        if not self._check():
            return
        self._run(lambda: self.core.shell("pm trim-caches 1G", self.selected_device))

    def _emergency(self):
        if not self._check():
            return
        def run():
            return "\n".join([
                "=== EMERGENCY ===",
                self.core.shell("getprop ro.product.model", self.selected_device),
                self.core.shell("getprop ro.build.fingerprint", self.selected_device),
                self.core.shell("getprop gsm.version.baseband", self.selected_device),
            ])
        self._run(run)

    def _wake(self):
        if not self._check():
            return
        self._run(lambda: self.core.wake_screen(self.selected_device))


def main():
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    app = ADBExpertGUI(root)
    # Start auto-refresh after first full refresh
    root.after(8000, app._auto_refresh)
    root.mainloop()


if __name__ == "__main__":
    main()
