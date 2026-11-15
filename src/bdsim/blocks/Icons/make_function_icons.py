"""Draw the icons of the function and noise blocks: 250x250, black ink, transparent bg.

Plot-style icons follow clip.png: thin axes crossing at the centre and a thick curve
showing the input-output map, with the input along the horizontal axis.  The noise
icons have no axes: the operation (+ or x) followed by a held-sample noise waveform,
since the noise changes only at the ticks of the block's clock.

Run it from anywhere (``python make_function_icons.py``); the PNG files are written
next to this script.  The drawing helpers are in ``_icondraw.py``.
"""

from pathlib import Path

from _icondraw import CX, PY, arrowhead, axes, canvas, dot, poly, ring, save, stroke
from PIL import ImageDraw

K = 95  # pixels per unit of the plotted maps
HERE = Path(__file__).parent


def plot(*pts):
    """Plot coordinates, x right and y up, to pixel coordinates."""
    return [(CX + K * x, PY - K * y) for x, y in pts]


def new():
    im = canvas()
    return im, ImageDraw.Draw(im)


def done(im, name):
    save(im, str(HERE / f"{name}.png"))


# DEADBAND: zero inside the band, slope one outside
im, d = new()
axes(d)
stroke(d, plot((-1.2, -0.75), (-0.45, 0), (0.45, 0), (1.2, 0.75)))
done(im, "deadband")

# ABS
im, d = new()
axes(d)
# lifted so that the outer edge of the mitred tip rests on the axis
stroke(d, plot((-1.0, 1.14), (0, 0.14), (1.0, 1.14)))
done(im, "abs")

# SQRT: the signed square root, sgn(x) sqrt(|x|), an odd function
im, d = new()
axes(d)
ts = [-1.09 + 2.18 * i / 80 for i in range(81)]
stroke(d, plot(*[(t * abs(t), t) for t in ts]))
done(im, "sqrt")

# SIGN: +1 for x > 0, -1 for x < 0 and 0 at the origin (the filled dot)
im, d = new()
axes(d)
R, RW, LEVEL = 14, 7, 0.8
for sgn in (1, -1):
    (cx, cy), (x1, _) = plot((0, sgn * LEVEL), (1.2 * sgn, sgn * LEVEL))
    stroke(d, [(cx, cy), (x1, cy)])
    ring(d, cx, cy, R, RW)
dot(d, CX, PY, R)
done(im, "sign")

# HYSTERESIS_S: the output switches up when the input rises past the right edge of the
# loop and down when it falls past the left edge
im, d = new()
axes(d)
LV, EDGE = 0.6, 0.62
stroke(d, plot((-1.2, -LV), (EDGE, -LV), (EDGE, LV), (1.2, LV)))
stroke(d, plot((-EDGE, -LV), (-EDGE, LV), (EDGE, LV)))
# arrowheads part-way along the edges: up on the right edge, down on the left
for edge, a, b in ((EDGE, -LV, LV), (-EDGE, LV, -LV)):
    tip = plot((edge, a + 0.58 * (b - a)))[0]
    arrowhead(d, tip, (0, -1 if b > a else 1), length=34, width=48)
done(im, "hysteresis_s")

# ANOISE_S and MNOISE_S: input +/x held-sample noise
LEVELS = [0.3, -0.5, 0.65, -0.2, 0.75, -0.65]


def held_noise(x0, x1, amp, cy=125):
    n = len(LEVELS)
    pts = []
    for k, v in enumerate(LEVELS):
        xa = x0 + (x1 - x0) * k / n
        xb = x0 + (x1 - x0) * (k + 1) / n
        pts += [(xa, cy - amp * v), (xb, cy - amp * v)]
    return pts


def glyph_plus(d, cx, cy, arm, w):
    poly(d, [(cx - arm, cy), (cx + arm, cy)], w)
    poly(d, [(cx, cy - arm), (cx, cy + arm)], w)


def glyph_times(d, cx, cy, arm, w):
    a = arm * 0.85
    stroke(d, [(cx - a, cy - a), (cx + a, cy + a)], w)
    stroke(d, [(cx - a, cy + a), (cx + a, cy - a)], w)


for name, glyph in (("anoise_s", glyph_plus), ("mnoise_s", glyph_times)):
    im, d = new()
    glyph(d, 52, 125, 34, 17)
    poly(d, held_noise(104, 240, 60), 11)
    done(im, name)

# SWITCH: X (upper) and Y (lower) in on the left, Z out on the right, a lever pivoting at
# the output and resting on X, and a control arrow for S pointing at the lever
im, d = new()
PIVOT, XT, YT = (206, 125), (50, 76), (50, 174)
poly(d, [(8, XT[1]), (XT[0] - 10, XT[1])], 9)
poly(d, [(8, YT[1]), (YT[0] - 10, YT[1])], 9)
poly(d, [(PIVOT[0] + 4, PIVOT[1]), (242, PIVOT[1])], 9)
dot(d, *XT, 11)
dot(d, *YT, 11)
dot(d, *PIVOT, 11)
# the lever stops short of X, so that the contact is visible
lx, ly = XT[0] + 16, XT[1] + 5
stroke(d, [PIVOT, (lx, ly)], 13, cap="round")
mx, my = (PIVOT[0] + lx) / 2, (PIVOT[1] + ly) / 2
poly(d, [(mx, 22), (mx, my - 34)], 7)
arrowhead(d, (mx, my - 12), (0, 1), length=26, width=30)
done(im, "switch")
