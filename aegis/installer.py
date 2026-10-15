"""Aegis Desktop Installer & Setup Wizard (GUI).

A standalone graphical installer for Aegis.
- Modern dark-mode Apple / Cupertino design aesthetic.
- High-DPI support on Windows 10 & 11.
- Standalone executable compatible (extracts from PyInstaller bundle or local folder).
- Automatically discovers host Python and windowless pythonw interpreters.
- Verifies / installs required Python dependencies (FastAPI, PyWebView, NumPy, PyPDF).
- Deploys application modules, frontend assets, and multi-resolution icons.
- Creates 1-click Desktop shortcut and Start Menu entry with custom icon.
- Runs without any terminal or command prompt needed by the user.
"""
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Enable high-DPI scaling on Windows if available
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

APP_NAME = "Aegis"
APP_TAGLINE = "Privacy-First AI File Manager"
APP_VERSION = "v1.0.0"

DEFAULT_INSTALL_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "Programs",
    APP_NAME
)

# Apple Dark Mode Palette
COLOR_BG = "#0b0b1e"
COLOR_PANEL = "#13132d"
COLOR_CARD = "#1c1c3c"
COLOR_BORDER = "#2b2b52"
COLOR_TXT = "#f5f5f7"
COLOR_DIM = "#9b9ba8"
COLOR_ACC = "#8075ff"
COLOR_ACC_HOVER = "#9a91ff"
COLOR_MINT = "#30d158"
COLOR_MINT_HOVER = "#34c759"
COLOR_RED = "#ff453a"


def find_python_executable():
    """Find a functional python.exe interpreter on the host system."""
    # 1. If running as normal python script, sys.executable is the python interpreter
    if not getattr(sys, "frozen", False):
        return sys.executable

    # 2. Frozen mode: find system Python via PATH
    for name in ["python.exe", "python", "py.exe", "py"]:
        p = shutil.which(name)
        if p and os.path.exists(p):
            return p

    # 3. Check standard Windows LocalAppData installation paths
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        py_dirs = sorted(Path(local_app_data).glob("Programs/Python/Python*/python.exe"), reverse=True)
        if py_dirs:
            return str(py_dirs[0])

    # 4. Check Program Files
    for pf in ["ProgramFiles", "ProgramFiles(x86)"]:
        prog_files = os.environ.get(pf, "")
        if prog_files:
            py_dirs = sorted(Path(prog_files).glob("Python*/python.exe"), reverse=True)
            if py_dirs:
                return str(py_dirs[0])

    return "python.exe"


def find_pythonw_executable():
    """Find pythonw.exe (windowless Python that opens without any command prompt)."""
    # 1. Check beside detected python.exe
    py = find_python_executable()
    if py and os.path.exists(py):
        pyw = Path(py).parent / "pythonw.exe"
        if pyw.exists():
            return str(pyw)

    # 2. Check PATH
    for name in ["pythonw.exe", "pythonw"]:
        p = shutil.which(name)
        if p and os.path.exists(p):
            return p

    # 3. Check Windows LocalAppData
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        pyw_dirs = sorted(Path(local_app_data).glob("Programs/Python/Python*/pythonw.exe"), reverse=True)
        if pyw_dirs:
            return str(pyw_dirs[0])

    return "pythonw.exe"


def get_base_dir():
    """Determine the source directory containing Aegis payload files."""
    # 1. If running inside PyInstaller bundle, check _MEIPASS
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS).resolve()
        if (meipass / "aegis").exists() and (meipass / "desktop.py").exists():
            return meipass

    # 2. Check next to the executable (or parent folder if in dist/)
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "aegis").exists() and (exe_dir / "desktop.py").exists():
            return exe_dir
        if (exe_dir.parent / "aegis").exists() and (exe_dir.parent / "desktop.py").exists():
            return exe_dir.parent

    # 3. Check next to this script (or parent folder)
    try:
        script_dir = Path(__file__).resolve().parent
        if (script_dir / "aegis").exists() and (script_dir / "desktop.py").exists():
            return script_dir
        if (script_dir.parent / "aegis").exists() and (script_dir.parent / "desktop.py").exists():
            return script_dir.parent
    except Exception:
        pass

    return Path(".").resolve()


def create_windows_shortcut(target, lnk_path, icon=None, args="", working_dir=""):
    """Create a Windows .lnk shortcut using VBScript COM interface."""
    temp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
    vbs_path = os.path.join(temp_dir, "_aegis_mklink.vbs")

    target_str = str(target).replace('"', '""')
    lnk_str = str(lnk_path).replace('"', '""')
    args_str = str(args).replace('"', '""')
    work_str = str(working_dir or os.path.dirname(target)).replace('"', '""')
    icon_str = str(icon or "").replace('"', '""')

    script_lines = [
        'Set oWS = WScript.CreateObject("WScript.Shell")',
        f'Set oLink = oWS.CreateShortcut("{lnk_str}")',
        f'oLink.TargetPath = "{target_str}"',
    ]
    if args:
        script_lines.append(f'oLink.Arguments = "{args_str}"')
    if working_dir:
        script_lines.append(f'oLink.WorkingDirectory = "{work_str}"')
    if icon:
        script_lines.append(f'oLink.IconLocation = "{icon_str}"')
    script_lines.extend([
        'oLink.Description = "Aegis - Privacy-First AI File Manager"',
        'oLink.Save',
        ''
    ])

    script = "\r\n".join(script_lines)
    try:
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(script)
        cmd = ["cscript", "//nologo", vbs_path]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        subprocess.run(cmd, check=True, creationflags=flags)
    finally:
        if os.path.exists(vbs_path):
            try:
                os.remove(vbs_path)
            except OSError:
                pass


class AegisInstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} Setup — {APP_TAGLINE}")
        self.geometry("700x580")
        self.minsize(660, 540)
        self.configure(bg=COLOR_BG)

        # Center on screen
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")

        self.install_dir_var = tk.StringVar(value=DEFAULT_INSTALL_DIR)
        self.shortcut_desktop_var = tk.BooleanVar(value=True)
        self.shortcut_start_var = tk.BooleanVar(value=True)
        self.deps_var = tk.BooleanVar(value=True)
        self.launch_after_var = tk.BooleanVar(value=True)

        self.base_source_dir = get_base_dir()
        self.ico_path = self.find_ico()
        if self.ico_path and os.path.exists(self.ico_path):
            try:
                self.iconbitmap(self.ico_path)
            except Exception:
                pass

        self.init_styles()
        self.setup_ui()

    def find_ico(self):
        candidates = [
            self.base_source_dir / "aegis.ico",
            self.base_source_dir / "aegis" / "aegis.ico",
            Path(__file__).resolve().parent / "aegis.ico" if "__file__" in globals() else None,
        ]
        for c in candidates:
            if c and c.exists():
                return str(c)
        return ""

    def init_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=COLOR_BG, foreground=COLOR_TXT)
        style.configure(
            "Aegis.Horizontal.TProgressbar",
            troughcolor=COLOR_CARD,
            background=COLOR_ACC,
            bordercolor=COLOR_BORDER,
            lightcolor=COLOR_ACC,
            darkcolor=COLOR_ACC
        )

    def setup_ui(self):
        # 1. Header Frame
        header = tk.Frame(self, bg=COLOR_PANEL, height=88)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        h_inner = tk.Frame(header, bg=COLOR_PANEL)
        h_inner.pack(fill="both", expand=True, padx=26, pady=16)

        # Logo badge (Apple style icon rounded badge)
        badge = tk.Label(
            h_inner, text="🛡️", font=("Segoe UI Emoji", 20),
            bg=COLOR_CARD, fg=COLOR_TXT, width=3, height=1,
            highlightbackground=COLOR_ACC, highlightthickness=1
        )
        badge.pack(side="left", padx=(0, 16))

        titles_box = tk.Frame(h_inner, bg=COLOR_PANEL)
        titles_box.pack(side="left", fill="y")

        lbl_app = tk.Label(
            titles_box, text=f"{APP_NAME} {APP_VERSION}",
            font=("Segoe UI Variable Display", 16, "bold"), bg=COLOR_PANEL, fg=COLOR_TXT
        )
        lbl_app.pack(anchor="w")

        lbl_tag = tk.Label(
            titles_box, text="Official Installer & Desktop Setup Wizard — 100% On-Device",
            font=("Segoe UI", 9), bg=COLOR_PANEL, fg=COLOR_DIM
        )
        lbl_tag.pack(anchor="w", pady=(2, 0))

        # 2. Main Content Container
        self.container = tk.Frame(self, bg=COLOR_BG)
        self.container.pack(fill="both", expand=True, padx=28, pady=20)

        # Build initial Options Step
        self.build_step_options()

    def build_step_options(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        # Welcome Card
        w_card = tk.Frame(self.container, bg=COLOR_CARD, bd=1, relief="solid")
        w_card.configure(highlightbackground=COLOR_BORDER, highlightthickness=1)
        w_card.pack(fill="x", pady=(0, 14))

        w_inner = tk.Frame(w_card, bg=COLOR_CARD)
        w_inner.pack(fill="x", padx=18, pady=14)

        tk.Label(
            w_inner, text="Install Aegis AI File Manager",
            font=("Segoe UI Variable Display", 11, "bold"), bg=COLOR_CARD, fg=COLOR_TXT
        ).pack(anchor="w")
        tk.Label(
            w_inner,
            text="This wizard will install Aegis to your system and place a direct shortcut on your Desktop.\n"
                 "Once installed, you can launch Aegis with a simple double-click — no terminal needed.",
            font=("Segoe UI", 9), bg=COLOR_CARD, fg=COLOR_DIM, justify="left"
        ).pack(anchor="w", pady=(6, 0))

        # Destination Directory Card
        d_card = tk.Frame(self.container, bg=COLOR_CARD, bd=1, relief="solid")
        d_card.configure(highlightbackground=COLOR_BORDER, highlightthickness=1)
        d_card.pack(fill="x", pady=(0, 14))

        d_inner = tk.Frame(d_card, bg=COLOR_CARD)
        d_inner.pack(fill="x", padx=18, pady=14)

        tk.Label(
            d_inner, text="Destination Folder",
            font=("Segoe UI", 10, "bold"), bg=COLOR_CARD, fg=COLOR_TXT
        ).pack(anchor="w")

        d_row = tk.Frame(d_inner, bg=COLOR_CARD)
        d_row.pack(fill="x", pady=(8, 0))

        ent_dir = tk.Entry(
            d_row, textvariable=self.install_dir_var, font=("Segoe UI", 9),
            bg="#0e0e24", fg=COLOR_TXT, insertbackground=COLOR_TXT,
            relief="flat", bd=4
        )
        ent_dir.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse = tk.Button(
            d_row, text="Browse…", font=("Segoe UI", 9),
            bg=COLOR_BORDER, fg=COLOR_TXT, activebackground=COLOR_ACC,
            activeforeground="#000", relief="flat", padx=14, pady=3,
            command=self.browse_dir, cursor="hand2"
        )
        btn_browse.pack(side="right")

        # Shortcuts & Options Card
        o_card = tk.Frame(self.container, bg=COLOR_CARD, bd=1, relief="solid")
        o_card.configure(highlightbackground=COLOR_BORDER, highlightthickness=1)
        o_card.pack(fill="x", pady=(0, 16))

        o_inner = tk.Frame(o_card, bg=COLOR_CARD)
        o_inner.pack(fill="x", padx=18, pady=14)

        tk.Label(
            o_inner, text="Setup Preferences",
            font=("Segoe UI", 10, "bold"), bg=COLOR_CARD, fg=COLOR_TXT
        ).pack(anchor="w", pady=(0, 8))

        def make_chk(parent, text, var):
            c = tk.Checkbutton(
                parent, text=text, variable=var,
                bg=COLOR_CARD, fg=COLOR_TXT, selectcolor="#0e0e24",
                activebackground=COLOR_CARD, activeforeground=COLOR_TXT,
                font=("Segoe UI", 9), cursor="hand2"
            )
            c.pack(anchor="w", pady=2)
            return c

        make_chk(o_inner, "Create Desktop shortcut (1-click double-click launcher)", self.shortcut_desktop_var)
        make_chk(o_inner, "Add Aegis to Windows Start Menu", self.shortcut_start_var)
        make_chk(o_inner, "Verify and install Python dependencies (FastAPI, PyWebView, NumPy, PyPDF)", self.deps_var)
        make_chk(o_inner, "Launch Aegis immediately when installation finishes", self.launch_after_var)

        # Bottom Button Bar
        btn_bar = tk.Frame(self.container, bg=COLOR_BG)
        btn_bar.pack(fill="x", side="bottom")

        btn_cancel = tk.Button(
            btn_bar, text="Cancel", font=("Segoe UI", 10),
            bg=COLOR_CARD, fg=COLOR_DIM, activebackground=COLOR_BORDER,
            activeforeground=COLOR_TXT, relief="flat", padx=18, pady=6,
            command=self.destroy, cursor="hand2"
        )
        btn_cancel.pack(side="right", padx=(10, 0))

        btn_install = tk.Button(
            btn_bar, text="Install Now", font=("Segoe UI", 10, "bold"),
            bg=COLOR_ACC, fg="#0b0b1e", activebackground=COLOR_ACC_HOVER,
            activeforeground="#000", relief="flat", padx=24, pady=6,
            command=self.start_installation, cursor="hand2"
        )
        btn_install.pack(side="right")

    def browse_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.install_dir_var.get(), title="Select Install Folder")
        if chosen:
            self.install_dir_var.set(os.path.join(chosen, APP_NAME))

    def build_step_progress(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        self.lbl_status = tk.Label(
            self.container, text="Starting installation…",
            font=("Segoe UI", 11, "bold"), bg=COLOR_BG, fg=COLOR_TXT
        )
        self.lbl_status.pack(anchor="w", pady=(0, 8))

        self.prog_bar = ttk.Progressbar(
            self.container, style="Aegis.Horizontal.TProgressbar",
            orient="horizontal", mode="determinate", maximum=100
        )
        self.prog_bar.pack(fill="x", pady=(0, 14))
        self.prog_bar["value"] = 5
        self.update_idletasks()

        # Log Console Box
        log_frame = tk.Frame(self.container, bg=COLOR_CARD, bd=1, relief="solid")
        log_frame.configure(highlightbackground=COLOR_BORDER, highlightthickness=1)
        log_frame.pack(fill="both", expand=True, pady=(0, 14))

        self.txt_log = tk.Text(
            log_frame, bg="#070716", fg=COLOR_TXT, insertbackground=COLOR_TXT,
            font=("Consolas", 9), relief="flat", padx=12, pady=10
        )
        self.txt_log.pack(fill="both", expand=True)

        self.btn_finish_bar = tk.Frame(self.container, bg=COLOR_BG)
        self.btn_finish_bar.pack(fill="x", side="bottom")

    def log(self, msg):
        def _append():
            if hasattr(self, "txt_log") and self.txt_log.winfo_exists():
                self.txt_log.insert("end", msg + "\n")
                self.txt_log.see("end")
        self.after(0, _append)

    def set_progress(self, percent, status=""):
        def _update():
            if hasattr(self, "prog_bar") and self.prog_bar.winfo_exists():
                self.prog_bar["value"] = percent
            if status and hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
                self.lbl_status.config(text=status)
            try:
                self.update_idletasks()
            except Exception:
                pass
        self.after(0, _update)

    def start_installation(self):
        # Capture GUI variables on main thread before spawning worker thread
        target_dir = Path(self.install_dir_var.get()).resolve()
        do_desktop = self.shortcut_desktop_var.get()
        do_start = self.shortcut_start_var.get()
        do_deps = self.deps_var.get()
        do_launch = self.launch_after_var.get()

        self.build_step_progress()
        threading.Thread(
            target=self._run_install_thread,
            args=(target_dir, do_desktop, do_start, do_deps, do_launch),
            daemon=True
        ).start()

    def _run_install_thread(self, target_dir, do_desktop, do_start, do_deps, do_launch):
        try:
            src_dir = self.base_source_dir

            self.set_progress(10, "Initializing installation environment…")
            self.log(f"Target folder: {target_dir}")
            self.log(f"Source folder: {src_dir}")
            target_dir.mkdir(parents=True, exist_ok=True)

            # 1. Discover Python & Pythonw
            self.set_progress(20, "Detecting Python runtime components…")
            python_exe = find_python_executable()
            pythonw_exe = find_pythonw_executable()
            self.log(f"Detected host Python:  {python_exe}")
            self.log(f"Detected windowless:   {pythonw_exe}")

            # 2. Copy Aegis Application Assets
            self.set_progress(35, "Deploying core Aegis modules…")
            deploy_items = ["aegis", "frontend", "desktop.py", "app.py", "requirements.txt", "requirements-optional.txt", "aegis.ico", "README.md"]
            copied_count = 0
            for i, name in enumerate(deploy_items):
                src_item = src_dir / name
                if src_item.exists():
                    dst_item = target_dir / name
                    if src_item.is_dir():
                        shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
                    else:
                        try:
                            shutil.copy2(src_item, dst_item)
                        except Exception:
                            pass
                    copied_count += 1
                    self.log(f"✓ Copied: {name}")
                self.set_progress(35 + int((i + 1) / len(deploy_items) * 25))

            # Ensure high-res icon is in target
            target_ico = target_dir / "aegis.ico"
            if not target_ico.exists() and self.ico_path and os.path.exists(self.ico_path):
                shutil.copy2(self.ico_path, target_ico)
                self.log("✓ Copied: aegis.ico")

            # 3. Verify & Install Python Dependencies (Instant local check first)
            if do_deps:
                self.set_progress(65, "Verifying Python dependencies…")
                self.log("\nVerifying Python dependencies (FastAPI, PyWebView, NumPy, PyPDF)...")

                required_pkgs = {
                    "fastapi": "fastapi",
                    "uvicorn": "uvicorn",
                    "webview": "pywebview",
                    "numpy": "numpy",
                    "pypdf": "pypdf",
                }
                verify_code = (
                    "for m in ['fastapi', 'uvicorn', 'webview', 'numpy', 'pypdf']:\n"
                    "    try:\n"
                    "        __import__(m)\n"
                    "        print('OK:' + m)\n"
                    "    except ImportError:\n"
                    "        print('MISSING:' + m)\n"
                )
                missing = []
                try:
                    p_check = subprocess.run(
                        [python_exe, "-c", verify_code],
                        capture_output=True, text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                    )
                    for line in p_check.stdout.splitlines():
                        if line.startswith("OK:"):
                            self.log(f"✓ {line.split(':')[1]}: satisfied")
                        elif line.startswith("MISSING:"):
                            mod_missing = line.split(":")[1]
                            missing.append(required_pkgs.get(mod_missing, mod_missing))
                except Exception:
                    pass

                # Only run pip if packages are genuinely missing
                if missing:
                    self.set_progress(75, f"Installing {len(missing)} missing package(s)…")
                    self.log(f"Installing missing: {', '.join(missing)}...")
                    cmd = [python_exe, "-m", "pip", "install", *missing, "--prefer-binary", "--timeout", "15", "-q"]
                    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                    p = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
                    if p.returncode == 0:
                        self.log("✓ All missing dependencies installed successfully.")
                    else:
                        self.log(f"Note: {p.stderr.strip()[:140] if p.stderr else 'Finished'}")
                else:
                    self.log("✓ All dependencies are already satisfied! (Zero network wait)")

            # 4. Generate Launchers
            self.set_progress(82, "Generating zero-console native launchers…")
            desktop_py = target_dir / "desktop.py"

            # VBS silent launcher (absolutely zero console window popup)
            vbs_launcher = target_dir / "AegisLauncher.vbs"
            with open(vbs_launcher, "w", encoding="utf-8") as f:
                f.write(
                    f'Set oShell = CreateObject("WScript.Shell")\n'
                    f'oShell.CurrentDirectory = "{target_dir}"\n'
                    f'oShell.Run Chr(34) & "{pythonw_exe}" & Chr(34) & " " & Chr(34) & "{desktop_py}" & Chr(34), 0, False\n'
                )
            self.log("✓ Created silent launcher: AegisLauncher.vbs")

            # Standard batch script runner
            bat_file = target_dir / "run_aegis.bat"
            with open(bat_file, "w", encoding="utf-8") as f:
                f.write(
                    "@echo off\n"
                    f'cd /d "{target_dir}"\n'
                    f'start "" "{pythonw_exe}" desktop.py\n'
                )
            self.log("✓ Created runner script: run_aegis.bat")

            # Shortcut configuration
            shortcut_target = pythonw_exe
            shortcut_args = f'"{desktop_py}"'
            shortcut_ico = str(target_ico) if target_ico.exists() else None

            # 5. Desktop Shortcut
            if do_desktop:
                self.set_progress(85, "Creating Desktop shortcut…")
                desktop_dir = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))) / "Desktop"
                desktop_lnk = desktop_dir / f"{APP_NAME}.lnk"
                self.log(f"Creating Desktop shortcut: {desktop_lnk}")
                create_windows_shortcut(
                    target=shortcut_target,
                    lnk_path=desktop_lnk,
                    icon=shortcut_ico,
                    args=shortcut_args,
                    working_dir=str(target_dir)
                )
                self.log("✓ Desktop shortcut created successfully.")

            # 6. Start Menu Shortcut
            if do_start:
                self.set_progress(95, "Creating Start Menu shortcut…")
                start_menu_dir = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
                start_menu_dir.mkdir(parents=True, exist_ok=True)
                start_lnk = start_menu_dir / f"{APP_NAME}.lnk"
                create_windows_shortcut(
                    target=shortcut_target,
                    lnk_path=start_lnk,
                    icon=shortcut_ico,
                    args=shortcut_args,
                    working_dir=str(target_dir)
                )
                self.log("✓ Start Menu shortcut created.")

            self.set_progress(100, "Installation Complete!")
            self.log("\n=======================================================")
            self.log(f"🎉 {APP_NAME} {APP_VERSION} installed successfully!")
            self.log(f"• Location: {target_dir}")
            self.log(f"• Desktop Shortcut: {APP_NAME}.lnk")
            self.log("Double-click the desktop shortcut anytime to run Aegis.")
            self.log("=======================================================")

            self.after(500, lambda: self.show_completed(target_dir, pythonw_exe, desktop_py, do_launch))

        except Exception as e:
            self.set_progress(100, "Error during installation")
            self.log(f"\n❌ Error: {str(e)}")
            err_msg = str(e)
            self.after(0, lambda: messagebox.showerror("Installation Error", f"Failed to complete installation:\n{err_msg}"))

    def show_completed(self, target_dir, pythonw_exe, desktop_py, do_launch):
        for w in self.btn_finish_bar.winfo_children():
            w.destroy()

        btn_close = tk.Button(
            self.btn_finish_bar, text="Close", font=("Segoe UI", 10),
            bg=COLOR_CARD, fg=COLOR_TXT, activebackground=COLOR_BORDER,
            relief="flat", padx=20, pady=6, command=self.destroy, cursor="hand2"
        )
        btn_close.pack(side="right", padx=(10, 0))

        btn_launch = tk.Button(
            self.btn_finish_bar, text=f"Launch {APP_NAME} Now", font=("Segoe UI", 10, "bold"),
            bg=COLOR_MINT, fg="#0b0b1e", activebackground=COLOR_MINT_HOVER,
            relief="flat", padx=22, pady=6,
            command=lambda: self.launch_app_and_exit(target_dir, pythonw_exe, desktop_py),
            cursor="hand2"
        )
        btn_launch.pack(side="right")

        if do_launch:
            self.launch_app_and_exit(target_dir, pythonw_exe, desktop_py)

    def launch_app_and_exit(self, target_dir, pythonw_exe, desktop_py):
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            subprocess.Popen([str(pythonw_exe), str(desktop_py)], cwd=str(target_dir), creationflags=flags)
        except Exception:
            try:
                subprocess.Popen(["wscript.exe", str(target_dir / "AegisLauncher.vbs")], cwd=str(target_dir))
            except Exception:
                pass
        self.destroy()


def main():
    app = AegisInstallerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
