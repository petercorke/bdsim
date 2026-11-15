"""Draw the icons of the structural and graphics blocks: 250x250, black ink, transparent bg.

SubSystem, InPort, OutPort, Event and Animation.  These are pictograms, not math, so
they are drawn here rather than from LaTeX.  See ``make_function_icons.py`` for the
conventions the plot-style icons follow, and ``_icondraw.py`` for the helpers.

Run it from anywhere (``python make_system_icons.py``); the PNG files are written next
to this script.
"""

import math
from pathlib import Path

from _icondraw import CURVE, W, axes, box, canvas, poly, save, solid, stroke
from PIL import ImageDraw

HERE = Path(__file__).parent


def new():
    im = canvas()
    return im, ImageDraw.Draw(im)


def done(im, name):
    save(im, str(HERE / f"{name}.png"))


# SUBSYSTEM: a box containing three smaller boxes, wired in series
im, d = new()
box(d, 8, 38, 242, 212, W)
for x in (35, 105, 175):
    box(d, x, 98, x + 40, 152, 7)
for x in (75, 145):
    poly(d, [(x, 125), (x + 30, 125)], 6)
done(im, "subsystem")

# INPORT: a square with a triangle pointing in from the middle of its left edge
im, d = new()
box(d, 55, 55, 195, 195, W)
solid(d, [(55, 85), (55, 165), (130, 125)])
done(im, "inport")

# OUTPORT: a square with a triangle pointing out from the middle of its right edge
im, d = new()
box(d, 15, 55, 155, 195, W)
solid(d, [(155, 85), (155, 165), (230, 125)])
done(im, "outport")

# EVENT: a signal crossing zero and a lightning bolt from the crossing
im, d = new()
CX0, CY0 = 38, 135  # where the axes cross
axes(d, x=(15, 240), y=(12, 238), cx=CX0, cy=CY0)
XC = 105  # the signal crosses zero here
stroke(
    d,
    [(x, CY0 - 62 * math.tanh((x - XC) / 38)) for x in range(70, 205, 4)],
    CURVE - 4,
)
# the bolt starts at the crossing and runs down and to the right
bx, by = XC + 14, CY0 + 6
solid(
    d,
    [
        (bx + dx, by + dy)
        for dx, dy in (
            (0, 0),
            (30, 0),
            (17, 28),
            (38, 28),
            (-2, 84),
            (6, 44),
            (-16, 44),
        )
    ],
)
done(im, "event")

# ANIMATION: a square moving along a curve, each position bolder than the last
im, d = new()
N, SIDE = 6, 30
WIDTHS = (3, 3, 4, 5, 7, 10)
for k in range(N):
    t = k / (N - 1)
    cx = 36 + 178 * t
    cy = 190 - 105 * 4 * t * (1 - t)
    box(d, cx - SIDE / 2, cy - SIDE / 2, cx + SIDE / 2, cy + SIDE / 2, WIDTHS[k])
done(im, "animation")
