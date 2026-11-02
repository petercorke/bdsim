"""Drawing helpers shared by the scripts that generate block icons.

Icons are 250x250, black ink on a transparent background.  Everything is drawn at
``S`` times the final size and reduced on :func:`save`, which anti-aliases the edges.
Coordinates passed to the helpers are in final (250x250) pixels.
"""

import math

from PIL import Image, ImageFont

S = 4  # supersample
N = 250
W = 13  # main stroke width (matches log/watch weight)
CY = 125
FONT = "/System/Library/Fonts/Helvetica.ttc"


def canvas():
    return Image.new("L", (N * S, N * S), 0)


def s(v):
    return int(round(v * S))


def poly(d, pts, w=W, round_join=False):
    """Polyline; axis-aligned corners get square joins, unless round_join."""
    P = [(s(x), s(y)) for x, y in pts]
    if round_join:
        d.line(P, fill=255, width=s(w), joint="curve")
        r = s(w) / 2
        for x, y in (P[0], P[-1]):  # round caps
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        return
    h = s(w) / 2
    n = len(P) - 1
    for i, ((x0, y0), (x1, y1)) in enumerate(zip(P, P[1:])):
        ex0 = h if i > 0 else 0
        ex1 = h if i < n - 1 else 0
        if y0 == y1:  # horizontal
            xa, xb = (x0 - ex0, x1 + ex1) if x1 > x0 else (x1 - ex1, x0 + ex0)
            d.rectangle([xa, y0 - h, xb, y0 + h], fill=255)
        else:  # vertical
            ya, yb = (y0 - ex0, y1 + ex1) if y1 > y0 else (y1 - ex1, y0 + ex0)
            d.rectangle([x0 - h, ya, x0 + h, yb], fill=255)


def arrow(d, x0, x1, y=CY, w=W, head=22):
    poly(d, [(x0, y), (x1 - 4, y)], w)
    poly(d, [(x1 - head, y - head), (x1, y), (x1 - head, y + head)], w, True)


def text(d, xy, t, size, bold=True, spacing=0):
    f = ImageFont.truetype(FONT, s(size), index=1 if bold else 0)
    x, y = xy
    if spacing:  # centred, letter-spaced
        widths = [d.textlength(c, font=f) for c in t]
        tot = sum(widths) + s(spacing) * (len(t) - 1)
        cx = s(x) - tot / 2
        for c, wd in zip(t, widths):
            d.text((cx, s(y)), c, font=f, fill=255, anchor="lm")
            cx += wd + s(spacing)
    else:
        d.text((s(x), s(y)), t, font=f, fill=255, anchor="mm")


def save(im, name):
    im = im.resize((N, N), Image.LANCZOS)
    out = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    out.putalpha(im)
    out.save(name)


# ---- plot-style icons: thin axes and a thick curve, after clip.png, ramp.png, step.png

AXIS = 5  # width of the axes
CURVE = 19  # width of the curve
CX, PY = 129, 120  # where the axes cross, as in clip.png


def stroke(d, pts, w=CURVE, cap="butt"):
    """
    Polyline of any slope, ``w`` wide.

    :param cap: ``"butt"`` for flat ends as in clip.png, or ``"round"``

    Corners are mitred, as in clip.png, unless the turn is so sharp that the point
    would stick out, when they are rounded.
    """
    P = [(s(x), s(y)) for x, y in pts]
    r = s(w) / 2

    def unit(a, b):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        return ((b[0] - a[0]) / L, (b[1] - a[1]) / L) if L else (0.0, 0.0)

    for a, b in zip(P, P[1:]):
        ux, uy = unit(a, b)
        nx, ny = -uy * r, ux * r
        d.polygon(
            [
                (a[0] + nx, a[1] + ny),
                (b[0] + nx, b[1] + ny),
                (b[0] - nx, b[1] - ny),
                (a[0] - nx, a[1] - ny),
            ],
            fill=255,
        )
    for p0, p1, p2 in zip(P, P[1:], P[2:]):
        d1, d2 = unit(p0, p1), unit(p1, p2)
        cross = d1[0] * d2[1] - d1[1] * d2[0]
        dotp = d1[0] * d2[0] + d1[1] * d2[1]
        if cross == 0 or dotp < -0.2:
            if cross != 0:
                d.ellipse([p1[0] - r, p1[1] - r, p1[0] + r, p1[1] + r], fill=255)
            continue
        k = 1 if cross < 0 else -1  # the outside of the turn
        n1 = (-d1[1] * r, d1[0] * r)
        n2 = (-d2[1] * r, d2[0] * r)
        d.polygon(
            [
                p1,
                (p1[0] + k * n1[0], p1[1] + k * n1[1]),
                (
                    p1[0] + k * (n1[0] + n2[0]) / (1 + dotp),
                    p1[1] + k * (n1[1] + n2[1]) / (1 + dotp),
                ),
                (p1[0] + k * n2[0], p1[1] + k * n2[1]),
            ],
            fill=255,
        )
    if cap == "round":
        for x, y in (P[0], P[-1]):
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)


def axes(d, x=(5, 246), y=(9, 240), cx=CX, cy=PY, w=AXIS):
    """Horizontal axis across ``x`` at height ``cy``, vertical across ``y`` at ``cx``."""
    h = w / 2
    d.rectangle([s(x[0]), s(cy - h), s(x[1]), s(cy + h)], fill=255)
    d.rectangle([s(cx - h), s(y[0]), s(cx + h), s(y[1])], fill=255)


def dot(d, x, y, r):
    d.ellipse([s(x - r), s(y - r), s(x + r), s(y + r)], fill=255)


def ring(d, x, y, r, w):
    """Open circle of outer radius ``r`` and line width ``w``; clears whatever is inside."""
    dot(d, x, y, r)
    d.ellipse([s(x - r + w), s(y - r + w), s(x + r - w), s(y + r - w)], fill=0)


def arrowhead(d, tip, direction, length=30, width=34):
    """Filled triangle with its tip at ``tip``, pointing along ``direction`` (dx, dy)."""
    dx, dy = direction
    n = math.hypot(dx, dy)
    dx, dy = dx / n, dy / n
    bx, by = tip[0] - dx * length, tip[1] - dy * length
    px, py = -dy * width / 2, dx * width / 2
    d.polygon(
        [(s(tip[0]), s(tip[1])), (s(bx + px), s(by + py)), (s(bx - px), s(by - py))],
        fill=255,
    )


def box(d, x0, y0, x1, y1, w=W):
    """
    Hollow rectangle with its outer edge at the given coordinates.

    It clears its inside, so draw it before anything that goes inside it.
    """
    d.rectangle([s(x0), s(y0), s(x1), s(y1)], fill=255)
    d.rectangle([s(x0 + w), s(y0 + w), s(x1 - w), s(y1 - w)], fill=0)


def solid(d, pts):
    """Filled polygon."""
    d.polygon([(s(x), s(y)) for x, y in pts], fill=255)
