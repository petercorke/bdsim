"""Draw the six hardware I/O block icons: 250x250, black ink, transparent bg.

Left-to-right flow (bdsim norm): a "bracket" is the bdsim signal side, the
pictogram is the physical/world side.  *Out blocks: bracket -> world.
*In blocks: world -> bracket.
"""
import math
from PIL import Image, ImageDraw, ImageFont

S = 4                   # supersample
N = 250
W = 13                  # main stroke width (matches log/watch weight)
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
        for x, y in (P[0], P[-1]):   # round caps
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        return
    h = s(w) / 2
    n = len(P) - 1
    for i, ((x0, y0), (x1, y1)) in enumerate(zip(P, P[1:])):
        ex0 = h if i > 0 else 0
        ex1 = h if i < n - 1 else 0
        if y0 == y1:      # horizontal
            xa, xb = (x0 - ex0, x1 + ex1) if x1 > x0 else (x1 - ex1, x0 + ex0)
            d.rectangle([xa, y0 - h, xb, y0 + h], fill=255)
        else:             # vertical
            ya, yb = (y0 - ex0, y1 + ex1) if y1 > y0 else (y1 - ex1, y0 + ex0)
            d.rectangle([x0 - h, ya, x0 + h, yb], fill=255)


def arrow(d, x0, x1, y=CY, w=W, head=22):
    poly(d, [(x0, y), (x1 - 4, y)], w)
    poly(d, [(x1 - head, y - head), (x1, y), (x1 - head, y + head)], w, True)


def bracket(d, x0, x1, gap_side, y0=28, y1=222, gap=(98, 152), r=30):
    d.rounded_rectangle([s(x0), s(y0), s(x1), s(y1)], radius=s(r),
                        outline=255, width=s(W))
    gx = (s(x1 - W - 2), s(x1 + 2)) if gap_side == "right" else (s(x0 - 2), s(x0 + W + 2))
    d.rectangle([gx[0], s(gap[0]), gx[1], s(gap[1])], fill=0)


def text(d, xy, t, size, bold=True, spacing=0):
    f = ImageFont.truetype(FONT, s(size), index=1 if bold else 0)
    x, y = xy
    if spacing:                     # centred, letter-spaced
        widths = [d.textlength(c, font=f) for c in t]
        tot = sum(widths) + s(spacing) * (len(t) - 1)
        cx = s(x) - tot / 2
        for c, wd in zip(t, widths):
            d.text((cx, s(y)), c, font=f, fill=255, anchor="lm")
            cx += wd + s(spacing)
    else:
        d.text((s(x), s(y)), t, font=f, fill=255, anchor="mm")


def gear(d, cx, cy, ro=46, rr=35, ri=16, teeth=8):
    pts = []
    for i in range(teeth):
        a = 2 * math.pi * i / teeth
        da = math.pi / teeth
        for ang, rad in ((a - 0.36 * da * 2 / 2 * 1.0 - 0.10, rr), (a - 0.20, ro),
                         (a + 0.20, ro), (a + 0.36 * da + 0.10, rr)):
            pts.append((s(cx + rad * math.cos(ang)), s(cy + rad * math.sin(ang))))
    d.polygon(pts, fill=255)
    d.ellipse([s(cx - rr + 3), s(cy - rr + 3), s(cx + rr - 3), s(cy + rr - 3)], fill=255)
    d.ellipse([s(cx - ri), s(cy - ri), s(cx + ri), s(cy + ri)], fill=0)


def sine(x0, x1, amp, y=CY):
    return [(x0 + (x1 - x0) * t / 60, y - amp * math.sin(2 * math.pi * t / 60))
            for t in range(61)]


def quantised(x0, x1, amp, steps, y=CY):
    pts = []
    for k in range(steps):
        xa = x0 + (x1 - x0) * k / steps
        xb = x0 + (x1 - x0) * (k + 1) / steps
        v = y - round(3 * math.sin(2 * math.pi * (k + .5) / steps)) * amp / 3
        pts += [(xa, v), (xb, v)]
    return pts


def save(im, name):
    im = im.resize((N, N), Image.LANCZOS)
    out = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    out.putalpha(im)
    out.save(name)


# ---- geometry: left bracket (out) x 12..96, right bracket (in) x 154..238
BL, BR = (12, 96), (154, 238)
SW = 10                                    # pictogram stroke


def step(x):
    return [(x, 148), (x + 26, 148), (x + 26, 102), (x + 68, 102)]


# DIGITALOUT
im = canvas(); d = ImageDraw.Draw(im)
bracket(d, *BL, "right"); text(d, (52, 110), "01", 28, bold=False, spacing=3)
text(d, (52, 190), "DOUT", 17)
arrow(d, 80, 140); poly(d, step(160), SW); save(im, "digitalout.png")

# DIGITALIN
im = canvas(); d = ImageDraw.Draw(im)
bracket(d, *BR, "left"); text(d, (198, 110), "01", 28, bold=False, spacing=3)
text(d, (198, 190), "DIN", 17)
arrow(d, 100, 172); poly(d, step(14), SW); save(im, "digitalin.png")

# PWMOUT
pulses = [(158, 148), (170, 148), (170, 100), (192, 100), (192, 148), (208, 148),
          (208, 100), (224, 100), (224, 148), (240, 148)]
im = canvas(); d = ImageDraw.Draw(im)
bracket(d, *BL, "right"); text(d, (50, 125), "PWM", 19)
arrow(d, 80, 140); poly(d, pulses, 9); save(im, "pwmout.png")

# ANALOGIN
im = canvas(); d = ImageDraw.Draw(im)
bracket(d, *BR, "left")
poly(d, quantised(176, 222, 36, 8), 6)
arrow(d, 104, 168); poly(d, sine(12, 90, 34), W, True); save(im, "analogin.png")

# ANALOGOUT
im = canvas(); d = ImageDraw.Draw(im)
bracket(d, *BL, "right")
poly(d, quantised(28, 74, 36, 8), 6)
arrow(d, 82, 146); poly(d, sine(166, 238, 34), W, True); save(im, "analogout.png")

# DEVICEIN
im = canvas(); d = ImageDraw.Draw(im)
bracket(d, *BR, "left"); text(d, (200, 125), "[…]", 26)
arrow(d, 112, 172); gear(d, 54, CY); save(im, "devicein.png")

# DEVICEOUT
im = canvas(); d = ImageDraw.Draw(im)
bracket(d, *BL, "right"); text(d, (50, 125), "[…]", 26)
arrow(d, 78, 138); gear(d, 196, CY); save(im, "deviceout.png")
# contact sheet
names = ["digitalout", "digitalin", "pwmout", "analogin", "analogout", "devicein", "deviceout"]
sheet = Image.new("RGB", (4 * 260, 2 * 260), "white")
for i, n in enumerate(names):
    t = Image.open(n + ".png")
    bg = Image.new("RGBA", t.size, (255, 255, 255, 255)); bg.alpha_composite(t)
    x, y = (i % 4) * 260 + 5, (i // 4) * 260 + 5
    sheet.paste(bg.convert("RGB"), (x, y))
    ImageDraw.Draw(sheet).rectangle([x, y, x + 249, y + 249], outline=(200, 200, 200))
sheet.save("sheet.png")
