"""Lander sheet (shab_lander): deck top polar, underside polar, one 60 degree wall sector, trim."""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from tl import *
import ll as L

N = 2048
c = Canvas(N, N, albedo=(.78, .78, .77), gloss=.28)
X, Y = c.x, c.y


def polar(zone, rmax):
    x0, y0, w, h = zone
    sy, sx = slice(y0, y0 + h), slice(x0, x0 + w)
    dx, dy = X[sy, sx] - x0 - w / 2, Y[sy, sx] - y0 - h / 2
    rr = np.hypot(dx, dy) / (w / 2) * rmax
    az = np.degrees(np.arctan2(dx, dy))
    return sy, sx, rr, az, (w / 2) / rmax    # px per metre


def ring_bolts(H, A, rr, az, ppm, r, n, size=2.6, gain=1.4, dark=.25):
    ang = (az % (360 / n)) - 180 / n
    d = np.hypot((rr - r) * ppm, np.radians(ang) * rr * ppm)
    H += fill(d - size, .8) * gain
    A *= (1 - fill(d - size - 1.5, 1)[..., None] * dark)


# ------------------------------------------------------------ deck top
sy, sx, rr, az, ppm = polar(L.TOP, L.TOP_RMAX)
h, w = rr.shape
A = np.ones((h, w, 3), np.float32) * np.array((.78, .78, .765), np.float32)
A *= (.95 + .09 * grime(h, w, 401, base=5))[..., None]
H = fbm(h, w, 402, base=180, octaves=2) * .1
G = np.full((h, w), .30, np.float32)
# sector plating: every 15 degrees out to the rim, ring seams
for r0, r1, n, rseed in ((1.70, 2.48, 24, 1), (.92, 1.20, 24, 2)):
    band = (rr > r0) & (rr < r1)
    sa = np.abs(((az + 7.5) % (360 / n)) - 7.5 * 24 / n) * np.pi / 180 * rr * ppm
    seam = np.exp(-sa / 1.4) * band
    A *= (1 - seam[..., None] * .45)
    H -= seam * 1.2
    # per-plate tone
    idx = np.floor((az + 180) / (360 / n)).astype(int) % n
    t = rng(403 + rseed).uniform(.965, 1.035, n)
    A = np.where(band[..., None], A * t[idx][..., None], A)
for r0 in (.90, 1.20, 1.70, 2.48):
    d = np.abs(rr - r0) * ppm
    A *= (1 - np.exp(-d / 1.5)[..., None] * .5)
    H += fill(d - 2.5, 1) * 1.6
for r0, n in ((.94, 48), (1.17, 48), (1.73, 96), (2.45, 120)):
    ring_bolts(H, A, rr, az, ppm, r0, n)
# outer field: raised access plates with fasteners
for i in range(12):
    azc = 7.5 + 30 * i
    ang = ((az - azc + 180) % 360 - 180)
    d = np.maximum(np.abs(rr - 2.09) - .24, (np.abs(ang) - 5.2) * np.pi / 180 * rr) * ppm
    H += bevel(d, 3) * 1.5
    A *= (1 - np.exp(-np.abs(d) / 1.8)[..., None] * .42)
    A = np.where((d < 0)[..., None], A * .97, A)
# walkway: tread plate with yellow edges
wk = (rr > 1.23) & (rr < 1.67)
tx = rr * 26; ty = np.radians(az + 180) * 1.45 * 26
d1 = (((tx % 1) - .5) * 1.0) ** 2 + (((ty + np.floor(tx)) % 1 - .5) * .35) ** 2
tread = (d1 < .08) & wk
A = np.where(wk[..., None], np.array((.33, .335, .345), np.float32) * (.9 + .14 * grime(h, w, 404, base=14))[..., None], A)
A = np.where(tread[..., None], A * 1.32, A)
H += blur(tread.astype(np.float32), .7) * 1.6
G = np.where(wk, .42, G)
for r0 in (1.25, 1.65):
    d = np.abs(rr - r0) * ppm
    m = fill(d - 3.5, 1)
    A = A * (1 - m[..., None]) + np.array((.80, .64, .14), np.float32) * m[..., None]
    H += m * .4
# ladder landing, azimuth 0: hazard chevrons on the walkway
ang = (az + 180) % 360 - 180
pad = (np.abs(ang) < 15) & (rr > 1.28) & (rr < 1.62)
chev = (((rr * 11 + np.abs(ang) * .22) % 1) < .5)
A = np.where((pad & chev)[..., None], np.array((.80, .64, .14), np.float32), A)
A = np.where((pad & ~chev)[..., None], np.array((.05, .05, .05), np.float32), A)
# inner ring: bare metal around the PCM mount
inner = rr < 1.20
A = np.where(inner[..., None], A * np.array((.86, .87, .90), np.float32), A)
G = np.where(inner, .48, G)
# soft staining and scuffing along foot traffic
A += scratches(h, w, 405, n=900, length=(8, 60))[..., None] * .05
A *= (1 - (smooth(1.6, 2.5, rr) * .05 * grime(h, w, 406, base=20))[..., None])
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = G

# ------------------------------------------------------------ underside: dark foil and thrust structure
sy, sx, rr, az, ppm = polar(L.UNDER, L.UNDER_RMAX)
h, w = rr.shape
shade, ht, ed = facet_foil(h, w, 411, cells=24)
A = np.array((.11, .105, .10), np.float32) * (.8 + .5 * shade[..., None])
H = blur(ht, .6) * .5
G = np.full((h, w), .35, np.float32)
hub = rr < .78
A = np.where(hub[..., None], np.array((.20, .20, .21), np.float32) * (.85 + .3 * grime(h, w, 412, base=8))[..., None], A)
for r0 in (.78, 1.65, 2.48):
    d = np.abs(rr - r0) * ppm
    A *= (1 - np.exp(-d / 1.6)[..., None] * .5)
    H += fill(d - 2.2, 1) * 1.4
ring_bolts(H, A, rr, az, ppm, 1.62, 72, size=2.0)
# engine mounts: soot pattern around each of the eight wells
ang8 = ((az + 22.5) % 45) - 22.5
dx8 = np.hypot((rr - L.ENGINE_R), np.radians(ang8) * rr) * ppm
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = G

# ------------------------------------------------------------ deck wall sector
x0, y0, w, h = L.SIDE
sy, sx = slice(y0, y0 + h), slice(x0, x0 + w)
xx, yy = X[sy, sx] - x0, Y[sy, sx] - y0
ppm = h / 1.3
z_px = lambda z: (L.DECK_TOP - z) * ppm
# MLI blanket: soft pillowing and shallow wrinkles, no hard facets at this viewing distance
soft = crinkle(h, w, 422, scale=22, sharp=1.4)
big = grime(h, w, 423, base=5)
shade = np.clip(soft * .6 + big * .5, 0, 1)
A = np.array((.84, .84, .82), np.float32) * (.90 + .14 * shade[..., None])
H = blur(soft, 1.5) * .9 + weave(xx, yy, 3.0) * .10
G = (.16 + .08 * shade).astype(np.float32)
# one gold thermal panel beside the leg mount, typical for a tank bay
for ga, gb in ((.70, .90),):
    gm = ((xx / w) > ga) & ((xx / w) < gb) & (yy > z_px(.42)) & (yy < z_px(-.40))
    A = np.where(gm[..., None], np.array((.74, .55, .22), np.float32) * (.72 + .50 * shade[..., None]), A)
    G = np.where(gm, .62, G)
# ring frames and longerons, bolted
for z0, half in ((.625, 10), (.02, 8), (-.625, 10)):
    yc = z_px(z0)
    m = fill(np.abs(yy - yc) - half)
    A = A * (1 - m[..., None]) + np.array((.76, .76, .75), np.float32) * m[..., None]
    H += bevel(np.abs(yy - yc) - half, 2.0) * 2.0
    G = G * (1 - m) + .3 * m
    A *= (1 - np.exp(-np.abs(np.abs(yy - yc) - half) / 2.2)[..., None] * .4)
    b = (((xx % 22) - 11) ** 2 + (yy - yc) ** 2) < 2.3 ** 2
    H += b * 1.2
for s0 in (.25, .75):
    xc = s0 * w
    m = fill(np.abs(xx - xc) - 7)
    A = A * (1 - m[..., None]) + np.array((.74, .74, .73), np.float32) * m[..., None]
    H += bevel(np.abs(xx - xc) - 7, 2) * 1.8
    A *= (1 - np.exp(-np.abs(np.abs(xx - xc) - 7) / 2)[..., None] * .35)
    b = ((xx - xc) ** 2 + ((yy % 24) - 12) ** 2) < 2.2 ** 2
    H += b * 1.2
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = G
c.add_text('CH4 BAY', x0 + 40, y0 + z_px(.40), 26, rgb=(.08, .08, .09), opacity=.85)
c.add_text('LOX BAY', x0 + w * .78, y0 + z_px(.40), 26, rgb=(.08, .08, .09), opacity=.85)
c.add_text('NO STEP', x0 + 300, y0 + z_px(-.05), 20, rgb=(.08, .08, .09), opacity=.8)
c.add_text('RCS', x0 + 16, y0 + z_px(-.12), 20, rgb=(.6, .08, .05), opacity=.85)

# ------------------------------------------------------------ avionics trim: fins, louvers, plates
x0, y0, w, h = L.BOXES
sy, sx = slice(y0, y0 + h), slice(x0, x0 + w)
xx, yy = X[sy, sx] - x0, Y[sy, sx] - y0
A = np.ones((h, w, 3), np.float32) * np.array((.74, .74, .73), np.float32) * (.94 + .1 * grime(h, w, 431, base=6))[..., None]
H = np.zeros((h, w), np.float32)
for cx_, cy_, hw, hh in ((128, 128, 112, 112), (384, 128, 112, 112), (640, 128, 112, 112), (896, 128, 112, 112), (256, 380, 240, 112), (768, 380, 240, 112)):
    d = sd_rrect(xx, yy, cx_, cy_, hw, hh, 8)
    H += bevel(d, 4) * 2.2
    A *= (1 - np.exp(-np.abs(d) / 2)[..., None] * .4)
    for sxx in (-1, 1):
        for syy in (-1, 1):
            dd = sd_circle(xx, yy, cx_ + sxx * (hw - 11), cy_ + syy * (hh - 11), 3.5)
            H += fill(dd, 1) * 1.6
fin = (xx > 280) & (xx < 480) & (yy > 40) & (yy < 215) & ((xx % 14) < 5)
A = np.where(fin[..., None], A * .45, A)
H += fin * 1.8
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = .32
c.add_text('AVIONICS 2', x0 + 40, y0 + 90, 26, rgb=(.08, .08, .09), opacity=.8)
c.add_text('PDU', x0 + 830, y0 + 80, 40, rgb=(.08, .08, .09), opacity=.8)
c.add_text('ENGINE CTRL', x0 + 120, y0 + 370, 34, rgb=(.08, .08, .09), opacity=.8)
c.add_text('HIAD INFL. VLV', x0 + 620, y0 + 370, 34, rgb=(.08, .08, .09), opacity=.8)

# ------------------------------------------------------------ mount ring wall and plates
x0, y0, w, h = L.PLATE
sy, sx = slice(y0, y0 + h), slice(x0, x0 + w)
xx, yy = X[sy, sx] - x0, Y[sy, sx] - y0
A = np.ones((h, w, 3), np.float32) * np.array((.60, .61, .63), np.float32) * (.92 + .14 * grime(h, w, 441, base=7))[..., None]
H = np.zeros((h, w), np.float32)
b = (((xx % 26) - 13) ** 2 + ((yy % 26) - 13) ** 2) < 3.2 ** 2
H += b * 1.6
A *= (1 - (((xx % 26) - 13) ** 2 + ((yy % 26) - 13) ** 2 < 5.5 ** 2)[..., None] * .18)
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = .5

# AO bake if present
p = os.path.join(OUT, 'ao_shab_lander.png')
if os.path.exists(p):
    ao = blur(np.asarray(Image.open(p).convert('L')).astype(np.float32) / 255, .8)
    # Only the polar deck sheets are unique. The wall sector repeats six times with different greebles on
    # each, and the boxes and mount share trim, so the bake's shadows there have no caster: leave them out.
    for zx, zy, zw, zh in (L.SIDE, L.BOXES, L.PLATE):
        ao[zy:zy + zh, zx:zx + zw] = 1
    c.ao = np.clip(ao, .12, 1) ** .9
    print('applied AO bake', p, round(float(ao.mean()), 3))
c.save('shab_lander', nstrength=1.0, cavity=.28, target_p90=.79)
