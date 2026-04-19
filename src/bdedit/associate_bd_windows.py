#!/usr/bin/env python3
"""
Register .bd files with bdedit on Windows.

Run once (as a normal user — no admin rights needed for HKCU):

    python associate_bd_windows.py

This creates HKEY_CURRENT_USER registry entries so that:
  - Double-clicking a .bd file opens bdedit
  - "Open with bdedit" appears in the right-click menu

To remove the association, run:

    python associate_bd_windows.py --uninstall
"""

import sys
import argparse

if sys.platform != "win32":
    print("This script is Windows-only.")
    sys.exit(1)

import winreg  # noqa: E402 (Windows-only stdlib module)


PROG_ID = "bdedit.Document"
EXT = ".bd"
PYTHON = sys.executable
OPEN_CMD = f'"{PYTHON}" -m bdsim.bdedit.bdedit "%1"'
APP_FRIENDLY = "bdedit Block Diagram"


def _set(key_path: str, name: str, value: str, hive=winreg.HKEY_CURRENT_USER):
    with winreg.CreateKey(hive, key_path) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)


def _del_tree(hive, key_path: str):
    """Recursively delete a registry key (best-effort)."""
    try:
        key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_ALL_ACCESS)
    except FileNotFoundError:
        return
    with key:
        while True:
            try:
                sub = winreg.EnumKey(key, 0)
                _del_tree(hive, f"{key_path}\\{sub}")
            except OSError:
                break
    winreg.DeleteKey(hive, key_path)


def install():
    hive = winreg.HKEY_CURRENT_USER

    # 1. Associate extension → ProgID
    _set(rf"Software\Classes\{EXT}", "", PROG_ID, hive)
    _set(rf"Software\Classes\{EXT}", "Content Type", "application/x-bdsim", hive)

    # 2. ProgID → friendly name
    _set(rf"Software\Classes\{PROG_ID}", "", APP_FRIENDLY, hive)

    # 3. Default icon (use Python icon as fallback)
    _set(rf"Software\Classes\{PROG_ID}\DefaultIcon", "", f'"{PYTHON}",0', hive)

    # 4. Open command
    _set(rf"Software\Classes\{PROG_ID}\shell\open\command", "", OPEN_CMD, hive)

    # 5. Tell the shell the association changed
    try:
        from ctypes import windll

        windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception:
        pass

    print(f"Registered: {EXT}  ->  {PROG_ID}")
    print(f"Open command: {OPEN_CMD}")
    print("Double-click any .bd file to open it with bdedit.")


def uninstall():
    hive = winreg.HKEY_CURRENT_USER
    _del_tree(hive, rf"Software\Classes\{PROG_ID}")

    # Remove our ProgID from the extension key (leave the key itself)
    try:
        with winreg.OpenKey(
            hive, rf"Software\Classes\{EXT}", 0, winreg.KEY_ALL_ACCESS
        ) as k:
            current, _ = winreg.QueryValueEx(k, "")
            if current == PROG_ID:
                winreg.DeleteValue(k, "")
    except FileNotFoundError:
        pass

    try:
        from ctypes import windll

        windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception:
        pass

    print(f"Removed file association for {EXT}.")


def main():
    parser = argparse.ArgumentParser(
        description="Register .bd files with bdedit on Windows."
    )
    parser.add_argument(
        "--uninstall", action="store_true", help="Remove the file association."
    )
    args = parser.parse_args()
    if args.uninstall:
        uninstall()
    else:
        install()


if __name__ == "__main__":
    main()
