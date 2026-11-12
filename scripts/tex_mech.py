"""Mechanism sheet (shab_mech_diff/nrm): the radiator wing's pumped-loop panel, landing-leg trim (footpad tread,
strut sleeve, crush cartridge) and the HIAD stowage band with its Kevlar straps and torus seams.
Zones in mech_layout.py. Clean HabTech2 style: flat colour, relief only on real features."""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from tl import *
import mech_layout as ML

N = ML.ATLAS
TAU = math.tau
c = Canvas(N, N, albedo=(.55, .55, .56), gloss=.25)
X, Y = c.x, c.y
WHITE = np.array((.86, .86, .845), np.float32)


def zone(z):
    x0, y0, w, h = z
    sy, sx = slice(y0, y0 + h), slice(x0, x0 + w)
    return sy, sx, X[sy, sx] - x0, Y[sy, sx] - y0, w, h


def text_mask(txt, size, w, h, x, y, rotate=0, sx=1.0, sy=1.0):
    """Coverage mask (h, w) of a stencil, drawn upright then rotated and squeezed (sx, sy) so it reads at the
    right aspect on a zone mapped with unequal px/m. x, y: where the text block's centre lands."""
    font = ImageFont.truetype(FONT_BOLD, int(size))
    l, t, r, b = font.getbbox(txt)
    im = Image.new('L', (r - l + 8, b - t + 8), 0)
    ImageDraw.Draw(im).text((4 - l, 4 - t), txt, fill=255, font=font)
    if rotate:
        im = im.rotate(rotate, expand=True, resample=Image.BICUBIC)
    im = im.resize((max(1, int(im.width * sx)), max(1, int(im.height * sy))), Image.LANCZOS)
    out = np.zeros((h, w), np.float32)
    x0, y0 = int(x - im.width / 2), int(y - im.height / 2)
    a = np.asarray(im, np.float32) / 255
    xa, ya = max(0, x0), max(0, y0)
    xb, yb = min(w, x0 + im.width), min(h, y0 + im.height)
    out[ya:yb, xa:xb] = a[ya - y0:yb - y0, xa - x0:xb - x0]
    return out


def rivets(xx, yy, pts, r=3.0, hgt=1.0):
    hm = np.zeros_like(xx)
    for px, py in pts:
        hm = np.maximum(hm, np.clip(1 - ((xx - px) ** 2 + (yy - py) ** 2) / (r * r), 0, 1) ** .5)
    return hm * hgt


# ------------------------------------------------------------ radiator panel face (pumped single-phase NH3 loop)
sy, sx, xx, yy, w, h = zone(ML.WING)
ppm = w / ML.WING_W
E = ML.WING_EDGE * ppm; HD = ML.WING_HDR * ppm
A = np.ones((h, w, 3), np.float32) * WHITE
H = np.zeros((h, w), np.float32)
G = np.full((h, w), .22, np.float32)
inner = (xx > E) & (xx < w - E) & (yy > HD) & (yy < h - HD)
# flow tubes along the span: half-round tube on a bonded saddle, flat fin between
pitch = (w - 2 * E) / ML.WING_TUBES
d = np.abs(((xx - E) % pitch) - pitch / 2)
span_ok = smooth(HD - 4, HD + 18, yy) * smooth(HD - 4, HD + 18, h - yy) * ((xx > E + 2) & (xx < w - E - 2))
tube_h = np.sqrt(np.clip(1 - (d / 7.0) ** 2, 0, 1))
saddle = np.clip(1 - np.abs(d) / 13.0, 0, 1)
H += (tube_h * 1.9 + saddle * .35) * span_ok
A *= (1 - (np.exp(-((d - 8.5) / 1.4) ** 2) * .07 * span_ok))[..., None]      # shadowed tube flank
A *= (1 + tube_h * .025 * span_ok)[..., None]
A *= (1 - (np.abs(d - 13) < .8) * .035 * span_ok)[..., None]              # saddle bond line
G += tube_h * .05 * span_ok
# header doublers at root and tip: the manifold tubes sit on them
for y_in in (HD, h - HD):
    band = (yy < HD) if y_in == HD else (yy > h - HD)
    H += band * .6
    dd = np.abs(yy - y_in)
    A *= (1 - np.exp(-dd / 1.2)[..., None] * .30)
    H -= np.exp(-dd / 1.0) * .5
# edge closeouts beside the rails
for x_in in (E, w - E):
    band = (xx < E) if x_in == E else (xx > w - E)
    H += band * .5
    dd = np.abs(xx - x_in)
    A *= (1 - np.exp(-dd / 1.2)[..., None] * .30)
    H -= np.exp(-dd / 1.0) * .5
pts = [(x_, y_) for x_ in (E - 20, w - E + 20) for y_ in np.arange(HD + 30, h - HD - 20, 46)]
pts += [(x_, y_) for y_ in (HD - 14, h - HD + 14) for x_ in np.arange(E + 26, w - E - 20, 52)]
# hinge-lug doublers at both ends (lugs at 0.07 m and 0.33 m across the width)
for s_ in (.175, .825):
    for y_c in (HD * .55, h - HD * .55):
        sd = sd_rrect(xx, yy, s_ * w, y_c, 46, HD * .55, 6)
        H += bevel(sd, 3) * .5
        A *= (1 - np.exp(-np.abs(sd) / 1.3)[..., None] * .25)
        pts += [(s_ * w + ox, y_c + oy) for ox in (-32, 32) for oy in (-HD * .3, HD * .3)]
# tie-down inserts: round doublers the launch snubbers bear on; tubes are routed round them
for s_ in (.125, .875):
    cx_, cy_ = s_ * w, h * (1 - .78)
    rr = np.hypot(xx - cx_, yy - cy_)
    H = np.where(rr < 62, H * smooth(56, 62, rr), H)
    A = np.where((rr < 60)[..., None], WHITE * np.ones_like(A), A)
    sd = rr - 56
    H += bevel(sd, 3) * .55
    A *= (1 - np.exp(-np.abs(sd) / 1.3)[..., None] * .28)
    pts += [(cx_ + 44 * math.cos(a), cy_ + 44 * math.sin(a)) for a in np.linspace(0, TAU, 7)[:-1]]
H += rivets(xx, yy, pts, 3.2, 1.0)
rv = rivets(xx, yy, pts, 3.2, 1.0)
A *= (1 - (rv > 0) * .06)[..., None]; G += (rv > 0) * .1
# stencils: loop id near the root, no-step near the tip, small panel id box
for txt, ty, sz in (('TR-3  NH3  LOOP B', h - HD - 54, 26), ('NO STEP', HD + 52, 26)):
    m = text_mask(txt, sz, w, h, w / 2, ty)
    A = A * (1 - m[..., None] * .85) + np.array((.10, .10, .11), np.float32) * m[..., None] * .85
sd = sd_rrect(xx, yy, w * .80, h - HD - 54, 70, 22, 3)
m = np.clip(1 - np.abs(sd) / 1.6, 0, 1)
A = A * (1 - m[..., None] * .8) + np.array((.10, .10, .11), np.float32) * m[..., None] * .8
m = text_mask('PNL', 22, w, h, w * .80, h - HD - 54)
A = A * (1 - m[..., None] * .85) + np.array((.10, .10, .11), np.float32) * m[..., None] * .85
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = G

# ------------------------------------------------------------ HIAD stowage band: folded tori behind a Nomex cover
sy, sx, xx, yy, w, h = zone(ML.BAND)
t = 1 - yy / h
BASE = np.array((.30, .295, .29), np.float32)
A = np.ones((h, w, 3), np.float32) * BASE
H = np.zeros((h, w), np.float32)
G = np.full((h, w), .16, np.float32)
# the folded tori push the cover out in four soft rows; stitched seams run between them
rows = [.065, .29, .50, .71, .935]
for a_, b_ in zip(rows[:-1], rows[1:]):
    u = np.clip((t - a_) / (b_ - a_), 0, 1)
    inside = (t > a_) & (t < b_)
    H += np.sin(u * np.pi) * 6.0 * inside
    A *= (1 + (np.sin(u * np.pi) - .6) * .05 * inside)[..., None]
for tc in rows[1:-1]:
    dpx = np.abs(t - tc) * h
    A *= (1 - np.exp(-dpx / 1.6)[..., None] * .45)
    H -= np.exp(-dpx / 1.5) * 1.2
    for off in (-5, 5):
        st = (np.abs(dpx - abs(off)) < .9) & ((xx % 10) < 6) & (np.sign(t - tc) == np.sign(off))
        A = np.where(st[..., None], np.array((.52, .50, .44), np.float32), A)
        H += st * .4
# binding tape top and bottom, with grommets
for lo, hi in ((0, rows[0]), (rows[-1], 1)):
    m = (t >= lo) & (t <= hi)
    A = np.where(m[..., None], np.array((.46, .46, .47), np.float32), A)
    H = np.where(m, 1.0, H)
    for e_ in (lo, hi):
        if 0 < e_ < 1:
            dpx = np.abs(t - e_) * h
            A *= (1 - np.exp(-dpx / 1.2)[..., None] * .35)
    yc = (lo + hi) / 2
    gm = ((((xx + 21) % 42) - 21) ** 2 + ((t - yc) * h) ** 2)
    A = np.where((gm < 25)[..., None], np.array((.62, .62, .64), np.float32), A)
    A = np.where((gm < 7)[..., None], np.array((.08, .08, .08), np.float32), A)
    H += np.clip(1 - np.abs(np.sqrt(gm) - 4) / 2, 0, 1) * .8
# gore seam at each tile edge
for xc in (0, w):
    dpx = np.abs(xx - xc)
    A *= (1 - np.exp(-dpx / 1.8)[..., None] * .4)
    H -= np.exp(-dpx / 1.6) * 1.0
    st = (np.abs(dpx - 6) < .9) & ((yy % 10) < 6) & (t > rows[0]) & (t < rows[-1])
    A = np.where(st[..., None], np.array((.52, .50, .44), np.float32), A)
# Kevlar retention straps over the whole height, edges proud of the cover
KEV = np.array((.80, .64, .22), np.float32)
SW = 26
for k in range(ML.BAND_STRAPS):
    xc = w * (k + .5) / ML.BAND_STRAPS
    dx_ = np.abs(xx - xc)
    m = fill(dx_ - SW, .8)
    A *= (1 - np.exp(-np.maximum(dx_ - SW, 0) / 2.5) * (dx_ > SW) * .40)[..., None]   # contact shadow
    tw = (np.sin((xx - xc + yy) * TAU / 7) * .5 + .5)
    kev = KEV * (.93 + .09 * tw)[..., None]
    for e_ in (-SW + 3, SW - 3):
        kev *= (1 - np.exp(-np.abs(xx - xc - e_) / 1.0) * .25)[..., None]
    A = A * (1 - m[..., None]) + kev * m[..., None]
    H = H * (1 - m) + (np.where(H > 0, H, 0) + 2.2 + tw * .3 + bevel(dx_ - SW, 2.5) * .8) * m
    G = G * (1 - m) + (.20 + .06 * tw) * m
    # box-X stitching where the strap is sewn to the bindings
    for yc_t in (.12, .88):
        cy_ = (1 - yc_t) * h
        bx = (np.abs(xx - xc) < SW - 7) & (np.abs(yy - cy_) < 20)
        edge = bx & ((np.abs(np.abs(xx - xc) - (SW - 8)) < .9) | (np.abs(np.abs(yy - cy_) - 19) < .9) |
                     (np.abs(np.abs(xx - xc) / (SW - 8) - np.abs(yy - cy_) / 19) < .06))
        A = np.where(edge[..., None], A * .55, A)
for txt, xc, tc in (('HIAD  -  DO NOT PUNCTURE', w * .5, .18), ('N2  1.5 BAR', w * .5, .82)):
    m = text_mask(txt, 19, w, h, xc, (1 - tc) * h, sx=.9)
    A = A * (1 - m[..., None] * .8) + np.array((.74, .71, .62), np.float32) * m[..., None] * .8
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = G

# ------------------------------------------------------------ back-cover cloth for the band's ledges
sy, sx, xx, yy, w, h = zone(ML.LEDGE)
A = np.ones((h, w, 3), np.float32) * np.array((.58, .58, .59), np.float32)
H = (np.sin(xx * TAU / 3.2) * np.sin(yy * TAU / 3.2)) * .12
for i in range(8):
    dpx = np.abs(xx - (i + .5) * (w - 64) / 8)
    A *= (1 - np.exp(-dpx / 1.6)[..., None] * .3)
    H -= np.exp(-dpx / 1.5) * .8
A[:, w - 64:] = np.array((.10, .10, .105), np.float32); H[:, w - 64:] = 0
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = .14

# ------------------------------------------------------------ footpad top: diamond tread annulus, bolt circle
sy, sx, xx, yy, w, h = zone(ML.PADTOP)
ppm = (w / 2 - 2) / ML.PAD_RMAX
rr = np.hypot(xx - w / 2, yy - h / 2) / ppm
A = np.ones((h, w, 3), np.float32) * WHITE
H = np.zeros((h, w), np.float32)
G = np.full((h, w), .26, np.float32)
tread = (rr > .072) & (rr < .168)
TR = np.array((.60, .61, .63), np.float32)
A = np.where(tread[..., None], TR, A)
G = np.where(tread, .42, G)
# lozenges in alternating directions, as on aluminium tread plate
p = 22.0
cx_ = np.floor(xx / p); cy_ = np.floor(yy / p)
fx = (xx % p) - p / 2; fy = (yy % p) - p / 2
alt = ((cx_ + cy_) % 2) * 2 - 1
u_ = (fx + alt * fy) / 1.414; v_ = (fx - alt * fy) / 1.414
loz = ((u_ / 8.5) ** 2 + (v_ / 2.4) ** 2) < 1
H += (loz & tread) * 1.3
A = np.where((loz & tread)[..., None], A * 1.12, A)
for r_e in (.072, .168):
    dpx = np.abs(rr - r_e) * ppm
    A *= (1 - np.exp(-dpx / 1.4)[..., None] * .35)
    H -= np.exp(-dpx / 1.2) * .7
az = np.arctan2(xx - w / 2, yy - h / 2)
for r_b, n_b in ((.058, 12), (.180, 16)):
    for k in range(n_b):
        a = TAU * (k + .5) / n_b
        bx_ = w / 2 + math.sin(a) * r_b * ppm; by_ = h / 2 + math.cos(a) * r_b * ppm
        dd = np.hypot(xx - bx_, yy - by_)
        H += np.clip(1 - dd / 5.0, 0, 1) ** .5 * 1.2
        A *= (1 - (np.abs(dd - 5) < 1) * .3)[..., None]
m = text_mask('NO STEP ON SENSOR', 15, w, h, w / 2, h / 2 + .19 * ppm * .995)
A = A * (1 - m[..., None] * .85) + np.array((.10, .10, .11), np.float32) * m[..., None] * .85
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = G

sy, sx, xx, yy, w, h = zone(ML.SOLE)
c.albedo[sy, sx] = np.array((.58, .58, .60), np.float32); c.gloss[sy, sx] = .3
rr = np.hypot(xx - w / 2, yy - h / 2)
c.height[sy, sx] = -np.exp(-np.abs(((rr % 24) - 12)) / 1.0) * .5

# ------------------------------------------------------------ strut sleeve: white, index stripe, stencils, pinch band
sy, sx, xx, yy, w, h = zone(ML.STRUT)
# s wraps .39 m in 256 px; t runs the 0.95 m sleeve in 1024 px (bottom = hinge end)
asp = (w / (TAU * .062)) / (h / .95)
A = np.ones((h, w, 3), np.float32) * WHITE
H = np.zeros((h, w), np.float32)
G = np.full((h, w), .28, np.float32)
A = np.where((np.abs(xx - w * .5) < 2.2)[..., None], np.array((.10, .10, .11), np.float32), A)
for tc in (.07, .35, .62, .985):
    dpx = np.abs(yy - (1 - tc) * h)
    A *= (1 - np.exp(-dpx / 1.3)[..., None] * .3)
    H -= np.exp(-dpx / 1.2) * .6
pinch = (yy < .045 * h) & (yy > .005 * h)
hz = ((xx / asp + yy) % 28) < 14
A = np.where((pinch & hz)[..., None], np.array((.82, .66, .10), np.float32), A)
A = np.where((pinch & ~hz)[..., None], np.array((.06, .06, .06), np.float32), A)
for txt, tc, xc in (('LL-6  PRIMARY STRUT', .50, w * .25), ('S/N 0042  -  NO HANDHOLD', .50, w * .75)):
    m = text_mask(txt, 22, w, h, xc, (1 - tc) * h, rotate=90, sx=asp)
    A = A * (1 - m[..., None] * .85) + np.array((.10, .10, .11), np.float32) * m[..., None] * .85
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = G

# ------------------------------------------------------------ crush cartridge: housing with honeycomb windows
sy, sx, xx, yy, w, h = zone(ML.CART)
# s wraps 2*pi*.066 m in 256 px; t runs .24 m in 512 px
asp = (w / (TAU * .066)) / (h / .24)
A = np.ones((h, w, 3), np.float32) * WHITE
H = np.zeros((h, w), np.float32)
G = np.full((h, w), .28, np.float32)
yy2 = yy * asp
s = 3.0
col = np.round(xx / (s * 1.732)); row = np.round((yy2 - (col % 2) * s) / (s * 2))
hx = xx - col * s * 1.732; hy = yy2 - row * s * 2 - (col % 2) * s
dd = np.maximum(np.abs(hx) * .866 + np.abs(hy) * .5, np.abs(hy)) - s * .78
for xc in (w * .25, w * .75):
    sd = sd_rrect(xx, yy2, xc, h * asp / 2, 34, h * asp * .30, 5)
    win = fill(sd, .8)
    hc = np.where((dd < 0)[..., None], np.array((.74, .75, .77), np.float32), np.array((.46, .46, .48), np.float32))
    A = A * (1 - win[..., None]) + hc * win[..., None]
    H += -bevel(sd, 2.5) * 2.0 + win * fill(dd, .6) * .5
    G = G * (1 - win) + .5 * win
    A *= (1 - np.exp(-np.abs(sd) / 1.2)[..., None] * .35)
for tc in (.06, .94):
    band = np.abs(yy - (1 - tc) * h) < h * .05
    A = np.where(band[..., None], np.array((.56, .57, .59), np.float32), A)
m = text_mask('CRUSH CORE', 18, w, h, w * .5, h * .5, rotate=90, sx=asp)
A = A * (1 - m[..., None] * .9) + np.array((.70, .08, .05), np.float32) * m[..., None] * .9
c.albedo[sy, sx] = A; c.height[sy, sx] = H; c.gloss[sy, sx] = G

c.save('shab_mech', nstrength=1.0, cavity=.25, target_p90=.80)
