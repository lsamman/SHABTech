"""Methalox engine sheet (shab_engine_diff/nrm, 1024 px): regen nozzle, copper chamber, powerhead trim.
Not a painted hull, so no Bluedog look pass. Zones in engine_layout.py."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from tl import *
from engine_layout import ENG, ATLAS, RIBS, T_THROAT

N = ATLAS
c = Canvas(N, N, albedo=(.40, .40, .41), gloss=.4)
X, Y = c.x, c.y


def box(k):
    x, y, w, h = ENG[k]
    return slice(y, y + h), slice(x, x + w), x, y, w, h


def ramp(t, stops):
    """Colour ramp: stops = [(t, rgb), ...] ascending in t."""
    ts = np.array([s[0] for s in stops], np.float32)
    out = np.empty(t.shape + (3,), np.float32)
    for k in range(3):
        out[..., k] = np.interp(t, ts, [s[1][k] for s in stops])
    return out


def channels(xx, period):
    """Coolant channel crowns across x: 1 on the crown, 0 in the braze line."""
    f = (xx % period) / period
    return np.clip(np.sin(np.pi * f) * 1.35, 0, 1) ** .6


# ---- nozzle outside: dark channel wall, crowns catch the light
sy, sx, x, y, w, h = box('bell')
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
t = 1 - yy / h                                    # 0 at the exit, 1 at the top
per = w / RIBS
cr = channels(xx, per)
c.height[sy, sx] = cr * 1.6
c.albedo[sy, sx] = ramp(t, [(0, (.13, .13, .14)), (.7, (.16, .155, .155)), (1, (.20, .17, .15))])
c.albedo[sy, sx] *= (.78 + .30 * cr)[..., None]
c.gloss[sy, sx] = .42 + .16 * cr
# the zone's edges sit under the manifold and the exit ring: a plain land there
land = (yy < 4) | (yy > h - 4)
c.height[sy, sx] = np.where(land, 1.0, c.height[sy, sx])

# ---- nozzle inside: smooth, near black at the exit, warm bronze toward the throat
sy, sx, x, y, w, h = box('bell_in')
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
t = 1 - yy / h
c.albedo[sy, sx] = ramp(t, [(0, (.07, .07, .075)), (.55, (.11, .10, .10)), (.85, (.24, .16, .11)), (1, (.30, .19, .12))])
c.gloss[sy, sx] = .30 + .25 * t
c.height[sy, sx] = channels(xx, w / RIBS) * .35

# ---- copper chamber and throat, faint heat tint around the throat
sy, sx, x, y, w, h = box('chamber')
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
t = 1 - yy / h
d = (t - T_THROAT)
heat = np.exp(-(d / .16) ** 2)
cu = ramp(t, [(0, (.55, .33, .20)), (T_THROAT, (.60, .34, .22)), (1, (.76, .47, .27))])
tint = np.array((.50, .32, .36), np.float32)       # faint violet where it ran hottest
c.albedo[sy, sx] = cu * (1 - .30 * heat[..., None]) + tint * .30 * heat[..., None]
straw = np.exp(-((d - .14) / .07) ** 2)             # straw band just above it
c.albedo[sy, sx] += np.array((.05, .04, -.01), np.float32) * straw[..., None]
c.gloss[sy, sx] = .58 - .12 * heat
# braze lines and the chamber's girth welds
for tw in (.62, .86):
    m = np.abs(t - tw) * h < 1.6
    c.height[sy, sx] += m * 1.4
    c.albedo[sy, sx] *= (1 - m * .18)[..., None]
c.height[sy, sx] += channels(xx, w / (RIBS // 2)) * .25 * (t < T_THROAT)

# ---- plain metals
def plain(k, rgb, gloss, rings=()):
    sy, sx, x, y, w, h = box(k)
    yy = Y[sy, sx] - y
    c.albedo[sy, sx] = np.array(rgb, np.float32)
    c.gloss[sy, sx] = gloss
    for f in rings:
        m = np.abs(yy - h * f) < 1.5
        c.height[sy, sx] += m * 1.5
        c.albedo[sy, sx] *= (1 - m * .25)[..., None]
    return sy, sx, x, y, w, h

plain('steel', (.52, .52, .53), .55, rings=(.5,))
plain('dark', (.20, .20, .21), .38)
sy, sx, x, y, w, h = plain('tint', (.62, .60, .58), .55)
t = 1 - (Y[sy, sx] - y) / h
c.albedo[sy, sx] = ramp(t, [(0, (.42, .42, .43)), (.35, (.46, .41, .33)), (.6, (.42, .33, .27)), (.8, (.32, .29, .36)), (1, (.34, .35, .40))])

# ---- hat bands: dark ring with a raised land and a fine edge line
sy, sx, x, y, w, h = plain('band', (.22, .22, .23), .45)
yy = Y[sy, sx] - y
land = np.abs(yy - h / 2) < h * .28
c.height[sy, sx] += blur(land.astype(np.float32), 1.0) * 2.0
c.albedo[sy, sx] *= (1 + .10 * land)[..., None]

# ---- bolted flange
sy, sx, x, y, w, h = plain('flange', (.48, .48, .49), .5)
xx, yy = X[sy, sx] - x, Y[sy, sx] - y
pitch = w / 64
bx = (xx % pitch) - pitch / 2
bolt = fill(np.hypot(bx, yy - h / 2) - 4.2, 1.0)
c.height[sy, sx] += bevel(np.hypot(bx, yy - h / 2) - 4.2, 2.5) * 2.0
c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - bolt[..., None] * .35) + np.array((.62, .62, .63), np.float32) * bolt[..., None] * .35
for e in (3, h - 3):
    m = np.abs(yy - e) < 1.2
    c.albedo[sy, sx] *= (1 - m * .3)[..., None]

# ---- bellows convolutions across t
sy, sx, x, y, w, h = plain('bellows', (.50, .50, .51), .6)
yy = Y[sy, sx] - y
cv = np.sin(yy * 2 * np.pi / 8) * .5 + .5
c.height[sy, sx] += cv * 2.2
c.albedo[sy, sx] *= (.72 + .36 * cv)[..., None]

# ---- duct: bare steel with weld bands
sy, sx, x, y, w, h = plain('duct', (.46, .46, .47), .58)
yy = Y[sy, sx] - y
m = (yy % 64) < 3
c.height[sy, sx] += m * 1.2
c.albedo[sy, sx] *= (1 - m * .2)[..., None]

c.save('shab_engine', nstrength=1.0, cavity=.25)
