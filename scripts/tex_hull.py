"""Paint the two PCM hull sheets on the layout shared with build_pcm.py.
  shab_mmod : bare Cygnus "Super" PCM, grey MMOD bumpers (paper fig. 1)
  shab_fib  : the SHAB's quilted white flexible insulation blanket (paper fig. 2)
An optional AO bake (build/tex/ao_<name>.png) from bake_ao.py multiplies in, if present."""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from tl import *
import layout as L

N = L.ATLAS
GRUNGE_FIB = .55


def strip_y(z):
    return N - (z - L.STRIP_Z0) * L.PX_PER_M


def az_x(az):
    return L.az_wrap(az) / 360 * N


AZPX = N / 360.0


def hull_sd(cx, cy, hw, hh, r, X, Y):
    # wrap in X so features crossing the seam still paint
    dx = (X - cx + N / 2) % N - N / 2
    return sd_rrect(dx, Y, 0, cy, hw, hh, r)


def paint_common_top(c):
    """Dome (polar), collar side wall, hatch disc."""
    X, Y = c.x, c.y
    # dome zone
    D = L.DOME_SIZE; cen = D / 2
    rr = np.hypot(X - cen, Y - cen) / cen * L.DOME_RMAX
    az = np.degrees(np.arctan2(X - cen, Y - cen))
    return rr, az


def paint_mmod():
    c = Canvas(N, N, albedo=(.58, .585, .60), gloss=.34)
    X, Y = c.x, c.y
    # overall finish: slightly satin anodized grey, fine weave of the Nextel-backed bumpers
    n = grime(N, N, 101, base=5)
    c.albedo *= (.92 + .16 * n)[..., None]
    c.height += weave(X, Y, 3.0) * .12 + fbm(N, N, 102, base=240, octaves=2) * .10
    y_top = strip_y(L.STRIP_Z1)
    in_strip = Y > y_top

    # gap floor between bumpers: very dark, recessed
    c.albedo[in_strip] *= 1.0

    # frames: bolt circles
    for z in L.SEG_Z:
        y = strip_y(z)
        band = np.abs(Y - y) < L.FRAME_H * L.PX_PER_M
        c.albedo[band] *= .86
        c.gloss[band] = .34   # strap webbing has a slight sheen
        c.height += fill(np.abs(Y - y) - L.FRAME_H * L.PX_PER_M, 1.2) * 2.5
        for dy in (-.45, .45):
            yy = y + dy * L.FRAME_H * L.PX_PER_M * 2 * .55
            b = (((X % 24) - 12) ** 2 + (Y - yy) ** 2) < 2.6 ** 2
            c.height += b * 1.6
            c.albedo[b] *= 1.25
    # ribs
    for rib in L.RIB_AZ:
        cx = az_x(rib)
        dx = (X - cx + N / 2) % N - N / 2
        m = (np.abs(dx) < L.RIB_HALF * AZPX) & in_strip & (Y < strip_y(L.SEG_Z[0]))
        c.albedo[m] *= .80
        c.height += m * 1.2
        for off in (-.55, .55):
            b = (((Y % 26) - 13) ** 2 + (dx - off * L.RIB_HALF * AZPX) ** 2 < 2.2 ** 2) & m
            c.height += b * 1.5
            c.albedo[b] *= 1.3
    # bumper panels: chamfered highlight, embossed inner frame, eight fasteners, IDs
    r = rng(103)
    letters = 'ABCDEF'
    for s in range(4):
        z0, z1 = L.SEG_Z[s] + L.FRAME_H, L.SEG_Z[s + 1] - L.FRAME_H
        zm = (z0 + z1) / 2
        for pz0, pz1, row in ((z0, zm - L.PANEL_GAP_Z, 0), (zm + L.PANEL_GAP_Z, z1, 1)):
            cy = strip_y((pz0 + pz1) / 2); hh = (pz1 - pz0) / 2 * L.PX_PER_M
            for b, baz in enumerate(L.BAY_AZ):
                cx = az_x(baz); hw = (L.BAY_W / 2 - L.RIB_HALF) * AZPX
                sd = hull_sd(cx, cy, hw, hh, 5, X, Y)
                ins = fill(sd)
                # panel tone varies a touch, like individually bonded sheets
                tone = r.uniform(.96, 1.06)
                c.albedo *= (1 + ins[..., None] * (tone - 1))
                # lit top chamfer
                edge = np.exp(-np.abs(sd) / 2.0)
                c.albedo *= (1 - edge[..., None] * .35)
                top = fill(np.abs(Y - (cy - hh + 5)) - 1.6) * fill(np.abs(((X - cx + N / 2) % N - N / 2)) - hw + 12)
                c.albedo += top[..., None] * .22
                # inner embossed frame like Cygnus' stiffened panels (fig. 1)
                sd2 = hull_sd(cx, cy, hw - 16, hh - 16, 4, X, Y)
                c.height += bevel(sd2, 2.5) * 1.3
                c.albedo *= (1 - np.exp(-np.abs(sd2) / 1.4)[..., None] * .22)
                # fasteners: corners and mid edges
                for fx in (-1, 0, 1):
                    for fy in (-1, 1):
                        px = (cx + fx * (hw - 8)) % N; py = cy + fy * (hh - 8)
                        d = hull_sd(px, py, 2.6, 2.6, 2.6, X, Y)
                        c.height += fill(d, .8) * 1.6
                        c.albedo *= (1 - fill(d - 1, 1)[..., None] * .35)
                # small stencil ID
                c.add_text(f'{letters[b]}{s + 1}{row + 1}', cx - hw + 14, cy + hh - 26, 13, rgb=(.1, .1, .11), opacity=.6)
    # scuffs and soft staining
    c.albedo += scratches(N, N, 104, n=2000, length=(6, 70))[..., None] * .05
    c.albedo *= (.96 + .08 * grime(N, N, 105, base=24))[..., None]
    # aft skirt darker where it meets the service module

    # large identification and tracking marks
    c.add_text('SHAB-01', az_x(120) - 90, strip_y(.86), 60, rgb=(.08, .08, .09), opacity=.8)
    for az_, z_ in ((30 + 8, .2), (-90 - 8, -.5), (150, .75), (-150, -1.3)):
        d = hull_sd(az_x(az_), strip_y(z_), 15, 15, 15, X, Y)
        c.tint(fill(d), (.92, .92, .9), 1)
        c.tint(fill(hull_sd(az_x(az_), strip_y(z_), 6, 6, 6, X, Y)), (.04, .04, .04), 1)
    paint_dome(c, 'mmod')
    paint_door(c)
    paint_ring(c)
    apply_bake(c, 'shab_mmod')
    c.save('shab_mmod', nstrength=1.15, cavity=.35)


def paint_dome(c, kind):
    """Crown: 12 trapezoid recesses around the CBM (fig. 1), or FIB petals."""
    X, Y = c.x, c.y
    D = L.DOME_SIZE; cen = D / 2
    sy, sx = slice(0, D), slice(0, D)
    dx, dy = X[sy, sx] - cen, Y[sy, sx] - cen
    rr = np.hypot(dx, dy) / cen * L.DOME_RMAX
    az = np.degrees(np.arctan2(dx, dy))
    nb = 12
    daz = ((az + 180 / nb) % (360 / nb)) - 180 / nb
    c.height[sy, sx] = 0
    if kind == 'mmod':
        base = np.array((.62, .625, .64), np.float32)
        c.albedo[sy, sx] = base * (.94 + .1 * grime(D, D, 111, base=4))[..., None]
        # trapezoids: radial window r in .66...86, angular half-width 11 deg
        d = np.maximum(np.abs(rr - .885) - .115, (np.abs(daz) - 11) * math.pi / 180 * rr)
        d_px = d * cen
        ins = fill(d_px, 1.5)
        c.height[sy, sx] += -bevel(d_px, 5) * 3
        c.albedo[sy, sx] *= (1 - np.exp(-np.abs(d_px) / 2.5)[..., None] * .55)
        c.albedo[sy, sx] += ins[..., None] * np.array((.22, .22, .20), np.float32)
        # bolt circle
        for ring, cnt in ((1.09, 96), (.69, 72)):
            ang = (az % (360 / cnt)) - 180 / cnt
            b = (np.abs(rr - ring) * cen) ** 2 + (ang * math.pi / 180 * rr * cen) ** 2 < 2.4 ** 2
            c.height[sy, sx] += b * 1.6
    else:
        wedge = (np.abs(daz) < .5 * 360 / nb)
        base = np.array((.84, .84, .81), np.float32)
        c.albedo[sy, sx] = base * (.96 + .08 * grime(D, D, 112, base=4))[..., None]
        # concentric + radial quilting
        rcell = (rr * 18) % 1
        acell = (az / (360 / 36)) % 1
        pillow = np.clip(1 - (2 * rcell - 1) ** 4 - (2 * acell - 1) ** 4, 0, 1)
        c.height[sy, sx] += pillow * 1.0
        lines = np.minimum(np.minimum(rcell, 1 - rcell) * cen / 18 * L.DOME_RMAX, np.minimum(acell, 1 - acell) * rr * cen * 2 * math.pi / 36)
        c.albedo[sy, sx] *= (1 - np.exp(-lines / 1.1)[..., None] * .2)
    # keep everything past the rim from bleeding oddly: nothing to do, unused area
    return c


def paint_door(c):
    """Exterior airlock door, flat: recessed skin, dogging bars, viewport ring, handle."""
    x0, y0, w, h = L.DOOR_ZONE
    sy, sx = slice(y0, y0 + h), slice(x0, x0 + w)
    X, Y = c.x[sy, sx] - x0, c.y[sy, sx] - y0
    c.albedo[sy, sx] = np.array((.80, .80, .79), np.float32) * (.95 + .1 * grime(h, w, 121, base=5))[..., None]
    c.gloss[sy, sx] = .3
    c.height[sy, sx] = 0
    H = np.zeros((h, w), np.float32)
    A = c.albedo[sy, sx]
    cx, cy = w / 2, h / 2
    sd = sd_rrect(X, Y, cx, cy, w / 2 - 14, h / 2 - 14, 60)
    H += -bevel(sd, 10) * 5
    A *= (1 - np.exp(-np.abs(sd) / 3)[..., None] * .5)
    # horizontal stiffeners
    for t in (.28, .5, .72):
        d = sd_rrect(X, Y, cx, h * t, w / 2 - 54, 9, 8)
        H += bevel(d, 3) * 3
        A *= (1 - np.exp(-np.abs(d) / 2)[..., None] * .25)
    # vertical spine
    d = sd_rrect(X, Y, cx, cy, 10, h / 2 - 54, 8)
    H += bevel(d, 3) * 3
    A *= (1 - np.exp(-np.abs(d) / 2)[..., None] * .25)
    # viewport
    d = sd_circle(X, Y, cx, h * .21, 58)
    H += bevel(d, 8) * 5 - bevel(d + 20, 5) * 5
    A *= (1 - np.exp(-np.abs(d) / 3)[..., None] * .4)
    glass = fill(d + 22)
    A[:] = A * (1 - glass[..., None]) + np.array((.02, .05, .09), np.float32) * glass[..., None]
    c.gloss[sy, sx] = c.gloss[sy, sx] * (1 - glass) + .95 * glass
    # handle housing
    d = sd_rrect(X, Y, cx, h * .62, 72, 44, 14)
    H += -bevel(d, 5) * 3
    m = fill(d)
    A[:] = A * (1 - m[..., None]) + np.array((.2, .2, .22), np.float32) * m[..., None]
    # bolts around the rim
    for i in range(44):
        t = i / 44 * 2 * math.pi
        px = cx + (w / 2 - 26) * np.sign(math.cos(t)) * min(1, abs(math.cos(t)) * 1.6)
        py = cy + (h / 2 - 26) * np.sign(math.sin(t)) * min(1, abs(math.sin(t)) * 1.6)
        d = sd_circle(X, Y, px, py, 5)
        H += fill(d, 1) * 2.4
        A *= (1 - fill(d - 2, 1)[..., None] * .25)
    c.height[sy, sx] += H
    # stencils
    c.add_text('EVA HATCH', x0 + w / 2 - 80, y0 + h * .78, 34, rgb=(.05, .05, .06))
    c.add_text('DUST LOCK ENGAGED BEFORE OPENING', x0 + w / 2 - 158, y0 + h * .83, 18, rgb=(.05, .05, .06))
    c.add_text('PULL', x0 + w / 2 - 26, y0 + h * .55, 22, rgb=(.7, .08, .05))
    # hazard bar
    bar = fill(sd_rrect(c.x[sy, sx] - x0, c.y[sy, sx] - y0, w / 2, h * .90, w / 2 - 54, 10, 2))
    st = ((X + Y) % 28) < 14
    c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - bar[..., None]) + np.where(st[..., None], np.array((.82, .66, .1), np.float32), np.array((.04, .04, .04), np.float32)) * bar[..., None]


def paint_ring(c):
    # collar side wall: bare aluminium ring with CBM bolts and alignment guides
    x0, y0, w, h = L.RING_ZONE
    sy, sx = slice(y0, y0 + h), slice(x0, x0 + w)
    X, Y = c.x[sy, sx] - x0, c.y[sy, sx] - y0
    c.albedo[sy, sx] = np.array((.70, .70, .72), np.float32) * (.92 + .16 * grime(h, w, 131, base=8))[..., None]
    c.height[sy, sx] = 0
    c.gloss[sy, sx] = .6
    b = ((X % 20) - 10) ** 2 + (Y - h * .3) ** 2 < 5 ** 2
    c.height[sy, sx] += b * 2.2
    c.albedo[sy, sx] *= (1 - (((X % 20) - 10) ** 2 + (Y - h * .3) ** 2 < 9 ** 2)[..., None] * .2)
    c.height[sy, sx] += fill(np.abs(Y - h * .75) - 4, 1) * 2
    # hatch disc
    x0, y0, w, h = L.DECK_ZONE
    sy, sx = slice(y0, y0 + h), slice(x0, x0 + w)
    X, Y = c.x[sy, sx] - x0, c.y[sy, sx] - y0
    cx = w / 2
    rr = np.hypot(X - cx, Y - cx)
    c.albedo[sy, sx] = np.array((.82, .82, .82), np.float32) * (.95 + .1 * grime(h, w, 132, base=5))[..., None]
    c.height[sy, sx] = 0
    c.gloss[sy, sx] = .35
    c.height[sy, sx] += -fill(np.abs(rr - w * .44) - 3, 1) * 3 + fill(np.abs(rr - w * .20) - 4, 1) * 3
    c.albedo[sy, sx] *= (1 - np.exp(-np.abs(rr - w * .44) / 2.5)[..., None] * .4)
    az = np.degrees(np.arctan2(X - cx, Y - cx))
    ang = (az % 22.5) - 11.25
    c.height[sy, sx] += ((np.abs(rr - w * .32)) ** 2 + (ang * math.pi / 180 * rr) ** 2 < 8 ** 2) * 2.5


def paint_fib():
    """Woven silica FIB quilt: about 17 cm cells at KSP scale, fine stitch lines, gentle
    patchwork by blanket, bigger proud seams, gaskets where the door and windows pass."""
    c = Canvas(N, N, albedo=(.85, .85, .83), gloss=.24)     # woven cloth
    X, Y = c.x, c.y
    cell = 60.0
    fx = (X % cell) / cell; fy = (Y % cell) / cell
    pillow = np.clip(1 - np.abs(2 * fx - 1) ** 4 - np.abs(2 * fy - 1) ** 4, 0, 1)
    c.height += pillow * .9
    dist = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy)) * cell
    c.albedo *= (1 - np.exp(-dist / 1.1)[..., None] * .20)
    # running stitches along the quilt lines read as the paper's dotted CAD lines
    st = (((X % 9) < 4) & (dist < .9)) | (((Y % 9) < 4) & (dist < .9))
    c.albedo[st] *= .78
    c.gloss[st] = .10         # thread is duller than the cloth
    wv = weave(X, Y, 2.6)
    c.height += wv * .20
    c.albedo *= (.98 + .04 * wv)[..., None]
    # blanket sheets, 8x5 cells: quiet tonal patchwork
    r = rng(201)
    bw, bh = cell * 8, cell * 5
    ci = np.floor(X / bw).astype(int); cj = np.floor(Y / bh).astype(int)
    tone = r.uniform(.975, 1.025, 4096)
    warm = r.uniform(-.004, .007, 4096)
    idx = (ci * 37 + cj * 101) % 4096
    c.albedo *= tone[idx][..., None]
    c.albedo[..., 0] += warm[idx]; c.albedo[..., 2] -= warm[idx] * 1.4
    sx_ = np.minimum(X % bw, bw - X % bw); sy_ = np.minimum(Y % bh, bh - Y % bh)
    seam = np.minimum(sx_, sy_)
    c.albedo *= (1 - np.exp(-seam / 1.6)[..., None] * .22)
    c.height += fill(seam - 2.5, 1) * 1.1
    c.gloss[seam < 2.5] = .12
    # soot near the lander, soft mottling
    st2 = grime(N, N, 202, base=9)
    c.albedo *= (.97 + .05 * st2)[..., None]
    # tie-down straps at each segment frame
    for z in L.SEG_Z:
        yy = strip_y(z)
        band = np.abs(Y - yy) < 9
        c.albedo[band] *= .86
        c.gloss[band] = .34   # strap webbing has a slight sheen
        c.height += fill(np.abs(Y - yy) - 9, 1.2) * 2.2
        b = (((X % 40) - 20) ** 2 + (Y - yy) ** 2) < 2.6 ** 2
        c.height += b * 1.4
        c.albedo[b] *= 1.12
        c.gloss[b] = .85      # metal snaps catch the light even where the relief is too small to see
    for cx_az, zc, w_, h_ in ((L.HATCH_AZ, L.HATCH_Z, L.HATCH_W, L.HATCH_H), (L.WIN_AZ, L.WIN_Z[0], L.WIN_W, L.WIN_H), (L.WIN_AZ, L.WIN_Z[1], L.WIN_W, L.WIN_H)):
        sd = hull_sd(az_x(cx_az), strip_y(zc), (w_ / 2 + .06) * L.PX_PER_M, (h_ / 2 + .06) * L.PX_PER_M, 16, X, Y)
        ring = fill(np.abs(sd) - 6)
        c.albedo *= (1 - ring[..., None] * .30)
        c.height += ring * 1.8
        c.gloss[ring > .5] = .48    # gasket
    c.add_text('SHAB-01', az_x(120) - 110, strip_y(.45), 74, rgb=(.07, .07, .08), opacity=.85)
    c.add_text('SHAB-01', az_x(-120) - 110, strip_y(-.42) , 74, rgb=(.07, .07, .08), opacity=.85)
    c.add_text('FIB-2  NO STEP', az_x(180) - 70, strip_y(.05), 22, rgb=(.1, .1, .1), opacity=.7)
    c.add_text('EVA EGRESS', az_x(0) - 58, strip_y(-.30) + 6, 22, rgb=(.1, .1, .1), opacity=.7)
    for az_, z_ in ((30 + 9, -.35), (-90 + 9, -1.35), (150 - 9, -.55), (-150 + 9, .8), (90 - 8, .85)):
        c.tint(fill(hull_sd(az_x(az_), strip_y(z_), 15, 15, 15, X, Y)), (.08, .08, .08), .9)
        c.tint(fill(hull_sd(az_x(az_), strip_y(z_), 6, 6, 6, X, Y)), (.92, .92, .9), 1)
        c.gloss[hull_sd(az_x(az_), strip_y(z_), 15, 15, 15, X, Y) < 0] = .7     # alignment targets are enamel
    # blanket lower edge turn-back onto the aft skirt
    paint_dome(c, 'fib')
    paint_door(c)
    paint_ring(c)
    # surface variation goes in gloss only; glass keeps its finish
    g = gloss_grunge(N, N, 203)
    c.gloss = np.where(c.gloss > .9, c.gloss, np.clip(c.gloss * (1 + GRUNGE_FIB * g), .03, 1))
    apply_bake(c, 'shab_fib')
    c.save('shab_fib', nstrength=.9, cavity=.2, target_p90=.79)


def apply_bake(c, name):
    """Multiply in the Cycles AO bake, with a contact-shadow curve and a touch of denoise."""
    p = os.path.join(OUT, f'ao_{name}.png')
    if os.path.exists(p):
        ao = np.asarray(Image.open(p).convert('L')).astype(np.float32) / 255
        ao = blur(ao, .8)
        c.ao = np.clip(ao, .12, 1) ** .9
        print('applied AO bake', p, round(float(ao.mean()), 3))


if __name__ == '__main__':
    which = sys.argv[1:] or ['mmod', 'fib']
    if 'mmod' in which:
        paint_mmod()
    if 'fib' in which:
        paint_fib()
