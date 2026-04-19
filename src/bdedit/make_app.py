#!/usr/bin/env python3
"""
Build a minimal macOS .app bundle for bdedit so that the menu-bar shows
"bdedit" instead of "Python".

Run with whatever Python you use to run bdedit:

    python src/bdsim/bdedit/make_app.py

The resulting bdedit.app is written to the current directory.
Drag it to /Applications or keep it in the repo root.
"""

import stat
import sys
import textwrap
from pathlib import Path

APP_NAME = "bdedit"
BUNDLE_ID = "org.bdsim.bdedit"


INFO_PLIST = textwrap.dedent(
    """\
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
      "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
        <key>CFBundleName</key>
        <string>{app}</string>
        <key>CFBundleDisplayName</key>
        <string>{app}</string>
        <key>CFBundleIdentifier</key>
        <string>{bundle_id}</string>
        <key>CFBundleVersion</key>
        <string>1.0</string>
        <key>CFBundleExecutable</key>
        <string>{app}</string>
        <key>CFBundlePackageType</key>
        <string>APPL</string>
        <key>NSHighResolutionCapable</key>
        <true/>
        <key>LSUIElement</key>
        <false/>
        <key>CFBundleDocumentTypes</key>
        <array>
            <dict>
                <key>CFBundleTypeName</key>
                <string>Block Diagram</string>
                <key>CFBundleTypeExtensions</key>
                <array>
                    <string>bd</string>
                </array>
                <key>CFBundleTypeRole</key>
                <string>Editor</string>
                <key>LSHandlerRank</key>
                <string>Owner</string>
            </dict>
        </array>
        <key>UTExportedTypeDeclarations</key>
        <array>
            <dict>
                <key>UTTypeIdentifier</key>
                <string>org.bdsim.bd</string>
                <key>UTTypeDescription</key>
                <string>Block Diagram</string>
                <key>UTTypeConformsTo</key>
                <array>
                    <string>public.json</string>
                </array>
                <key>UTTypeTagSpecification</key>
                <dict>
                    <key>public.filename-extension</key>
                    <array>
                        <string>bd</string>
                    </array>
                </dict>
            </dict>
        </array>
    </dict>
    </plist>
    """
)

LAUNCHER = textwrap.dedent(
    """\
    #!/bin/bash
    # Launch bdedit using the Python that built this bundle.
    exec "{python}" -m bdsim.bdedit.bdedit "$@"
    """
)


def make_app(dest: Path = Path(".")) -> Path:
    if sys.platform != "darwin":
        print("make_app: .app bundles are macOS-only — nothing to do on this platform.")
        return None

    python = sys.executable
    bundle = dest / f"{APP_NAME}.app"
    macos_dir = bundle / "Contents" / "MacOS"
    res_dir = bundle / "Contents" / "Resources"

    macos_dir.mkdir(parents=True, exist_ok=True)
    res_dir.mkdir(parents=True, exist_ok=True)

    # Info.plist
    (bundle / "Contents" / "Info.plist").write_text(
        INFO_PLIST.format(app=APP_NAME, bundle_id=BUNDLE_ID)
    )

    # Copy icon if available
    icon_src = Path(__file__).parent / "Icons" / "bdsim_logo.png"
    if icon_src.exists():
        import shutil

        shutil.copy(icon_src, res_dir / "bdedit.png")

    # Launcher shell script
    launcher = macos_dir / APP_NAME
    launcher.write_text(LAUNCHER.format(python=python))
    launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Created {bundle}")
    print(f"  launcher → {python} -m bdsim.bdedit.bdedit")
    print("Tip: run  open bdedit.app  or drag it to /Applications")
    return bundle


if __name__ == "__main__":
    if sys.platform != "darwin":
        print("make_app: .app bundles are macOS-only.")
        sys.exit(1)
    make_app()
