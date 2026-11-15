#!/usr/bin/env python3
"""
Generate the tag capsules shown in the notebook index, ``docs/notebooks/index.ipynb``.

Each tag is a small pill-shaped SVG in ``docs/figs/tags/``.  The index refers to them with an
``<img>`` tag, because GitHub and VS Code strip the ``style`` attribute from inline HTML, so
a coloured ``<span>`` cannot be used.

The label is ordinary SVG text, in DejaVu Sans Bold or the first sans-serif font the viewer
has.  The width of a capsule is worked out from the advance widths of the letters in DejaVu
Sans Bold (``_ADVANCE``), so this script needs no font and no plotting library, and a
different font only moves the letters a little within the padding.  The fill colors are from
the Okabe-Ito palette, chosen to be distinguishable with the common forms of color blindness,
and the text is black or white, whichever has the higher contrast with the fill.

The vocabulary is :data:`TAGS`, a tag and its fill color.  To add a tag, add it there and run

.. code-block:: bash

    python docs/gen_tags.py

``--check`` writes nothing and exits with status 1 if a committed file is missing, stale or has
no tag any more.  ``tests/test_notebook_tags.py`` runs it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

OUT = Path(__file__).parent / "figs" / "tags"

HEIGHT = 20  # capsule height (px)
FONT_SIZE = 11  # (px)
PADDING = 10  # horizontal padding either side of the text (px)

# The tag vocabulary: name -> fill color.  One color per kind of tag.
TAGS: dict[str, str] = {
    # what the notebook does with the system
    "control-design": "#0072B2",
    "linearization": "#0072B2",
    # what it shows of bdsim
    "animation": "#009E73",
    "diagram-modification": "#009E73",
    # the kind of system
    "linear": "#E69F00",
    "non-linear": "#D55E00",
    "hybrid-system": "#56B4E9",
    "discrete-time": "#CC79A7",
}

FONT_FAMILY = "DejaVu Sans, Verdana, Geneva, sans-serif"

# Advance width of each letter that a tag can use, in em, for DejaVu Sans Bold.  A letter that
# is not here is given the width of the widest, so add it if a tag needs it.
_ADVANCE: dict[str, float] = {
    "-": 0.415,
    "a": 0.675,
    "b": 0.716,
    "c": 0.593,
    "d": 0.716,
    "e": 0.678,
    "f": 0.435,
    "g": 0.716,
    "h": 0.712,
    "i": 0.343,
    "j": 0.343,
    "k": 0.665,
    "l": 0.343,
    "m": 1.042,
    "n": 0.712,
    "o": 0.687,
    "p": 0.716,
    "q": 0.716,
    "r": 0.493,
    "s": 0.595,
    "t": 0.478,
    "u": 0.712,
    "v": 0.652,
    "w": 0.924,
    "x": 0.645,
    "y": 0.652,
    "z": 0.582,
}


def _luminance(color: str) -> float:
    """Relative luminance of a ``#rrggbb`` color, as defined by WCAG."""
    rgb = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    """WCAG contrast ratio of two ``#rrggbb`` colors, from 1 to 21."""
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _text_width(text: str) -> float:
    """The width of ``text`` in the capsule font, in px."""
    widest = max(_ADVANCE.values())
    return FONT_SIZE * sum(_ADVANCE.get(c, widest) for c in text)


def svg(tag: str, fill: str) -> str:
    """
    The SVG of one capsule.

    :param tag: the text of the capsule
    :param fill: the fill color, ``#rrggbb``
    :return: the text of the SVG file
    """
    width = round(_text_width(tag) + 2 * PADDING)
    ink = max(("#ffffff", "#000000"), key=lambda c: _contrast(fill, c))
    baseline = HEIGHT / 2 + FONT_SIZE * 0.36
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{HEIGHT}" '
        f'role="img" aria-label="{tag}">\n'
        f"<title>{tag}</title>\n"
        f'<rect width="{width}" height="{HEIGHT}" rx="{HEIGHT // 2}" fill="{fill}"/>\n'
        f'<text x="{width / 2:g}" y="{baseline:.2f}" text-anchor="middle" '
        f'font-family="{FONT_FAMILY}" font-size="{FONT_SIZE}" font-weight="bold" '
        f'fill="{ink}">{tag}</text>\n'
        "</svg>\n"
    )


def main(argv: list[str] | None = None) -> int:
    """Write the capsules, or with ``--check`` verify the committed ones."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing, exit 1 if the files are not current",
    )
    args = parser.parse_args(argv)

    expected = {OUT / f"{tag}.svg": svg(tag, fill) for tag, fill in TAGS.items()}

    if args.check:
        bad = [
            p for p, text in expected.items() if not p.exists() or p.read_text() != text
        ]
        bad += [p for p in OUT.glob("*.svg") if p not in expected]
        for p in sorted(bad):
            print(f"stale, missing or unknown: {p}", file=sys.stderr)
        return 1 if bad else 0

    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*.svg"):
        if p not in expected:
            p.unlink()
    for p, text in expected.items():
        p.write_text(text)
    print(f"wrote {len(expected)} capsules to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
