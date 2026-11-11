"""Paint the shared details atlas (shab_details_diff/nrm): every greeble's material lives here."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from tl import *
from layout import DET

N = 2048
c = Canvas(N, N, albedo=(.5, .5, .5), gloss=.3)
X, Y = c.x, c.y
R = {k: v for k, v in DET.items()}

def box(k):
    x, y, w, h = R[k]
    return slice(y, y + h), slice(x, x + w), x, y, w, h

def base(k, rgb, gloss, mottle=.04, seed=0, scratch=0.0):
    sy, sx, x, y, w, h = box(k)
    n = grime(h, w, seed + hash(k) % 1000, base=6)
    a = np.array(rgb, np.float32)[None, None] * (1 - mottle + 2 * mottle * n[..., None])
    c.albedo[sy, sx] = a
    c.gloss[sy, sx] = gloss
    if scratch:
        s = scratches(h, w, seed + 7, n=int(h * w / 500), bright=1)
        c.albedo[sy, sx] += s[..., None] * scratch
    # tiny surface grain so even plain metals catch the light
    c.height[sy, sx] += fbm(h, w, seed + 3, base=max(w, h) // 8, octaves=3) * .08

base('white', (.86, .86, .85), .28, .03, 1, .03)
base('grey', (.56, .57, .59), .32, .04, 2, .04)
base('dark', (.17, .17, .18), .35, .06, 3, .05)
base('bare', (.66, .66, .68), .62, .05, 4, .08)
base('black', (.035, .035, .04), .25, .1, 5)
base('gold', (.66, .52, .28), .6, .05, 6, .06)
base('yellow', (.80, .64, .16), .36, .05, 7, .05)
base('copper', (.72, .42, .22), .55, .06, 8, .05)
base('rubber', (.06, .06, .06), .08, .1, 9)
base('orange', (.84, .38, .08), .3, .04, 10)
base('glass', (.05, .10, .16), .92, .02, 11)
base('red', (.72, .08, .06), .35, .04, 12)
base('blue', (.08, .20, .46), .35, .04, 13)
base('steel', (.44, .45, .47), .7, .06, 14, .1)
base('lens', (.86, .90, .96), .9, .02, 15)
base('lamp', (.98, .95, .82), .4, .01, 16)

# --- woven Kevlar straps (HIAD)
sy, sx, x, y, w, h = box('kevlar')
base('kevlar', (.86, .70, .22), .18, .05, 17)
wv = weave(X[sy, sx], Y[sy, sx], 4.0)
c.height[sy, sx] += wv * .9
c.albedo[sy, sx] *= (.82 + .3 * wv)[..., None]

# --- hazard stripes
for k, seed in (('hazard', 21), ('hazard2', 22)):
    sy, sx, x, y, w, h = box(k)
    base(k, (.82, .66, .10), .32, .03, seed)
    d = ((X[sy, sx] + Y[sy, sx]) % 48) < 24
    c.albedo[sy, sx] = np.where(d[..., None], c.albedo[sy, sx], np.array((.05, .05, .05), np.float32))

# --- foil and blankets
def foil(k, tint, seed, gloss=.72, low=.5, high=1.2):
    sy, sx, x, y, w, h = box(k)
    shade, ht, ed = facet_foil(h, w, seed, cells=46)
    shade = .5 + (shade - .5) * .55 + crinkle(h, w, seed + 9, scale=40) * .25 - .1
    big = grime(h, w, seed + 5, base=3)
    s = low + (high - low) * np.clip(shade * .85 + big * .2, 0, 1)
    s *= 1 - ed * .25
    s += (ed > .7) * .10                                  # bright crease highlights
    c.albedo[sy, sx] = np.array(tint, np.float32)[None, None] * s[..., None]
    c.gloss[sy, sx] = gloss * (.6 + .5 * shade)
    c.height[sy, sx] += blur(ht, .7) * 1.2
    for frac in (0.25, 0.75):
        mx = np.abs(Y[sy, sx] - (y + h * frac)) < 1.2
        pat = ((X[sy, sx] // 10) % 2 == 0)
        c.albedo[sy, sx] = np.where((mx & pat)[..., None], c.albedo[sy, sx] * .55, c.albedo[sy, sx])
        c.height[sy, sx] -= (mx & pat) * .6

foil('mli_gold', (.82, .60, .22), 31)
foil('mli_silver', (.80, .81, .84), 32)
foil('mli_black', (.09, .09, .10), 33, gloss=.3, low=.7, high=1.2)
foil('foil_dark', (.42, .36, .24), 34, gloss=.45)

sy, sx, x, y, w, h = box('beta')
base('beta', (.86, .85, .80), .12, .03, 35)
wv = weave(X[sy, sx], Y[sy, sx], 3.0)
c.height[sy, sx] += wv * .6 + crinkle(h, w, 36, scale=16) * 1.2
c.albedo[sy, sx] *= (.92 + .12 * wv)[..., None]

# --- FIB tile and ablator trim
sy, sx, x, y, w, h = box('tile')
base('tile', (.87, .87, .84), .10, .03, 41)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
cell = 64
fx, fy = (xx % cell) - cell / 2, (yy % cell) - cell / 2
sd = np.maximum(np.abs(fx), np.abs(fy)) - (cell / 2 - 1.5)
pillow = np.clip(1 - (np.abs(fx) / (cell / 2)) ** 3 - (np.abs(fy) / (cell / 2)) ** 3, 0, 1)
c.height[sy, sx] += pillow * 3.5 + weave(xx, yy, 3.0) * .25
c.albedo[sy, sx] *= (1 - fill(sd + 2.0)[..., None] * 0 - (1 - fill(sd)) [..., None] * .55)
r = rng(42); ids = (np.floor(xx / cell) + np.floor(yy / cell) * 37).astype(int)
vals = r.uniform(.93, 1.04, 8000)
c.albedo[sy, sx] *= vals[ids % 8000][..., None]

sy, sx, x, y, w, h = box('ablator')
base('ablator', (.20, .17, .14), .08, .12, 43)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
# Avcoat-style honeycomb
s = 11.0; col = np.round(xx / (s * 1.732)); row = np.round((yy - (col % 2) * s) / (s * 2))
hx = xx - col * s * 1.732; hy = yy - row * s * 2 - (col % 2) * s
d = np.maximum(np.abs(hx) * 0.866 + np.abs(hy) * .5, np.abs(hy)) - s * .90
c.height[sy, sx] += fill(d, 1.5) * 1.1 + fbm(h, w, 44, base=30, octaves=3) * .5
c.albedo[sy, sx] *= (.72 + .36 * fill(d, 1.5))[..., None]
c.albedo[sy, sx] *= (.85 + .3 * grime(h, w, 45, base=4))[..., None]

# --- functional panels
sy, sx, x, y, w, h = box('vent')
base('vent', (.5, .5, .52), .3, .03, 51)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
slats = ((yy % 22) < 12) & (np.abs(xx - w / 2) < w / 2 - 22) & (np.abs(yy - h / 2) < h / 2 - 22)
c.albedo[sy, sx] = np.where(slats[..., None], c.albedo[sy, sx] * .12, c.albedo[sy, sx])
c.height[sy, sx] -= blur(slats.astype(np.float32), 1.0) * 4
for fx_ in (14, w - 14):
    for fy_ in (14, h - 14):
        c.height[sy, sx] += fill(sd_circle(xx, yy, fx_, fy_, 5), 1) * 2

sy, sx, x, y, w, h = box('louver')
base('louver', (.78, .79, .80), .55, .03, 52)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
sl = (yy % 26) / 26
c.height[sy, sx] += sl * 4
c.albedo[sy, sx] *= (.6 + .55 * sl)[..., None]

sy, sx, x, y, w, h = box('grating')
base('grating', (.32, .32, .34), .35, .03, 53)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
g = ((xx % 16) < 4) | ((yy % 16) < 4)
c.albedo[sy, sx] = np.where(g[..., None], c.albedo[sy, sx], np.array((.03, .03, .03), np.float32))
c.height[sy, sx] += blur(g.astype(np.float32), .6) * 3

sy, sx, x, y, w, h = box('connector')
base('connector', (.30, .31, .33), .4, .04, 54)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
rr = rng(55)
for j in range(4):
    for i in range(4):
        cx, cy = 34 + i * 62, 34 + j * 62
        c.height[sy, sx] += bevel(sd_circle(xx, yy, cx, cy, 24), 6) * 5 - bevel(sd_circle(xx, yy, cx, cy, 13), 3) * 5
        m = fill(sd_circle(xx, yy, cx, cy, 13))
        col = np.array((.72, .55, .22) if rr.random() < .5 else (.05, .05, .05), np.float32)
        c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + col * m[..., None]

sy, sx, x, y, w, h = box('access')
base('access', (.7, .7, .7), .3, .04, 56, .05)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
sd = sd_rrect(xx, yy, w / 2, h / 2, w / 2 - 12, h / 2 - 12, 10)
c.height[sy, sx] += -bevel(sd, 4) * 2.5
c.albedo[sy, sx] *= (1 - np.exp(-np.abs(sd) / 2.0)[..., None] * .5)
for a_ in np.linspace(0, 1, 6)[:-1]:
    for (fx_, fy_) in ((24 + a_ * (w - 48), 24), (w - 24, 24 + a_ * (h - 48)), (w - 24 - a_ * (w - 48), h - 24), (24, h - 24 - a_ * (h - 48))):
        c.height[sy, sx] += fill(sd_circle(xx, yy, fx_, fy_, 4), 1) * 1.8

sy, sx, x, y, w, h = box('radpanel')
base('radpanel', (.90, .90, .88), .4, .02, 57)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
tubes = (np.sin(xx * 2 * np.pi / 28) * .5 + .5) ** 3
c.height[sy, sx] += tubes * 2.2
c.albedo[sy, sx] *= (.92 + .1 * tubes)[..., None]

# --- solar cells: fan-gore compatible, dark blue with silver bus bars
sy, sx, x, y, w, h = box('solar')
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
n = fbm(h, w, 61, base=8, octaves=3)
c.albedo[sy, sx] = np.array((.035, .055, .13), np.float32) * (1 + .15 * n[..., None])
c.gloss[sy, sx] = .82
cx_ = 64
gap = ((xx % cx_) < 3) | ((yy % cx_) < 3)
c.albedo[sy, sx] = np.where(gap[..., None], np.array((.42, .44, .48), np.float32), c.albedo[sy, sx])
fing = ((xx % 8) < 1)
c.albedo[sy, sx] += (fing & ~gap)[..., None] * np.array((.025, .03, .04), np.float32)
c.height[sy, sx] += blur(gap.astype(np.float32), .7) * -.7

# --- pressure vessels
for k, rgb, seed, glossy in (('tank_white', (.86, .86, .84), 71, .3), ('tank_grey', (.55, .56, .58), 72, .4)):
    sy, sx, x, y, w, h = box(k)
    base(k, rgb, glossy, .04, seed, .03)
    xx, yy = X[sy, sx] - x, Y[sy, sx] - y
    for frac in (.125, .375, .625, .875):
        d = np.abs(yy - h * frac) - 2
        c.height[sy, sx] += fill(d, 1.2) * 2.5
    bolts = (((xx % 32) - 16) ** 2 + ((yy % (h / 4)) - h / 8) ** 2) < 3.5 ** 2
    c.height[sy, sx] += bolts * 1.5

sy, sx, x, y, w, h = box('copv')
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
base('copv', (.09, .09, .10), .4, .05, 73)
wv = np.sin((xx + yy) * 2 * np.pi / 6) * np.sin((xx - yy) * 2 * np.pi / 6)
c.height[sy, sx] += wv * .9
c.albedo[sy, sx] *= (1 + .25 * wv)[..., None]
sy, sx, x, y, w, h = box('wrap')
base('wrap', (.75, .72, .62), .25, .05, 74)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
c.height[sy, sx] += (np.sin(yy * 2 * np.pi / 6) * .5 + .5) * 1.2

# --- engine bell: outside regen ribs, inside dark with soot
sy, sx, x, y, w, h = box('nozzle')
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
base('nozzle', (.40, .38, .36), .5, .08, 75, .04)
ribs = (xx % 6) < 2.4
c.height[sy, sx] += blur(ribs.astype(np.float32), .6) * 1.4
c.albedo[sy, sx] *= (.82 + .25 * ribs)[..., None]
heat = np.clip(yy / h, 0, 1)
sy, sx, x, y, w, h = box('nozzle_in')
base('nozzle_in', (.10, .09, .08), .3, .12, 76)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
c.albedo[sy, sx] *= (.6 + .9 * (yy / h))[..., None]
c.height[sy, sx] += ((xx % 8) < 2) * .7

# --- lander skin and deck plate
sy, sx, x, y, w, h = box('lander_panel')
base('lander_panel', (.80, .80, .79), .28, .04, 81, .05)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
for cxp in (w * .25, w * .75):
    sd = sd_rrect(xx, yy, cxp, h / 2, w / 4 - 8, h / 2 - 8, 8)
    c.height[sy, sx] += bevel(sd, 4) * 2.2 - bevel(sd + 16, 3) * 1.4
    c.albedo[sy, sx] *= (1 - np.exp(-np.abs(sd) / 1.6)[..., None] * .55)
c.height[sy, sx] += ((((xx % 28) - 14) ** 2 + ((yy % 28) - 14) ** 2) < 7) * .9

sy, sx, x, y, w, h = box('deck')
base('deck', (.30, .31, .32), .35, .05, 82, .07)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
d = ((xx + (yy // 18) % 2 * 9) % 18 - 9) ** 2 + ((yy % 18) - 9) ** 2 * 6
c.height[sy, sx] += (d < 40) * 1.2                    # tread plate
c.albedo[sy, sx] *= (.85 + .3 * (d < 40))[..., None]

sy, sx, x, y, w, h = box('hex')
base('hex', (.62, .63, .65), .4, .04, 83)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
s = 10.0; col = np.round(xx / (s * 1.732)); row = np.round((yy - (col % 2) * s) / (s * 2))
hx = xx - col * s * 1.732; hy = yy - row * s * 2 - (col % 2) * s
dd = np.maximum(np.abs(hx) * .866 + np.abs(hy) * .5, np.abs(hy)) - s * .8
c.height[sy, sx] += fill(dd, 1) * 1.8
c.albedo[sy, sx] *= (.5 + .55 * fill(dd, 1))[..., None]

sy, sx, x, y, w, h = box('nomex')
base('nomex', (.82, .82, .78), .12, .03, 84)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
wv = weave(xx, yy, 5.0)
c.height[sy, sx] += wv * .5 + crinkle(h, w, 85, scale=20) * 1.5
c.albedo[sy, sx] *= (.92 + .12 * wv)[..., None]

sy, sx, x, y, w, h = box('plumbing')
base('plumbing', (.5, .5, .52), .55, .05, 86, .06)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
c.height[sy, sx] += ((yy % 40) < 6) * 1.5
c.albedo[sy, sx] *= (.8 + .3 * ((yy % 40) < 6))[..., None]

# --- targets and stencils
sy, sx, x, y, w, h = box('target')
base('target', (.92, .92, .90), .2, .01, 91)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
m = fill(sd_circle(xx, yy, w / 2, h / 2, w * .2))
c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array((.03, .03, .03), np.float32) * m[..., None]

sy, sx, x, y, w, h = box('logo')
base('logo', (.88, .88, .86), .2, .02, 92)
c.add_text('SHAB-01', x + 18, y + 30, 66, rgb=(.08, .08, .09))
c.add_text('MARS SURFACE HABITAT', x + 20, y + 98, 22, rgb=(.08, .08, .09))
sy, sx, x, y, w, h = box('stencil')
base('stencil', (.72, .72, .72), .25, .02, 93)
c.add_text('CAUTION  NO STEP', x + 10, y + 8, 22)
c.add_text('EVA HANDHOLD', x + 280, y + 8, 22)
c.add_text('N2 VENT  •  KEEP CLEAR', x + 10, y + 40, 22)
c.add_text('QD-3 H2O', x + 340, y + 40, 22)
c.add_text('RESCUE  PULL', x + 10, y + 74, 22, rgb=(.7, .08, .05))
c.add_text('CH4', x + 300, y + 74, 22); c.add_text('LOX', x + 380, y + 74, 22)

c.save('shab_details', nstrength=1.1, cavity=.35)
