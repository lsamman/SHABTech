"""Paint the interior sheet shab_iva, written next to the IVA model in internals/."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import tl
from tl import *
from iva_layout import ZONES, CELLS, HATCH_C, HATCH_R, R_WALL

tl.OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'internals')
os.makedirs(tl.OUT, exist_ok=True)
N = 2048
c = Canvas(N, N, albedo=(.6, .6, .6), gloss=.2)
X, Y = c.x, c.y


def zone(k):
    x, y, w, h = ZONES[k]
    sy, sx = slice(y, y + h), slice(x, x + w)
    return sy, sx, x, y, w, h, X[sy, sx] - x, Y[sy, sx] - y


def base(k, rgb, gloss, mottle=.04, seed=0, scratch=0.0):
    sy, sx, x, y, w, h, xx, yy = zone(k)
    n = grime(h, w, seed + 11, base=5)
    c.albedo[sy, sx] = np.array(rgb, np.float32)[None, None] * (1 - mottle + 2 * mottle * n[..., None])
    c.gloss[sy, sx] = gloss
    c.height[sy, sx] = fbm(h, w, seed + 3, base=max(h, w) // 8, octaves=3) * .06
    if scratch:
        c.albedo[sy, sx] += scratches(h, w, seed + 7, n=int(h * w / 900))[..., None] * scratch
    return sy, sx, x, y, w, h, xx, yy


def groove(sy, sx, sd, depth=1.8, dark=.45, width=1.6):
    """Panel seam along sd = 0: a dark line with relief."""
    line = np.exp(-(sd / width) ** 2)
    c.albedo[sy, sx] *= (1 - line[..., None] * dark)
    c.height[sy, sx] -= line * depth


def bolts(sy, sx, xx, yy, pts, r=3.0, h=1.2):
    for px, py in pts:
        d = sd_circle(xx, yy, px, py, r)
        c.height[sy, sx] += fill(d, .8) * h
        c.albedo[sy, sx] *= (1 - np.exp(-np.maximum(d, 0) / 1.4)[..., None] * .22)


def ao_box(sy, sx, xx, yy, w, h, s=.35, reach=.12):
    """Soft baked-in contact shading toward the edges of a zone."""
    e = np.minimum(np.minimum(xx, w - xx) / (w * reach), np.minimum(yy, h - yy) / (h * reach))
    c.albedo[sy, sx] *= (1 - (1 - np.clip(e, 0, 1))[..., None] ** 2 * s)


def label(x, y, text, size=14, rgb=(.06, .06, .07), bg=(.92, .92, .88), pad=3):
    from PIL import ImageFont
    f = ImageFont.truetype(tl.FONT_BOLD, int(size))
    tw = int(f.getlength(text))
    m = fill(sd_rrect(X, Y, x + tw / 2, y + size * .55, tw / 2 + pad + 1, size * .55 + pad, 2))
    c.tint(m, bg, 1)
    c.add_text(text, x, y, size, rgb=rgb, opacity=.95)


def cell(k, rgb, gloss, seed=0, mottle=.05):
    base(k, rgb, gloss, mottle, seed + 400)


for i, (k, rgb, gl) in enumerate([
        ('white', (.84, .84, .82), .3), ('grey', (.52, .53, .54), .3), ('dark', (.16, .16, .17), .3), ('black', (.03, .03, .035), .25),
        ('yellow', (.82, .64, .12), .3), ('red', (.70, .09, .06), .35), ('blue', (.12, .24, .50), .25), ('steel', (.50, .51, .53), .65),
        ('copper', (.68, .42, .24), .5), ('rubber', (.05, .05, .05), .08), ('gold', (.80, .60, .22), .8), ('foam', (.34, .36, .40), .05),
        ('tan', (.72, .66, .52), .08), ('green', (.18, .46, .22), .25), ('orange', (.82, .40, .10), .25), ('softwhite', (.90, .90, .86), .06),
        ('hose', (.72, .72, .70), .2), ('lamp', (.97, .95, .86), .4), ('glove', (.78, .76, .70), .08), ('pad', (.30, .36, .48), .06),
        ('rail', (.70, .71, .72), .55), ('bag', (.76, .78, .80), .1), ('frame', (.62, .63, .64), .35), ('grate', (.24, .24, .26), .3)]):
    cell(k, rgb, gl, i)

# open grating, one tile per cell
sy, sx, x, y, w, h, xx, yy = zone('grate')
bar = np.minimum(np.minimum((xx % 14), 14 - (xx % 14)), np.minimum((yy % 14), 14 - (yy % 14)))
c.albedo[sy, sx] = np.where((bar < 2.0)[..., None], np.array((.42, .43, .45), np.float32), np.array((.035, .035, .04), np.float32))
c.height[sy, sx] = blur((bar < 2.0).astype(np.float32), .5) * 2.2
c.gloss[sy, sx] = .35

# ---------------------------------------------------------------- wall tile (one 60 deg bay)
sy, sx, x, y, w, h, xx, yy = base('wall', (.80, .81, .80), .22, .025, 1, .02)
for hx_ in (w * .5,):
    groove(sy, sx, xx - hx_, 1.6, .3, 1.4)
groove(sy, sx, np.minimum(xx, w - xx), 2.0, .4, 1.6)
for t in (.25, .5, .75):
    groove(sy, sx, yy - h * t, 1.8, .35, 1.6)
# stringer ribs top and bottom
c.height[sy, sx] += fill(np.abs(yy - 22) - 14, 1.5) * 2 + fill(np.abs(yy - (h - 22)) - 14, 1.5) * 2
c.albedo[sy, sx] *= (1 - (fill(np.abs(yy - 22) - 14, 1.5) + fill(np.abs(yy - (h - 22)) - 14, 1.5))[..., None] * .14)
pts = [(px, py) for px in np.arange(40, w, 80) for py in (22, h - 22)]
pts += [(px, py) for px in (24, w * .5 - 24, w * .5 + 24, w - 24) for py in np.arange(70, h - 50, 96)]
bolts(sy, sx, xx, yy, pts, 3.2, 1.3)
ao_box(sy, sx, xx, yy, w, h, .32, .10)
c.add_text('FIB LINER  NO FASTENERS', x + 60, y + h * .26, 13, rgb=(.25, .25, .26), opacity=.5)
c.add_text('FRAME 12', x + w * .55, y + h * .76, 13, rgb=(.25, .25, .26), opacity=.5)

# ---------------------------------------------------------------- stowage rack
sy, sx, x, y, w, h, xx, yy = base('rack', (.70, .71, .70), .25, .03, 2, .03)
rr = rng(21)
words = ['FOOD A', 'FOOD B', 'CREW 1', 'CREW 2', 'CREW 3', 'CREW 4', 'SPARES', 'MED KIT', 'TOOLS', 'FILTERS', 'WIPES', 'H2O AUX']
k_ = 0
for j in range(4):
    for i in range(3):
        cx, cy = w * (i + .5) / 3, h * (j + .5) / 4
        hw, hh = w / 6 - 7, h / 8 - 7
        sd = sd_rrect(xx, yy, cx, cy, hw, hh, 6)
        c.height[sy, sx] += bevel(sd, 4) * 2.4
        c.albedo[sy, sx] *= (1 + fill(sd)[..., None] * (rr.uniform(.98, 1.08) - 1))
        c.albedo[sy, sx] *= (1 - np.exp(-np.abs(sd) / 2)[..., None] * .5)
        d = sd_rrect(xx, yy, cx, cy + hh - 16, 26, 7, 4)
        c.height[sy, sx] += -bevel(d, 2) * 2
        c.albedo[sy, sx] *= (1 - fill(d)[..., None] * .55)
        label(x + cx - hw + 8, y + cy - hh + 8, words[k_ % 12], 13); k_ += 1
        bolts(sy, sx, xx, yy, [(cx - hw + 8, cy + hh - 8), (cx + hw - 8, cy + hh - 8), (cx + hw - 8, cy - hh + 8)], 2.4, 1)
ao_box(sy, sx, xx, yy, w, h, .25, .05)

# ---------------------------------------------------------------- science rack
sy, sx, x, y, w, h, xx, yy = base('science', (.62, .63, .65), .28, .03, 3, .03)
sd = sd_rrect(xx, yy, w * .5, h * .18, w * .42, h * .13, 8)
c.tint(np.zeros((N, N), np.float32), (0, 0, 0))
scr = fill(sd)
c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - scr[..., None]) + np.array((.02, .04, .05), np.float32) * scr[..., None]
c.gloss[sy, sx] = c.gloss[sy, sx] * (1 - scr) + .8 * scr
trace = np.exp(-((yy - (h * .18 + 18 * np.sin(xx / 16) * np.sin(xx / 47))) / 1.6) ** 2) * scr
c.albedo[sy, sx] += trace[..., None] * np.array((.15, .7, .35), np.float32)
c.height[sy, sx] += bevel(sd_rrect(xx, yy, w * .5, h * .18, w * .45, h * .155, 8), 4) * 2
for j, t in enumerate(('MARS SURFACE SCIENCE', 'SOIL SPECTROMETER', 'SAMPLE GLOVEBOX')):
    label(x + 34, y + h * (.36 + j * .2) - 4, t, 14)
    sdp = sd_rrect(xx, yy, w * .5, h * (.44 + j * .2), w * .42, h * .055, 5)
    c.height[sy, sx] += bevel(sdp, 3) * 2
    c.albedo[sy, sx] *= (1 - np.exp(-np.abs(sdp) / 2)[..., None] * .5)
    for i in range(6):
        px = w * .16 + i * w * .13; py = h * (.44 + j * .2)
        d = sd_circle(xx, yy, px, py, 8)
        c.height[sy, sx] += bevel(d, 3) * 2
        col = [(.7, .1, .06), (.1, .5, .2), (.8, .65, .1)][(i + j) % 3]
        c.tint(np.zeros((N, N), np.float32), col)
        m = fill(d + 3)
        c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array(col, np.float32) * m[..., None]
ao_box(sy, sx, xx, yy, w, h, .25, .05)

# ---------------------------------------------------------------- locker column
sy, sx, x, y, w, h, xx, yy = base('lockers', (.74, .75, .74), .25, .03, 4, .03)
for j in range(5):
    cy = h * (j + .5) / 5
    sd = sd_rrect(xx, yy, w / 2, cy, w / 2 - 8, h / 10 - 6, 6)
    c.height[sy, sx] += bevel(sd, 3) * 2.2
    c.albedo[sy, sx] *= (1 - np.exp(-np.abs(sd) / 2)[..., None] * .45)
    d = sd_rrect(xx, yy, w / 2, cy + 22, 34, 7, 4)
    c.albedo[sy, sx] *= (1 - fill(d)[..., None] * .55)
    label(x + 24, y + cy - 34, ['CLOTHES', 'HYGIENE', 'PERSONAL', 'BOOKS', 'FLAGS'][j], 13)

# ---------------------------------------------------------------- ECLSS rack
sy, sx, x, y, w, h, xx, yy = base('eclss', (.66, .68, .68), .28, .03, 5, .04)
for cx, cy, r_, nm in ((w * .28, h * .30, 74, 'CO2 BED A'), (w * .72, h * .30, 74, 'CO2 BED B')):
    d = sd_circle(xx, yy, cx, cy, r_)
    c.height[sy, sx] += bevel(d, 10) * 4 - bevel(d + 26, 4) * 2
    c.albedo[sy, sx] *= (1 - np.exp(-np.abs(d) / 3)[..., None] * .5)
    c.albedo[sy, sx] *= (1 + fill(d + 26)[..., None] * .15)
    label(x + cx - 40, y + cy - 8, nm, 14)
    bolts(sy, sx, xx, yy, [(cx + (r_ - 12) * np.cos(a), cy + (r_ - 12) * np.sin(a)) for a in np.linspace(0, 6.28, 10)[:-1]], 2.4, 1)
for py, col in ((h * .62, (.70, .42, .22)), (h * .68, (.15, .3, .55)), (h * .74, (.75, .75, .73))):
    m = fill(np.abs(yy - py) - 6, 1.2) * fill(np.abs(xx - w / 2) - (w / 2 - 26), 1.2)
    c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array(col, np.float32) * m[..., None]
    c.height[sy, sx] += m * 2.4
for i, nm in enumerate(('O2 GEN', 'H2O REC', 'TRACE')):
    px = w * (.2 + i * .3)
    d = sd_circle(xx, yy, px, h * .86, 22)
    c.height[sy, sx] += bevel(d, 6) * 3
    m = fill(d + 8); c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array((.04, .05, .05), np.float32) * m[..., None]
    label(x + px - 30, y + h * .92, nm, 13)
m = fill(np.abs(yy - h * .50) - 7, 1) * ((xx + yy) % 28 < 14)
c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array((.8, .63, .1), np.float32) * m[..., None]
m = fill(np.abs(yy - h * .50) - 7, 1) * ((xx + yy) % 28 >= 14)
c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array((.04, .04, .04), np.float32) * m[..., None]
ao_box(sy, sx, xx, yy, w, h, .25, .05)

# ---------------------------------------------------------------- flight console (dark)
sy, sx, x, y, w, h, xx, yy = base('console', (.15, .155, .165), .32, .04, 6, .03)
for fx0, fx1 in ((.03, .30), (.32, .68), (.70, .97)):
    for fy0, fy1 in ((.05, .62), (.65, .95)):
        cx, cy = w * (fx0 + fx1) / 2, h * (fy0 + fy1) / 2
        sd = sd_rrect(xx, yy, cx, cy, w * (fx1 - fx0) / 2, h * (fy1 - fy0) / 2, 7)
        c.height[sy, sx] += -bevel(sd, 3) * 2
        c.albedo[sy, sx] *= (1 - np.exp(-np.abs(sd) / 1.8)[..., None] * .6)
        c.albedo[sy, sx] += np.exp(-(np.maximum(sd + 2, 0) / 1.2) ** 2)[..., None] * .03
        bolts(sy, sx, xx, yy, [(cx - w * (fx1 - fx0) / 2 + 9, cy - h * (fy1 - fy0) / 2 + 9), (cx + w * (fx1 - fx0) / 2 - 9, cy - h * (fy1 - fy0) / 2 + 9),
                               (cx - w * (fx1 - fx0) / 2 + 9, cy + h * (fy1 - fy0) / 2 - 9), (cx + w * (fx1 - fx0) / 2 - 9, cy + h * (fy1 - fy0) / 2 - 9)], 2.6, 1.2)
W_ = (.86, .87, .84)
for t, fx, fy in (('NAV', .47, .075), ('ALT', .06, .075), ('VSI', .17, .075), ('ATM', .79, .075), ('RAD ALT', .875, .075),
                  ('SYSTEMS', .05, .67), ('SPEED', .455, .67), ('STAGE', .75, .67), ('THROTTLE', .85, .67)):
    c.add_text(t, x + w * fx, y + h * fy, 15, rgb=W_, opacity=.9)
sd = sd_rrect(xx, yy, w * .78, h * .82, 42, 42, 4)
m = fill(np.abs(sd) - 4, 1) * ((xx + yy) % 16 < 8)
c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array((.82, .65, .12), np.float32) * m[..., None]

# ---------------------------------------------------------------- bulkhead: door opening is central
sy, sx, x, y, w, h, xx, yy = base('bulkhead', (.78, .79, .78), .24, .03, 7, .03)
for t in (.20, .80):
    groove(sy, sx, xx - w * t, 1.8, .35, 1.4)
groove(sy, sx, yy - h * .12, 1.8, .35, 1.4)
pts = [(px, py) for px in np.arange(16, w, 34) for py in (h * .12 - 8, h * .12 + 8)]
bolts(sy, sx, xx, yy, pts, 2.4, 1)
# hazard frame around the door (door 0.76 x 1.08 of a 1.53 x 1.34 m wall)
dw, dh = w * .76 / 1.556 / 2, h * 1.08 / 1.34 / 2
cx, cy = w / 2, h * (1 - (1.06 - .36) / 1.34)
sd = sd_rrect(xx, yy, cx, cy, dw + 14, dh + 14, 18)
band = fill(np.abs(sd - 0) - 9, 1)
st = ((xx + yy) % 30 < 15)
c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - band[..., None]) + np.where(st[..., None], np.array((.80, .63, .1), np.float32), np.array((.05, .05, .05), np.float32)) * band[..., None]
c.add_text('AIRLOCK', x + w / 2 - 150, y + 16, 30, rgb=(.08, .08, .09), opacity=.9)
c.add_text('DUST LOCK', x + w / 2 + 16, y + 26, 18, rgb=(.08, .08, .09), opacity=.9)
c.add_text('NO SUITS', x + 18, y + h * .40, 20, rgb=(.7, .08, .05), opacity=.9)
c.add_text('PAST THIS', x + 18, y + h * .44, 20, rgb=(.7, .08, .05), opacity=.9)
c.add_text('POINT', x + 18, y + h * .48, 20, rgb=(.7, .08, .05), opacity=.9)
ao_box(sy, sx, xx, yy, w, h, .28, .06)

# ---------------------------------------------------------------- EVA door, cabin side
sy, sx, x, y, w, h, xx, yy = base('door', (.72, .73, .73), .3, .03, 8, .04)
sd = sd_rrect(xx, yy, w / 2, h / 2, w / 2 - 10, h / 2 - 10, 34)
c.height[sy, sx] += -bevel(sd, 6) * 3
c.albedo[sy, sx] *= (1 - np.exp(-np.abs(sd) / 3)[..., None] * .45)
for t in (.33, .66):
    d = sd_rrect(xx, yy, w / 2, h * t, w / 2 - 36, 7, 5)
    c.height[sy, sx] += bevel(d, 2.5) * 2.4
d = sd_rrect(xx, yy, w / 2, h / 2, 7, h / 2 - 36, 5)
c.height[sy, sx] += bevel(d, 2.5) * 2.4
d = sd_circle(xx, yy, w / 2, h * .22, 40)
c.height[sy, sx] += bevel(d, 6) * 3 - bevel(d + 14, 3) * 3
m = fill(d + 14); c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array((.02, .05, .09), np.float32) * m[..., None]
c.gloss[sy, sx] = c.gloss[sy, sx] * (1 - m) + .95 * m
c.add_text('CABIN SIDE', x + w / 2 - 54, y + h * .74, 20, rgb=(.06, .06, .07))
c.add_text('DEPRESS BEFORE OPENING', x + w / 2 - 92, y + h * .79, 14, rgb=(.7, .08, .05))
bolts(sy, sx, xx, yy, [(22 + (w - 44) * i / 7, 22) for i in range(8)] + [(22 + (w - 44) * i / 7, h - 22) for i in range(8)], 3, 1.4)

# ---------------------------------------------------------------- water bags: two across
sy, sx, x, y, w, h, xx, yy = base('water', (.70, .75, .80), .16, .04, 9, 0)
c.height[sy, sx] += weave(xx, yy, 3.0) * .15 + crinkle(h, w, 91, scale=9) * .45
c.albedo[sy, sx] *= (.90 + .2 * grime(h, w, 92, base=4))[..., None]
for cx_ in (w * .25, w * .75):
    sd = sd_rrect(xx, yy, cx_, h / 2, w / 4 - 3, h / 2 - 3, 18)
    c.albedo[sy, sx] *= (1 - np.exp(-np.abs(sd) / 3)[..., None] * .55)
    m = fill(np.abs(xx - cx_) - 7, 1)
    c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array((.20, .30, .50), np.float32) * m[..., None]
    c.height[sy, sx] += m * 1.5
    m = fill(np.abs(yy - h * .5) - 6, 1)
    c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array((.20, .30, .50), np.float32) * m[..., None]
    c.add_text('H2O', x + cx_ - 44, y + h * .22, 22, rgb=(.08, .12, .3), opacity=.85)
    c.add_text('POTABLE' if cx_ < w / 2 else 'GREY', x + cx_ + 14, y + h * .24, 15, rgb=(.08, .12, .3), opacity=.85)

# ---------------------------------------------------------------- deck plate, 1.64 m across the zone
sy, sx, x, y, w, h, xx, yy = base('deck', (.27, .28, .29), .3, .05, 10, .06)
dd = ((xx + (yy // 16) % 2 * 8) % 16 - 8) ** 2 + ((yy % 16) - 8) ** 2 * 5
c.height[sy, sx] += (dd < 30) * 1.0
c.albedo[sy, sx] *= (.92 + .22 * (dd < 30))[..., None]
ppm = w / 1.64
hx, hy = w / 2 + HATCH_C[0] * ppm, h / 2 - HATCH_C[1] * ppm
d = sd_circle(xx, yy, hx, hy, (HATCH_R + .05) * ppm)
band = fill(np.abs(d) - 7, 1)
st = ((xx + yy) % 22 < 11)
c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - band[..., None]) + np.where(st[..., None], np.array((.80, .63, .1), np.float32), np.array((.05, .05, .05), np.float32)) * band[..., None]
for r_ in np.arange(.3, .82, .26):
    d2 = np.abs(np.hypot(xx - w / 2, yy - h / 2) - r_ * ppm)
    groove(sy, sx, d2, 1.2, .3, 1.2)
ang = np.arctan2(xx - w / 2, yy - h / 2)
for a_ in np.linspace(-np.pi, np.pi, 9)[:-1]:
    dist = np.abs(np.sin(ang - a_)) * np.hypot(xx - w / 2, yy - h / 2)
    groove(sy, sx, dist + (np.cos(ang - a_) < 0) * 100, 1.2, .3, 1.2)
ao_box(sy, sx, xx, yy, w, h, .1, .05)

# ---------------------------------------------------------------- ceiling, planar over the disc
sy, sx, x, y, w, h, xx, yy = base('ceiling', (.82, .83, .82), .2, .02, 11, 0)
ppm = w / 1.64
ang = np.arctan2(xx - w / 2, yy - h / 2); rad = np.hypot(xx - w / 2, yy - h / 2)
for a_ in np.linspace(-np.pi, np.pi, 13)[:-1]:
    dist = np.abs(np.sin(ang - a_)) * rad
    groove(sy, sx, dist + (np.cos(ang - a_) < 0) * 100, 1.5, .3, 1.2)
for r_ in (.25, .55, .75):
    groove(sy, sx, np.abs(rad - r_ * ppm), 1.5, .3, 1.2)
hx, hy = w / 2 + HATCH_C[0] * ppm, h / 2 - HATCH_C[1] * ppm
c.albedo[sy, sx] *= (1 - np.exp(-np.maximum(sd_circle(xx, yy, hx, hy, HATCH_R * ppm), 0) / 12)[..., None] * .25)

# ---------------------------------------------------------------- crown liner
sy, sx, x, y, w, h, xx, yy = base('crown', (.83, .83, .80), .1, .02, 12, 0)
c.height[sy, sx] += np.clip(1 - np.abs(2 * ((xx % 58) / 58) - 1) ** 4, 0, 1) * np.clip(1 - np.abs(2 * ((yy % 50) / 50) - 1) ** 4, 0, 1) * 1.6
fx_, fy_ = (xx % 58) / 58, (yy % 50) / 50
dist = np.minimum(np.minimum(fx_, 1 - fx_) * 58, np.minimum(fy_, 1 - fy_) * 50)
c.albedo[sy, sx] *= (1 - np.exp(-dist / 1.3)[..., None] * .24)

# ---------------------------------------------------------------- sleep cubby back wall
sy, sx, x, y, w, h, xx, yy = base('sleep', (.72, .66, .56), .08, .04, 13, 0)
fx_, fy_ = (xx % 38) / 38, (yy % 38) / 38
c.height[sy, sx] += np.clip(1 - np.abs(2 * fx_ - 1) ** 4 - np.abs(2 * fy_ - 1) ** 4, 0, 1) * 1.5
dist = np.minimum(np.minimum(fx_, 1 - fx_), np.minimum(fy_, 1 - fy_)) * 38
c.albedo[sy, sx] *= (1 - np.exp(-dist / 1.2)[..., None] * .3)
rr = rng(131)
for px, py, pw, ph, col in ((.20, .24, 30, 22, (.72, .32, .18)), (.42, .22, 24, 30, (.25, .45, .75)), (.68, .25, 34, 24, (.28, .52, .28))):
    sd = sd_rrect(xx, yy, w * px, h * py, pw, ph, 1)
    m = fill(sd); frame = fill(sd + 4)
    c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array((.95, .95, .92), np.float32) * m[..., None]
    pic = (np.array(col, np.float32)[None, None] * (.75 + .5 * grime(h, w, int(px * 100), base=6))[..., None])
    c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - frame[..., None]) + pic * frame[..., None]
d = sd_rrect(xx, yy, w * .5, h * .46, 48, 10, 4)
m = fill(d); c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array((.95, .92, .8), np.float32) * m[..., None]
ao_box(sy, sx, xx, yy, w, h, .32, .16)

# ---------------------------------------------------------------- curtain and suit cloth
sy, sx, x, y, w, h, xx, yy = base('curtain', (.34, .42, .54), .05, .03, 14, 0)
fold = np.sin(xx * 2 * np.pi / 26 + 2 * np.sin(yy / 90))
c.height[sy, sx] += fold * 2.6
c.albedo[sy, sx] *= (.82 + .24 * (fold * .5 + .5))[..., None]
c.height[sy, sx] += weave(xx, yy, 3) * .15

sy, sx, x, y, w, h, xx, yy = base('suit', (.88, .87, .82), .08, .03, 15, 0)
c.height[sy, sx] += crinkle(h, w, 151, scale=22) * 1.6 + weave(xx, yy, 3) * .2
c.albedo[sy, sx] *= (.92 + .14 * grime(h, w, 152, base=7))[..., None]
c.albedo[sy, sx] *= (1 - fill(np.abs(yy - h * .55) - 8)[..., None] * .28)
for frac, col in ((.25, (.72, .12, .08)), (.78, (.12, .24, .55))):
    m = fill(np.abs(yy - h * frac) - 4)
    c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array(col, np.float32) * m[..., None]

# ---------------------------------------------------------------- dust station
sy, sx, x, y, w, h, xx, yy = base('dust', (.62, .63, .64), .25, .04, 16, .05)
sd = sd_rrect(xx, yy, w * .22, h * .5, w * .16, h * .34, 6)
s_ = ((yy % 14) < 7) * fill(sd)
c.albedo[sy, sx] *= (1 - s_[..., None] * .85)
c.height[sy, sx] -= s_ * 2.5
c.albedo[sy, sx] *= (1 - np.exp(-np.abs(sd) / 2)[..., None] * .45)
c.add_text('DUST STATION', x + w * .42, y + 12, 24, rgb=(.06, .06, .07))
for j, t in enumerate(('1  BRUSH SUIT', '2  VACUUM SEAMS', '3  WIPE VISOR', '4  CHECK FILTER')):
    c.add_text(t, x + w * .42, y + 54 + j * 30, 17, rgb=(.06, .06, .07))
m = fill(np.abs(sd_rrect(xx, yy, w / 2, h / 2, w / 2 - 4, h / 2 - 4, 4)) - 3) * ((xx + yy) % 18 < 9)
c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array((.8, .63, .1), np.float32) * m[..., None]

# ---------------------------------------------------------------- shelter pad
sy, sx, x, y, w, h, xx, yy = base('shelter', (.74, .46, .20), .06, .05, 17, 0)
fx_, fy_ = (xx % 50) / 50, (yy % 50) / 50
c.height[sy, sx] += np.clip(1 - np.abs(2 * fx_ - 1) ** 3 - np.abs(2 * fy_ - 1) ** 3, 0, 1) * 2.2
dist = np.minimum(np.minimum(fx_, 1 - fx_), np.minimum(fy_, 1 - fy_)) * 50
c.albedo[sy, sx] *= (1 - np.exp(-dist / 1.5)[..., None] * .35)
c.add_text('STORM SHELTER', x + 34, y + h * .38, 34, rgb=(.05, .05, .05), opacity=.9)

# ---------------------------------------------------------------- exercise bike shroud
sy, sx, x, y, w, h, xx, yy = base('bike', (.22, .23, .25), .35, .05, 18, .05)
c.add_text('CEVIS-K', x + 22, y + 22, 26, rgb=(.85, .85, .82))
c.add_text('60 MIN DAILY. NO EXCUSES.', x + 22, y + 66, 15, rgb=(.85, .85, .82))
c.albedo[sy, sx] *= (1 + fill(np.abs(yy - h * .78) - 4)[..., None] * 1.5)

c.save('shab_iva', nstrength=1.0, cavity=.25, target_p90=.78)

# translucent glass pane
g = Canvas(64, 64, albedo=(.72, .82, .9), gloss=.9)
arr = np.dstack([np.clip(g.albedo, 0, 1), np.full((64, 64), .07, np.float32)])
write_dds((arr * 255 + .5).astype(np.uint8), 'shab_ivaglass_diff')
