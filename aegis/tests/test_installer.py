"""Tests for the Aegis Desktop Installer."""
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
    AegisInstallerApp,
)


def test_python_discovery():
    py = find_python_executable()
    assert py, "Failed to find python executable"
    assert "python" in py.lower(), f"Unexpected python path: {py}"
    print(f"PASS: Python discovered at {py}")

    pyw = find_pythonw_executable()
    assert pyw, "Failed to find pythonw executable"
    assert "pythonw" in pyw.lower(), f"Unexpected pythonw path: {pyw}"
    print(f"PASS: Pythonw discovered at {pyw}")


def test_base_dir_resolution():
    base = get_base_dir()
    assert (base / "aegis").exists(), f"aegis package not found in {base}"
    assert (base / "desktop.py").exists(), f"desktop.py not found in {base}"
    assert (base / "frontend").exists(), f"frontend not found in {base}"
    print(f"PASS: Base directory resolved to {base}")


def test_shortcut_creation():
    temp_dir = Path(os.environ.get("TEMP", "."))
    test_lnk = temp_dir / "_aegis_test_shortcut.lnk"
    if test_lnk.exists():
        test_lnk.unlink()

    base = get_base_dir()
    target_pyw = find_pythonw_executable()
    desktop_py = base / "desktop.py"
    ico = base / "aegis.ico"

    create_windows_shortcut(
        target=target_pyw,
        lnk_path=test_lnk,
        icon=str(ico),
        args=f'"{desktop_py}"',
        working_dir=str(base)
    )

    assert test_lnk.exists(), "Shortcut file was not created"
    assert test_lnk.stat().st_size > 0, "Shortcut file is empty"
    print(f"PASS: Shortcut created successfully ({test_lnk.stat().st_size} bytes)")
    test_lnk.unlink()
    print("PASS: Cleaned up test shortcut")


def main():
    print("=== Running Installer Unit Tests ===")
    test_python_discovery()
    test_base_dir_resolution()
    test_shortcut_creation()
    print("=== All Installer Tests Passed! ===")


if __name__ == "__main__":
    main()
