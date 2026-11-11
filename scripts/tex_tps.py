"""TPS cap sheet: hard white ceramic tiles (paper fig. 2 and 7 show a white shell), unique mapped.
Bottom strip: unrolled cylinder. Top-left: polar crown. Right: liner."""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from tl import *

N = 2048
# geometry shared with build_tps.py
R_OUT = 1.085
Z_LOW, Z_SHOULDER = -1.92, -.30
CIRC = 2 * math.pi * R_OUT
PXM = N / CIRC
STRIP = int((Z_SHOULDER - Z_LOW) * PXM)   # px tall
c = Canvas(N, N, albedo=(.83, .83, .81), gloss=.22)
X, Y = c.x, c.y
r = rng(401)
# --- tiled shell. Square tiles in aligned rows, grouped into bonded arrays like the Shuttle's acreage:
# only whole arrays are offset, because staggering single rows reads as a brick wall.
tw, th = 32.0, 32.0
BW, BH = 8, 6                   # tiles per array
aw, ah = tw * BW, th * BH
brow = np.floor(Y / ah)
xa = X + (brow % 2) * aw / 2
bcol = np.floor(xa / aw)
fa = xa - bcol * aw; ga = Y - brow * ah
row = np.floor(Y / th); ci = np.floor(xa / tw)
fx = xa - ci * tw; fy = Y - row * th
dist = np.minimum(np.minimum(fx, tw - fx), np.minimum(fy, th - fy))
adist = np.minimum(np.minimum(fa, aw - fa), np.minimum(ga, ah - ga))
tone = r.uniform(.995, 1.005, 8192); btone = r.uniform(.985, 1.015, 8192)
idx = ((ci.astype(int) * 57 + row.astype(int) * 131) % 8192)
bidx = ((bcol.astype(int) * 71 + brow.astype(int) * 37) % 8192)
c.albedo *= (tone[idx] * btone[bidx])[..., None]
c.albedo *= (1 - np.exp(-dist / .8)[..., None] * .30)
c.height += fill(1.0 - dist, 1.0) * -1.0   # tile faces stay flat, relief only in the gaps
# array joints: wider, with tan gap filler showing
joint = adist < 1.6
c.albedo[joint] = np.array((.56, .52, .44), np.float32)
c.height += fill(1.8 - adist, 1.0) * -1.2
# a few round access plugs, one per array
pcx = fa - aw * .5 - tw * .5 * 0; pcy = ga - ah * .5
pl = np.hypot(pcx, pcy)
c.albedo *= (1 - np.exp(-np.abs(pl - 5) / .9)[..., None] * .35)
c.height += fill(5 - pl, 1) * .4
gn = grime(N, N, 402, base=9)
c.albedo *= (.97 + .05 * gn)[..., None]
c.height += fbm(N, N, 403, base=350, octaves=2) * .16
# reinforced panel band at the lower skirt
yb = N - .07 * PXM
band = Y > yb
c.albedo[band] = np.array((.62, .62, .63), np.float32) * (.95 + .08 * gn[band])[..., None]
c.height[band] = 0
for dy in (.025, .05):
    y0 = N - dy * PXM
    b = (((X % 36) - 18) ** 2 + (Y - y0) ** 2) < 3 ** 2
    c.height += b * 1.7
c.height += fill(np.abs(Y - yb) - 1.8, 1) * -1.8
c.gloss[band] = .4
# markings
for az in (30, 150, 270):
    x = az / 360 * N
    c.add_text('JETTISON  PLANE', x - 100, N - .17 * PXM, 24, rgb=(.7, .08, .05), opacity=.9)
for az in (70, 250):
    c.add_text('SHAB-01  TPS', az / 360 * N - 120, N - STRIP * .6, 44, rgb=(.08, .08, .09), opacity=.8)
c.add_text('NO STEP', 180 / 360 * N - 40, N - .25 * PXM, 20, rgb=(.1, .1, .1), opacity=.7)
# --- crown (polar, rho by arc length)
D = 1000; cen = D / 2; RHOMAX = 1.75
sy, sx = slice(0, D), slice(0, D)
dx, dy = X[sy, sx] - cen, Y[sy, sx] - cen
rho = np.hypot(dx, dy) / cen * RHOMAX
az = np.degrees(np.arctan2(dx, dy))
c.height[sy, sx] = 0
c.albedo[sy, sx] = np.array((.80, .80, .78), np.float32)
nr = 22
ring = rho * nr
ring_i = np.floor(ring)
nseg = 8 + (ring_i * 4.67).astype(int)
seg = ((az + 180) / 360 * nseg + (ring_i % 2) * .25)
seg_i = np.floor(seg)
fr = ring - ring_i
fs = seg - seg_i
d = np.minimum(np.minimum(fr, 1 - fr) * cen / RHOMAX / nr * 1.0, np.minimum(fs, 1 - fs) * (2 * math.pi * rho * cen / RHOMAX) / nseg)
c.albedo[sy, sx] *= (1 - np.exp(-d / 1.3)[..., None] * .55)
c.height[sy, sx] += -fill(1.5 - d, 1) * 1.2
tid = ((ring_i * 91 + seg_i * 17).astype(int) % 8192)
c.albedo[sy, sx] *= tone[tid][..., None]
# --- inner liner at the top right: silvered foil
x0, y0, w, h = 1024, 0, 1024, 512
sy2, sx2 = slice(y0, y0 + h), slice(x0, x0 + w)
c.height[sy2, sx2] = 0
sh, ht, ed = facet_foil(h, w, 411, cells=46)
c.albedo[sy2, sx2] = np.array((.58, .59, .62), np.float32) * (.6 + .6 * shade_mix if False else .55 + .6 * sh)[..., None] if False else np.array((.58, .59, .62), np.float32) * (.55 + .6 * sh)[..., None]
c.gloss[sy2, sx2] = .55
c.height[sy2, sx2] += blur(ht, .7) * 1.2
p = os.path.join(OUT, 'ao_shab_tps.png')
if os.path.exists(p):
    ao = np.asarray(Image.open(p).convert('L')).astype(np.float32) / 255
    c.ao = np.clip(blur(ao, .8), .15, 1) ** .9
    print('applied AO')
c.save('shab_tps', nstrength=.9, cavity=.2, target_p90=.78)
