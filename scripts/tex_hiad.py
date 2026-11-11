"""HIAD sheet (shab_hiad): windward TPS gore, braided torus bladder, stowage band, ablator plug."""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from tl import *
import ll as L

N = 2048
c = Canvas(N, N, albedo=(.5, .4, .3), gloss=.15)
X, Y = c.x, c.y


def zone(z):
    x0, y0, w, h = z
    sy, sx = slice(y0, y0 + h), slice(x0, x0 + w)
    return sy, sx, X[sy, sx] - x0, Y[sy, sx] - y0, w, h


# ------------------------------------------------------------ windward TPS gore (orange SiC fabric)
sy, sx, xx, yy, w, h = zone(L.SKIN)
# The gore's width grows 2.6x from hub to rim, so large noise stretches into wood grain: keep tone
# changes radial or very faint, and let the fine weave and the stitching carry the surface.
n1 = fbm(h, w, 501, base=220, octaves=3)
A = np.array((.60, .42, .25), np.float32) * np.ones_like(n1[..., None])
wv = weave(xx, yy, 2.6)
H = wv * .28
A *= (.975 + .05 * wv)[..., None]
G = np.full((h, w), .20, np.float32)
# gore seams: a raised felled seam with two rows of stitching
for s in (0, w):
    d = np.abs(xx - s)
    H += fill(d - 7, 1.5) * .9
    A *= (1 - np.exp(-d / 2.0)[..., None] * .40)
    st = (((yy % 11) < 6) & (np.abs(d - 5) < 1.0))
    A = np.where(st[..., None], A * .72, A)
    H -= st * .4
# fabric width joins around the cone, thin and stitched, with a soft swell where each torus sits behind
for i in range(9):
    yc = h * (i + .5) / 9
    H += np.exp(-((yy - yc) / 40) ** 2) * .9
for i in range(1, 5):
    yc = h * i / 5
    d = np.abs(yy - yc)
    A *= (1 - np.exp(-d / 1.6)[..., None] * .30)
    H += fill(d - 3, 1) * .5
    st = (((xx % 11) < 6) & (np.abs(d - 5) < 1.0))
    A = np.where(st[..., None], A * .78, A)
# strap tie-down patches behind the fabric, two per gore
for cx_ in (w * .25, w * .75):
    for i in range(1, 5):
        cy_ = h * i / 5 - 44
        d = sd_rrect(xx, yy, cx_, cy_, 26, 18, 3)
        m = fill(d, 1.5)
        A = A * (1 - m[..., None] * .22) + A * .86 * m[..., None] * .22
        H += bevel(d, 2) * .7
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = G
c.add_text('HD-16  GORE', L.SKIN[0] + 70, L.SKIN[1] + 960, 22, rgb=(.08, .05, .03), opacity=.5)

# ------------------------------------------------------------ torus bladder braid (fig. 7's yellow)
sy, sx, xx, yy, w, h = zone(L.BRAID)
n1 = grime(h, w, 511, base=8)
A = np.array((.70, .63, .30), np.float32) * (.88 + .22 * n1[..., None])
# diagonal braid both ways
d1 = np.sin((xx + yy) * 2 * np.pi / 20); d2 = np.sin((xx - yy) * 2 * np.pi / 20)
chk = ((np.floor((xx + yy) / 20) + np.floor((xx - yy) / 20)) % 2)
br = np.where(chk > 0, d1, d2) * .5 + .5
H = br * .9
A *= (.82 + .3 * br)[..., None]
G = (.16 + .14 * br).astype(np.float32)
# axial seam around the minor circle at the mid-height, plus cords
for t in (.5,):
    d = np.abs(yy - h * t)
    A *= (1 - np.exp(-d / 3)[..., None] * .35)
    H += fill(d - 3, 1) * .8
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = G

# ------------------------------------------------------------ stowage band (fig. 4's dark sandy ring)
sy, sx, xx, yy, w, h = zone(L.RIMZ)
n1 = fbm(h, w, 521, base=120, octaves=4)
A = np.array((.27, .265, .26), np.float32) * (.86 + .16 * n1[..., None]) * (.92 + .16 * grime(h, w, 522, base=6))[..., None]
H = n1 * .7 + fbm(h, w, 523, base=300, octaves=2) * .3
G = np.full((h, w), .16, np.float32)
# stitched gores and lacing every 1/16 of the circumference
for i in range(16):
    xc = (i + .5) * w / 16
    d = np.abs(xx - xc)
    A *= (1 - np.exp(-d / 3.5)[..., None] * .35)
    H -= np.exp(-d / 2) * 1
    lace = (np.abs(((yy + (xx - xc) * .8) % 26) - 13) < 2.2) & (d < 11)
    A = np.where(lace[..., None], np.array((.56, .53, .44), np.float32), A)
    H += lace * 1.4
for t in (.10, .90):
    d = np.abs(yy - h * t)
    m = fill(d - 7)
    A = A * (1 - m[..., None]) + np.array((.42, .42, .43), np.float32) * m[..., None]
    H += m * 1.2
    b = (((xx % 18) - 9) ** 2 + (yy - h * t) ** 2) < 2.4 ** 2
    H += b * 1
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = G
c.add_text('HIAD  -  DO NOT PUNCTURE', L.RIMZ[0] + 40, L.RIMZ[1] + 110, 24, rgb=(.70, .68, .60), opacity=.8)
c.add_text('INFL. 1.5 BAR N2', L.RIMZ[0] + 560, L.RIMZ[1] + 110, 24, rgb=(.70, .68, .60), opacity=.8)

# ------------------------------------------------------------ ablator plug (polar)
sy, sx, xx, yy, w, h = zone(L.NOSE)
dx, dy = xx - w / 2, yy - h / 2
rr = np.hypot(dx, dy) / (w / 2)
az = np.degrees(np.arctan2(dx, dy))
n1 = grime(h, w, 531, base=5)
A = np.array((.27, .23, .19), np.float32) * (.76 + .44 * n1[..., None])
s = 12.0
col = np.round(xx / (s * 1.732)); row = np.round((yy - (col % 2) * s) / (s * 2))
hx = xx - col * s * 1.732; hy = yy - row * s * 2 - (col % 2) * s
dd = np.maximum(np.abs(hx) * .866 + np.abs(hy) * .5, np.abs(hy)) - s * .90
H = fill(dd, 1.4) * 1.0 + fbm(h, w, 532, base=40, octaves=3) * .5
A *= (.72 + .36 * fill(dd, 1.5))[..., None]
G = np.full((h, w), .09, np.float32)
# gore seams, rim latches, soot rising from the rim
for i in range(12):
    azc = i * 30
    ang = ((az - azc + 180) % 360 - 180)
    d = np.abs(np.radians(ang)) * rr * w / 2
    A *= (1 - (np.exp(-d / 2.5) * (rr > .25))[..., None] * .45)
    H -= np.exp(-d / 2) * (rr > .25) * 1
d = np.abs(rr - .25) * w / 2
A *= (1 - np.exp(-d / 3)[..., None] * .4)
H += fill(d - 4, 1) * 1.5
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = G

# ------------------------------------------------------------ grey back cover and hub wall
sy, sx, xx, yy, w, h = zone(L.BACK)
A = np.array((.62, .62, .62), np.float32) * (.88 + .22 * grime(h, w, 541, base=6))[..., None]
wv = weave(xx, yy, 3.0)
H = wv * .3 + crinkle(h, w, 542, scale=18) * 1.2
A *= (.92 + .12 * wv)[..., None]
for i in range(16):
    xc = (i + .5) * w / 16
    d = np.abs(xx - xc)
    A *= (1 - np.exp(-d / 3)[..., None] * .3)
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = .14

sy, sx, xx, yy, w, h = zone(L.HUBZ)
A = np.array((.68, .68, .70), np.float32) * (.9 + .16 * grime(h, w, 551, base=8))[..., None]
H = np.zeros((h, w), np.float32)
b = (((xx % 30) - 15) ** 2 + ((yy % 30) - 15) ** 2) < 3 ** 2
H += b * 1.5
A *= (1 - (((xx % 30) - 15) ** 2 + ((yy % 30) - 15) ** 2 < 5 ** 2)[..., None] * .2)
s = 15.0
col = np.round(xx / (s * 1.732)); row = np.round((yy - (col % 2) * s) / (s * 2))
hx = xx - col * s * 1.732; hy = yy - row * s * 2 - (col % 2) * s
dd = np.maximum(np.abs(hx) * .866 + np.abs(hy) * .5, np.abs(hy)) - s * .82
H += fill(dd, 1.2) * .9
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = .42

p = os.path.join(OUT, 'ao_shab_hiad.png')
if os.path.exists(p):
    ao = blur(np.asarray(Image.open(p).convert('L')).astype(np.float32) / 255, .8)
    # The braid, band and hub zones tile around the part, so a bake has no single right answer there.
    for zx, zy, zw, zh in (L.BRAID, L.RIMZ, L.HUBZ):
        ao[zy:zy + zh, zx:zx + zw] = 1
    c.ao = np.clip(ao, .15, 1) ** .9
    print('applied AO bake', p, round(float(ao.mean()), 3))
c.save('shab_hiad', nstrength=1.0, cavity=.28)
