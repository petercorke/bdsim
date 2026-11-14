#!/usr/bin/env python3
"""
Generate the tag capsules shown in the notebook index, ``docs/notebooks/index.ipynb``.

Each tag is a small pill-shaped SVG in ``docs/figs/tags/``.  The index refers to them with an
``<img>`` tag, because GitHub and VS Code strip the ``style`` attribute from inline HTML, so
a coloured ``<span>`` cannot be used.

The letters are drawn as outlines, using the DejaVu Sans Bold that ships with Matplotlib, so
the capsules look the same in every viewer, whatever fonts it has.  The fill colors are from
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

from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MplPath
from matplotlib.textpath import TextPath

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
}

_FONT = FontProperties(family="DejaVu Sans", weight="bold")


def _luminance(color: str) -> float:
    """Relative luminance of a ``#rrggbb`` color, as defined by WCAG."""
    rgb = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    """WCAG contrast ratio of two ``#rrggbb`` colors, from 1 to 21."""
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _outline(text: str, x0: float, baseline: float) -> str:
    """
    The SVG path data for the outlines of ``text``.

    :param text: the text
    :param x0: the x coordinate of the left of the text
    :param baseline: the y coordinate of the baseline, in SVG coordinates (y down)
    :return: the ``d`` attribute of a path
    """
    path = TextPath((0, 0), text, size=FONT_SIZE, prop=_FONT)
    letter = {
        MplPath.MOVETO: "M",
        MplPath.LINETO: "L",
        MplPath.CURVE3: "Q",
        MplPath.CURVE4: "C",
    }
    d: list[str] = []
    for coords, code in path.iter_segments(simplify=False, curves=True):
        if code == MplPath.CLOSEPOLY:
            d.append("Z")
            continue
        # the coordinates are x1, y1, x2, y2, ...: shift and flip y, since SVG has y down
        pts = [
            f"{x0 + coords[i]:.2f} {baseline - coords[i + 1]:.2f}"
            for i in range(0, len(coords), 2)
        ]
        d.append(letter[code] + " ".join(pts))
    return "".join(d)


def _text_width(text: str) -> float:
    """The width of ``text`` in the capsule font, in px."""
    return float(TextPath((0, 0), text, size=FONT_SIZE, prop=_FONT).get_extents().width)


def svg(tag: str, fill: str) -> str:
    """
    The SVG of one capsule.

    :param tag: the text of the capsule
    :param fill: the fill color, ``#rrggbb``
    :return: the text of the SVG file
    """
    text_w = _text_width(tag)
    width = round(text_w + 2 * PADDING)
    ink = max(("#ffffff", "#000000"), key=lambda c: _contrast(fill, c))
    extents = TextPath((0, 0), tag, size=FONT_SIZE, prop=_FONT).get_extents()
    # centre the glyphs, using the ink bounds so that the left and right gaps match
    x0 = (width - extents.width) / 2 - extents.x0
    baseline = HEIGHT / 2 + FONT_SIZE * 0.36
    d = _outline(tag, x0, baseline)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{HEIGHT}" '
        f'role="img" aria-label="{tag}">\n'
        f"<title>{tag}</title>\n"
        f'<rect width="{width}" height="{HEIGHT}" rx="{HEIGHT // 2}" fill="{fill}"/>\n'
        f'<path d="{d}" fill="{ink}"/>\n'
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
