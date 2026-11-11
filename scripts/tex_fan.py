"""UltraFlex fan sheet: one gore's cell side and back as wedges, hub face. 1024 px."""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from tl import *
import sm_layout as L

N = L.FAN_ATLAS
c = Canvas(N, N, albedo=(.62, .62, .63), gloss=.3)
X, Y = c.x, c.y
PP = L.FAN_PPM
half = math.radians(180.0 / L.FAN_N)
c.height[:] = 0

# ---- front: cell wedge
lat = (X - L.FRONT_CX) / PP            # image lateral in metres (mirrored in UV helper)
rad = (L.APEX_Y - Y) / PP
ang = np.arctan2(np.abs(lat), np.maximum(rad, 1e-3))
inside = (ang <= half + .004) & (rad > .05) & (rad <= L.FAN_R * 1.0) & (np.abs(X - L.FRONT_CX) < 180)
margin = .02
dist_edge = (rad * np.sin(half) - np.abs(lat)) * np.cos(half)     # metres to the radial edge
kapton = np.array((.78, .66, .36), np.float32)
c.albedo[inside] = kapton
c.gloss[inside] = .4
# cell block: rows across the gore, rectangular cells aligned to the gore axis
cell_w, cell_h = .068, .054
row = np.floor(rad / cell_h)
col = np.floor(lat / cell_w + .5)
hash_ = ((row * 73 + col * 151).astype(np.int64)) % 997
tone = rng(501).uniform(.82, 1.18, 997)[hash_]
cells = inside & (dist_edge > margin) & (rad > .18) & (rad < L.FAN_R - .045)
blue = np.array((.028, .050, .125), np.float32)
c.albedo[cells] = blue * tone[cells][..., None]
c.gloss[cells] = .86
# interconnect: thin silver lines between cells, finger pattern across each cell
fy = (rad / cell_h) % 1; fx = (lat / cell_w + .5) % 1
gap = ((fy < .045) | (fy > .955) | (fx < .04) | (fx > .96)) & cells
c.albedo[gap] = (.27, .28, .32)
c.gloss[gap] = .6
c.height += blur(gap.astype(np.float32), .5) * -.5
fing = (((fy * 9) % 1) < .10) & cells & ~gap
c.albedo[fing] += .022
# bus strips every 8 rows
bus = ((np.floor(rad / cell_h) % 8) == 0) & (fy > .35) & (fy < .65) & cells
c.albedo[bus] = (.40, .40, .43)
c.gloss[bus] = .55
# tensioning spoke on the gore centre line and edge tape
spoke = (np.abs(lat) * PP < 1.1) & inside
c.albedo[spoke] = (.86, .86, .84)
c.height += blur(spoke.astype(np.float32), .6) * 1.0
tape = inside & (dist_edge < .012)
c.albedo[tape] = (.90, .90, .88)
c.gloss[tape] = .3
rim = inside & (rad > L.FAN_R - .035)
c.albedo[rim] = (.90, .90, .88)
c.height += blur(tape.astype(np.float32), .7) * 1.0 + blur(rim.astype(np.float32), .7) * 1.0
# gentle slack: each gore ripples a little between tie points, seen as big soft normals
ripple = np.sin(rad * 2 * np.pi / .42) * .7 + fbm(N, N, 502, base=6, octaves=2) * .4
c.height += ripple * inside * 1.0

# ---- back: grey kapton mesh with wire runs
lat2 = (X - L.BACK_CX) / PP
ang2 = np.arctan2(np.abs(lat2), np.maximum(rad, 1e-3))
in2 = (ang2 <= half + .004) & (rad > .05) & (rad <= L.FAN_R) & (np.abs(X - L.BACK_CX) < 180)
n = grime(N, N, 503, base=10)
c.albedo[in2] = (np.array((.60, .60, .60), np.float32) * (.92 + .16 * n[..., None]))[in2]
c.gloss[in2] = .22
mesh_ = (((lat2 * 90) % 1 < .12) | ((rad * 90) % 1 < .12)) & in2
c.albedo[mesh_] *= .85
wires = (np.abs(((lat2 * PP + 24) % 48) - 24) < 1.2) & in2 & (rad > .15) & (rad < L.FAN_R - .05)
c.albedo[wires] = (.70, .55, .28)
c.height += blur(wires.astype(np.float32), .6) * 1.2
dist2 = (rad * np.sin(half) - np.abs(lat2)) * np.cos(half)
tape2 = in2 & ((dist2 < .012) | (rad > L.FAN_R - .035))
c.albedo[tape2] = (.84, .84, .82)
c.height += blur(tape2.astype(np.float32), .7) * 1.0

# ---- hub face
cx, cy, rp, rm = L.HUB_POLAR
d = np.hypot(X - cx, Y - cy)
hub = d < rp + 4
c.albedo[hub] = (.90, .90, .90)
c.gloss[hub] = .45
c.height[hub] = 0
for rr_, w_ in ((.92, 7), (.62, 5), (.30, 5)):
    ringd = np.abs(d - rr_ * rp)
    c.height += fill(ringd - w_, 1.2) * 2.6 * hub
    c.albedo *= (1 - np.exp(-ringd / 2.2)[..., None] * .35 * hub[..., None])
az = np.degrees(np.arctan2(X - cx, Y - cy))
angb = (az % 18) - 9
b = ((d - .78 * rp) ** 2 + (angb * math.pi / 180 * .78 * rp) ** 2) < 5.5 ** 2
c.height += (b & hub) * 2.4
c.albedo[b & hub] = (.50, .50, .52)
core = d < .30 * rp
c.albedo[core] = (.20, .20, .22)
c.add_text('ULTRAFLEX', cx - 58, cy + 72, 20, rgb=(.1, .1, .12), opacity=.8)

c.save('shab_fan', nstrength=1.0, cavity=.15)
