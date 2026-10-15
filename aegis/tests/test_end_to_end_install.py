"""End-to-end installation test for Aegis Installer."""
import os
import shutil
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from installer import (
    find_python_executable,
    find_pythonw_executable,
    get_base_dir,
    create_windows_shortcut,
    DEFAULT_INSTALL_DIR,
)


def run_full_installation_test():
    print("=== Running End-to-End Installation Test ===")
    target_dir = Path(DEFAULT_INSTALL_DIR).resolve()
    src_dir = get_base_dir()

    print(f"Source Directory: {src_dir}")
    print(f"Target Directory: {target_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Discover Python & pythonw
    python_exe = find_python_executable()
    pythonw_exe = find_pythonw_executable()
    print(f"Discovered Python:  {python_exe}")
    print(f"Discovered Pythonw: {pythonw_exe}")
    assert os.path.exists(python_exe), "python_exe does not exist"
    assert os.path.exists(pythonw_exe), "pythonw_exe does not exist"

    # 2. Deploy items
    deploy_items = ["aegis", "frontend", "desktop.py", "app.py", "requirements.txt", "aegis.ico"]
    for name in deploy_items:
        src_item = src_dir / name
        assert src_item.exists(), f"Source item missing: {src_item}"
        dst_item = target_dir / name
        if src_item.is_dir():
            if dst_item.exists():
                shutil.rmtree(dst_item)
            shutil.copytree(src_item, dst_item)
        else:
            shutil.copy2(src_item, dst_item)
        assert dst_item.exists(), f"Failed to copy {name} to {dst_item}"
        print(f"✓ Deployed: {name}")

    # 3. Create Launchers
    desktop_py = target_dir / "desktop.py"
    target_ico = target_dir / "aegis.ico"

    vbs_launcher = target_dir / "AegisLauncher.vbs"
    with open(vbs_launcher, "w", encoding="utf-8") as f:
        f.write(
            f'Set oShell = CreateObject("WScript.Shell")\n'
            f'oShell.CurrentDirectory = "{target_dir}"\n'
            f'oShell.Run Chr(34) & "{pythonw_exe}" & Chr(34) & " " & Chr(34) & "{desktop_py}" & Chr(34), 0, False\n'
        )
    assert vbs_launcher.exists(), "AegisLauncher.vbs missing"
    print("✓ Created: AegisLauncher.vbs")

    bat_file = target_dir / "run_aegis.bat"
    with open(bat_file, "w", encoding="utf-8") as f:
        f.write(
            "@echo off\n"
            f'cd /d "{target_dir}"\n'
            f'start "" "{pythonw_exe}" desktop.py\n'
        )
    assert bat_file.exists(), "run_aegis.bat missing"
    print("✓ Created: run_aegis.bat")

    # 4. Create Desktop Shortcut
    desktop_dir = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))) / "Desktop"
    desktop_lnk = desktop_dir / "Aegis.lnk"
    create_windows_shortcut(
        target=pythonw_exe,
        lnk_path=desktop_lnk,
        icon=str(target_ico),
        args=f'"{desktop_py}"',
        working_dir=str(target_dir)
    )
    assert desktop_lnk.exists(), f"Desktop shortcut was not created at {desktop_lnk}"
    assert desktop_lnk.stat().st_size > 0, "Desktop shortcut is empty"
    print(f"✓ Created Desktop Shortcut: {desktop_lnk} ({desktop_lnk.stat().st_size} bytes)")

    # 5. Create Start Menu Shortcut
    start_menu_dir = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    start_menu_dir.mkdir(parents=True, exist_ok=True)
    start_lnk = start_menu_dir / "Aegis.lnk"
    create_windows_shortcut(
        target=pythonw_exe,
        lnk_path=start_lnk,
        icon=str(target_ico),
        args=f'"{desktop_py}"',
        working_dir=str(target_dir)
    )
    assert start_lnk.exists(), f"Start Menu shortcut was not created at {start_lnk}"
    print(f"✓ Created Start Menu Shortcut: {start_lnk} ({start_lnk.stat().st_size} bytes)")

    print("\n=== End-to-End Installation Test PASSED Perfectly! ===")


if __name__ == "__main__":
    run_full_installation_test()
