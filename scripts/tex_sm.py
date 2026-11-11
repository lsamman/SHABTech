"""Service module sheet: gold MLI blanket strip, aft bulkhead, top deck ring, radiator panel,
dish faces. Unique-mapped areas take a Cycles AO bake from bake_ao.py when present."""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from tl import *
import sm_layout as L

N = L.ATLAS


def foil_height(h, w, seed, cells=70):
    """Crumpled MLI: sharp facets over soft quilting. Returns (height, shade 0..1)."""
    sh, ht, ed = facet_foil(h, w, seed, cells=cells)
    cr = crinkle(h, w, seed + 3, scale=11, sharp=2.0)
    big = fbm(h, w, seed + 5, base=4, octaves=3)
    H = blur(ht, 1.6) * .16 + blur(cr, .8) * 1.1 + big * 2.6 - blur(ed, .8) * .22
    # fake raking light so the diffuse alone reads as crumpled foil at a distance
    dx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) * .5
    dy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) * .5
    lit = dx * .7 + dy * .7
    lit = lit / (lit.std() * 2.2 + 1e-6)
    crease = np.clip((blur(cr, .5) - .60) * 7, 0, 1)
    H = H + crease * .35
    shade = np.clip(.5 + lit * .42 + (sh - .5) * .16 + big * .10 - crease * .20, 0, 1)
    return H, shade.astype(np.float32)


def metal_ramp(t, dark, mid, light):
    t = t[..., None]
    a = np.array(dark, np.float32); b = np.array(mid, np.float32); c = np.array(light, np.float32)
    return np.where(t < .5, a + (b - a) * (t / .5), b + (c - b) * ((t - .5) / .5))


c = Canvas(N, N, albedo=(.14, .14, .15), gloss=.25)
X, Y = c.x, c.y
PPM = L.PPM

# ------------------------------------------------------------ blanket strip
y0, y1 = L.Y_TOP, int(L.Y_TOP + (L.Z_TOP - L.Z_BOT) * PPM)
h_s, w_s = y1 - y0, N
H, sh = foil_height(h_s, w_s, 401, cells=60)
sy, sx = slice(y0, y1), slice(0, N)
col = metal_ramp(sh, (.36, .22, .06), (.68, .46, .16), (.95, .78, .38))
XS, YS = X[sy, sx], Y[sy, sx]
c.albedo[sy, sx] = col
c.gloss[sy, sx] = .50 + .28 * sh
c.height[sy, sx] = H * .9
az_px = N / L.NF
ys_z = L.Z_TOP - (YS - y0) / PPM                # z for every strip pixel
in_blanket = (np.abs(ys_z) > L.MID) & (np.abs(ys_z) < L.Z_TOP - L.BAND)
# tie-tacks and their puckers
tx, ty = 62.0, 50.0
fx = (XS % tx) - tx / 2; fy = ((YS - y0) % ty) - ty / 2
d = np.hypot(fx, fy)
c.height[sy, sx] -= np.exp(-(d / 7) ** 2) * 1.1 * in_blanket
button = fill(d - 3.2, 1) * in_blanket
c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - button[..., None]) + np.array((.07, .06, .05), np.float32) * button[..., None]
c.albedo[sy, sx] *= (1 - np.exp(-(d / 5) ** 2)[..., None] * .18 * in_blanket[..., None])
# blanket stitching along facet seams and frames
facet_u = (XS % az_px)
edge_d = np.minimum(facet_u, az_px - facet_u)
st = ((YS % 9) < 4.5) & (np.abs(edge_d - 16) < 1.3) & in_blanket
c.albedo[sy, sx] = np.where(st[..., None], c.albedo[sy, sx] * .45, c.albedo[sy, sx])
c.height[sy, sx] -= st * .8
for zedge in (L.Z_TOP - L.BAND - .025, L.Z_BOT + L.BAND + .025, L.MID + .025, -L.MID - .025):
    yy = y0 + (L.Z_TOP - zedge) * PPM
    st = ((XS % 9) < 4.5) & (np.abs(YS - yy) < 1.2)
    c.albedo[sy, sx] = np.where(st[..., None], c.albedo[sy, sx] * .45, c.albedo[sy, sx])
    c.height[sy, sx] -= st * .8
# facet seams darken toward the corner posts
c.albedo[sy, sx] *= (1 - np.exp(-edge_d / 7)[..., None] * .55)
# metal tape patches, a few per facet
r = rng(402)
for k in range(L.NF):
    for _ in range(int(r.integers(1, 4))):
        cx = (k + r.uniform(.2, .8)) * az_px
        zc = r.choice([-1, 1]) * r.uniform(.08, .28)
        cy = y0 + (L.Z_TOP - zc) * PPM
        hw, hh = r.uniform(10, 34), r.uniform(5, 14)
        m = fill(sd_rrect(XS, YS, cx, cy, hw, hh, 1.5), .9)
        tone = (.80, .80, .78) if r.random() < .5 else (.72, .50, .18)
        c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None] * .92) + np.array(tone, np.float32) * m[..., None] * .92
        c.height[sy, sx] = c.height[sy, sx] * (1 - m * .75) + m * .8
# ring frames and mid belt: painted metal, bolts, darker where the blanket tucks in
for zlo, zhi in ((L.Z_TOP - L.BAND, L.Z_TOP), (L.Z_BOT, L.Z_BOT + L.BAND), (-L.MID, L.MID)):
    ya, yb = y0 + (L.Z_TOP - zhi) * PPM, y0 + (L.Z_TOP - zlo) * PPM
    band = (YS >= ya) & (YS <= yb)
    n = grime(h_s, w_s, 403, base=30)
    metal = np.array((.60, .60, .62), np.float32) * (.9 + .2 * n)[..., None]
    c.albedo[sy, sx] = np.where(band[..., None], metal, c.albedo[sy, sx])
    c.gloss[sy, sx] = np.where(band, .42, c.gloss[sy, sx])
    c.height[sy, sx] = np.where(band, 0, c.height[sy, sx])
    bolts_y = (ya + yb) / 2
    b = (((XS % 26) - 13) ** 2 + (YS - bolts_y) ** 2) < 3.2 ** 2
    c.height[sy, sx] += b * 1.8
    c.albedo[sy, sx] = np.where((((XS % 26) - 13) ** 2 + (YS - bolts_y) ** 2 < 5 ** 2)[..., None] & band[..., None], c.albedo[sy, sx] * .78, c.albedo[sy, sx])
    # edge shadow
    edge = np.minimum(np.abs(YS - ya), np.abs(YS - yb))
    c.albedo[sy, sx] *= (1 - np.exp(-edge / 3.0)[..., None] * .5)
# stencils on the frames and tape
for az_, z_, txt in ((0, .0, 'SM-02 AFT MODULE'), (150, .0, 'FWD ▲'), (-120, .0, 'NO GRIP'), (60, Z := L.Z_BOT + .045, 'DECOUPLER PLANE ABOVE'),
                     (-60, L.Z_BOT + .045, 'RCS QUAD 3'), (120, L.Z_TOP - .045, 'BIPROP TANKS BELOW')):
    x_, y_ = L.strip_px(az_, z_)
    c.add_text(txt.replace('▲', '^'), x_ - 70, y_ - 6, 13, rgb=(.05, .05, .06), opacity=.82)
for az_, z_, txt in ((30, .19, 'NTO FILL'), (-30, .19, 'MMH FILL'), (180, -.2, 'GSE PURGE')):
    x_, y_ = L.strip_px(az_, z_)
    m = fill(sd_rrect(X, Y, x_, y_ + 7, 54, 11, 2))
    c.tint(m, (.80, .80, .78), .95)
    c.add_text(txt, x_ - 48, y_, 13, rgb=(.04, .04, .05), opacity=.9)


# ------------------------------------------------------------ black polar blankets
def polar_blanket(cx, cy, rp, rmax, seed, seams=12, rings=(), tone=.11):
    x0, y0_, x1, y1_ = int(cx - rp - 6), int(cy - rp - 6), int(cx + rp + 6), int(cy + rp + 6)
    sy_, sx_ = slice(y0_, y1_), slice(x0, x1)
    h_, w_ = y1_ - y0_, x1 - x0
    H_, sh_ = foil_height(h_, w_, seed, cells=max(26, w_ // 34))
    xx, yy = X[sy_, sx_] - cx, Y[sy_, sx_] - cy
    rr = np.hypot(xx, yy) / rp * rmax
    az = np.degrees(np.arctan2(xx, yy))
    colr = metal_ramp(sh_, (tone * .55,) * 3, (tone,) * 3, (tone * 2.6,) * 3)
    c.albedo[sy_, sx_] = colr
    c.gloss[sy_, sx_] = .30 + .25 * sh_
    c.height[sy_, sx_] = H_ * .55
    # seams
    daz = np.abs(((az + 180 / seams) % (360 / seams)) - 180 / seams) * math.pi / 180 * rr / rmax * rp
    seam = fill(daz - 1.4, 1)
    c.albedo[sy_, sx_] *= (1 - seam[..., None] * .55)
    c.height[sy_, sx_] -= seam * 1.2
    for ring in rings:
        d_ = np.abs(rr - ring) / rmax * rp
        b_ = fill(d_ - 1.4, 1)
        c.albedo[sy_, sx_] *= (1 - b_[..., None] * .55)
        c.height[sy_, sx_] -= b_ * 1.2
    return rr, az, sy_, sx_


rr, az, sy2, sx2 = polar_blanket(*L.AFT, 411, rings=(.28, .52, .74))
# silver thrust ring and bolts near the engine mount; scorch around the bell
m = fill(np.abs(rr - .235) / L.AFT[3] * L.AFT[2] - 16, 1)
c.albedo[sy2, sx2] = c.albedo[sy2, sx2] * (1 - m[..., None]) + np.array((.52, .52, .54), np.float32) * m[..., None]
c.gloss[sy2, sx2] = c.gloss[sy2, sx2] * (1 - m) + .55 * m
ang = (az % 15) - 7.5
b = ((np.abs(rr - .235) / L.AFT[3] * L.AFT[2]) ** 2 + (ang * math.pi / 180 * rr / L.AFT[3] * L.AFT[2]) ** 2) < 5 ** 2
c.height[sy2, sx2] += b * 2.0
c.albedo[sy2, sx2] *= (.82 + .28 * grime(sy2.stop - sy2.start, sx2.stop - sx2.start, 412, base=6))[..., None]
soot = np.exp(-(rr / .34) ** 2)

rr, az, sy2, sx2 = polar_blanket(*L.TOPRING, 421, seams=12, rings=(.86,), tone=.075)
ring = (rr < .835)
c.albedo[sy2, sx2] = np.where(ring[..., None], np.array((.58, .58, .60), np.float32), c.albedo[sy2, sx2])
c.gloss[sy2, sx2] = np.where(ring, .5, c.gloss[sy2, sx2])
c.height[sy2, sx2] = np.where(ring, 0, c.height[sy2, sx2])
ang = (az % 15) - 7.5
b = ((np.abs(rr - .815) / L.TOPRING[3] * L.TOPRING[2]) ** 2 + (ang * math.pi / 180 * rr / L.TOPRING[3] * L.TOPRING[2]) ** 2) < 3.5 ** 2
c.height[sy2, sx2] += b * 2.0
# interface bulkhead: radial stiffeners, lightening rings, access plates, all out of sight once mated
pr = rr / L.TOPRING[3] * L.TOPRING[2]
for rg in (.74, .48, .22):
    d_ = np.abs(rr - rg) / L.TOPRING[3] * L.TOPRING[2]
    c.height[sy2, sx2] += fill(d_ - 3, 1) * 2 * ring
    c.albedo[sy2, sx2] *= (1 - (np.exp(-d_ / 1.6) * ring)[..., None] * .35)
spokes = np.abs(((az + 15) % 30) - 15) * math.pi / 180 * pr
c.height[sy2, sx2] += fill(spokes - 2.2, 1) * 1.6 * ring * (rr > .22) * (rr < .74)
c.albedo[sy2, sx2] *= (1 - (np.exp(-spokes / 1.4) * ring * (rr > .22) * (rr < .74))[..., None] * .3)
ang2 = (az % 10) - 5
b = ((np.abs(rr - .76) / L.TOPRING[3] * L.TOPRING[2]) ** 2 + (ang2 * math.pi / 180 * pr) ** 2) < 2.4 ** 2
c.height[sy2, sx2] += b * 1.4
c.albedo[sy2, sx2] *= (.93 + .12 * grime(sy2.stop - sy2.start, sx2.stop - sx2.start, 422, base=7))[..., None]
c.add_text('PCM INTERFACE', L.TOPRING[0] - 62, L.TOPRING[1] - 90, 16, rgb=(.08, .08, .09), opacity=.75)

# ------------------------------------------------------------ radiator panel
x, y, w, h = L.RAD
sy3, sx3 = slice(y, y + h), slice(x, x + w)
xx, yy = X[sy3, sx3] - x, Y[sy3, sx3] - y
n = grime(h, w, 431, base=6)
c.albedo[sy3, sx3] = np.array((.86, .86, .84), np.float32) * (.96 + .08 * n)[..., None]
c.gloss[sy3, sx3] = .46
c.height[sy3, sx3] = 0
# fluid tubes along the span (t), header bars across both ends
tube = (np.sin((xx - 10) * 2 * np.pi / 42) * .5 + .5) ** 4
c.height[sy3, sx3] += tube * 2.6 * ((yy > 44) & (yy < h - 44))
c.albedo[sy3, sx3] *= (.97 + .06 * tube)[..., None]
for ye in (30, h - 30):
    d_ = np.abs(yy - ye) - 12
    c.height[sy3, sx3] += fill(d_, 1.2) * 3
    c.albedo[sy3, sx3] *= (1 - np.exp(-np.abs(d_) / 1.8)[..., None] * .35)
sd = sd_rrect(xx, yy, w / 2, h / 2, w / 2 - 6, h / 2 - 6, 6)
c.albedo[sy3, sx3] *= (1 - np.exp(-np.abs(sd) / 2.0)[..., None] * .45)
c.height[sy3, sx3] += bevel(sd, 3) * 1.4
for i in range(9):
    for yb in (6, h - 6):
        d_ = sd_circle(xx, yy, 14 + i * (w - 28) / 8, yb + (10 if yb < h / 2 else -10), 3)
        c.height[sy3, sx3] += fill(d_, 1) * 2
c.albedo[sy3, sx3] += scratches(h, w, 432, n=120)[..., None] * .03
c.add_text('LOOP B', x + 16, y + 56, 15, rgb=(.15, .15, .16), opacity=.7)
c.add_text('NH3', x + w - 54, y + h - 72, 15, rgb=(.15, .15, .16), opacity=.7)

# ------------------------------------------------------------ dish faces
cx, cy, rp, rm = L.DISH_IN
sy4, sx4 = slice(int(cy - rp - 4), int(cy + rp + 4)), slice(int(cx - rp - 4), int(cx + rp + 4))
xx, yy = X[sy4, sx4] - cx, Y[sy4, sx4] - cy
rr = np.hypot(xx, yy) / rp
az = np.degrees(np.arctan2(xx, yy))
hh_, ww_ = xx.shape
c.albedo[sy4, sx4] = np.array((.84, .84, .82), np.float32) * (.96 + .08 * grime(hh_, ww_, 441, base=5))[..., None]
c.gloss[sy4, sx4] = .52
c.height[sy4, sx4] = 0
daz = np.abs(((az + 15) % 30) - 15) * math.pi / 180 * rr * rp
c.albedo[sy4, sx4] *= (1 - np.exp(-daz / 1.4)[..., None] * .35)
c.height[sy4, sx4] += fill(daz - 1.2, 1) * 1.1
for rg in (.32, .62, .96):
    d_ = np.abs(rr - rg) * rp
    c.albedo[sy4, sx4] *= (1 - np.exp(-d_ / 1.4)[..., None] * .35)
    c.height[sy4, sx4] += fill(d_ - 1.4, 1) * 1.1
# fine perforation at the rim
pf = ((xx % 7) < 2) & ((yy % 7) < 2) & (rr > .64)
c.albedo[sy4, sx4] *= (1 - pf[..., None] * .05)
cx, cy, rp, rm = L.DISH_OUT
sy5, sx5 = slice(int(cy - rp - 4), int(cy + rp + 4)), slice(int(cx - rp - 4), int(cx + rp + 4))
xx, yy = X[sy5, sx5] - cx, Y[sy5, sx5] - cy
rr = np.hypot(xx, yy) / rp
az = np.degrees(np.arctan2(xx, yy))
hh_, ww_ = xx.shape
H5, sh5 = foil_height(hh_, ww_, 451, cells=26)
c.albedo[sy5, sx5] = metal_ramp(sh5, (.38, .38, .39), (.62, .62, .63), (.86, .86, .87))
c.gloss[sy5, sx5] = .35 + .3 * sh5
c.height[sy5, sx5] = H5 * .6
daz = np.abs(((az + 15) % 30) - 15) * math.pi / 180 * rr * rp
c.albedo[sy5, sx5] *= (1 - np.exp(-daz / 1.8)[..., None] * .45)

# ------------------------------------------------------------ AO, save
p = os.path.join(OUT, 'ao_shab_sm.png')
if os.path.exists(p):
    ao = np.asarray(Image.open(p).convert('L')).astype(np.float32) / 255
    c.ao = np.clip(blur(ao, .8), .15, 1) ** .9
    print('applied AO bake', p, round(float(c.ao.mean()), 3))
c.save('shab_sm', nstrength=.9, cavity=.15)
