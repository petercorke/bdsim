"""
The tag capsules in the notebook index, ``docs/notebooks/index.ipynb``.

The capsules are SVG files in ``docs/figs/tags/`` made by ``docs/gen_tags.py``, from the
vocabulary in that script.  These tests check the files are current and that the index only
uses tags in the vocabulary.
"""

from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path
from types import ModuleType

DOCS = Path(__file__).resolve().parents[1] / "docs"
GENERATOR = DOCS / "gen_tags.py"
INDEX = DOCS / "notebooks" / "index.ipynb"


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gen_tags", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(
    GENERATOR.exists(), "the docs folder is not part of this installation"
)
class NotebookTagsTest(unittest.TestCase):
    def test_capsules_are_current(self) -> None:
        # run `python docs/gen_tags.py` if this fails
        self.assertEqual(_load_generator().main(["--check"]), 0)

    def test_index_uses_known_tags(self) -> None:
        tags = _load_generator().TAGS
        source = "".join(
            "".join(cell["source"]) for cell in json.loads(INDEX.read_text())["cells"]
        )
        used = re.findall(r"docs/figs/tags/([\w-]+)\.svg", source)
        self.assertTrue(used, "the index has no tag capsules")
        for tag in used:
            self.assertIn(tag, tags, f"index uses a tag not in gen_tags.TAGS: {tag}")
        # the width of an image is the width of its file, else it is scaled
        for tag, width in re.findall(
            r'tags/([\w-]+)\.svg" alt="[\w-]+" title="[\w-]+" width="(\d+)"', source
        ):
            svg = (DOCS / "figs" / "tags" / f"{tag}.svg").read_text()
            self.assertIn(f'width="{width}" height=', svg, f"index width of {tag}")
        # the alt text of an image says the same as its file name
        for tag, alt in re.findall(r'tags/([\w-]+)\.svg" alt="([\w-]+)"', source):
            self.assertEqual(tag, alt)


if __name__ == "__main__":
    unittest.main()
