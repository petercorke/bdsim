"""Every block shipped with bdsim has an icon.

Icons are used by bdedit, bdweb and the documentation (the ``:blockname:`` role),
all from ``src/bdsim/blocks/Icons``.  A new block needs an icon file named for
its class, in lower case: the class ``Gain`` has ``gain.png``.  See the README in
that folder for how to make one.
"""

import struct
import unittest
from pathlib import Path

import bdsim

ICONS = Path(bdsim.__file__).parent / "blocks" / "Icons"
SIZE = 250


def png_size(path: Path) -> tuple[int, int]:
    """Width and height from the IHDR chunk of a PNG file."""
    with open(path, "rb") as f:
        header = f.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"{path.name} is not a PNG file")
    return struct.unpack(">II", header[16:24])


class IconTest(unittest.TestCase):
    def test_every_bdsim_block_has_an_icon(self):
        library = bdsim.BDSim(sysargs=False, graphics=False).block_library
        missing = sorted(
            f"{name} ({info['classname'].lower()}.png)"
            for name, info in library.items()
            if info["module"].startswith("bdsim.blocks.")
            and not (ICONS / f"{info['classname'].lower()}.png").exists()
        )
        self.assertEqual(
            missing,
            [],
            "blocks with no icon in src/bdsim/blocks/Icons, see the README there",
        )

    def test_icons_are_png_files_of_the_standard_size(self):
        wrong = {}
        for path in sorted(ICONS.glob("*.png")):
            size = png_size(path)
            if size != (SIZE, SIZE):
                wrong[path.name] = size
        self.assertEqual(wrong, {}, f"icons must be {SIZE}x{SIZE}")

    def test_the_icon_folder_is_found(self):
        self.assertTrue((ICONS / "gain.png").exists())


if __name__ == "__main__":
    unittest.main()
