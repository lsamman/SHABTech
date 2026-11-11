"""Sheets for the surface parts: shab_surface (trim), shab_rover and shab_isru (unique, AO baked), shab_wiremesh (cutout)."""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from tl import *
from surface_layout import *


def zone_view(c, z):
    x, y, w, h = z
    return slice(y, y + h), slice(x, x + w), c.x[y:y + h, x:x + w] - x, c.y[y:y + h, x:x + w] - y, w, h


def fasteners(h_, a, xs, ys, r=3.0, depth=1.5, shade=.25):
    for fx in xs:
        for fy in ys:
            pass


def bolt(H, A, X, Y, px, py, r=3.2, up=1.6, shade=.28):
    d = sd_circle(X, Y, px, py, r)
    H += fill(d, 1.0) * up
    A *= (1 - fill(d - 1.6, 1.0)[..., None] * shade)
    A += fill(d + 1.0, .8)[..., None] * .05


def stencil(c, text, x, y, size, rgb=(.05, .05, .06), op=.88):
    c.add_text(text, x, y, size, rgb=rgb, opacity=op)


def trefoil_mask(X, Y, cx, cy, R):
    """IEC radiation trefoil, 0..1 coverage."""
    dx, dy = X - cx, Y - cy
    r = np.hypot(dx, dy)
    a = np.degrees(np.arctan2(dx, -dy))
    ang = (a + 180) % 120 - 60
    blade = (np.abs(ang) < 30) & (r > R * .27) & (r < R)
    core = r < R * .18
    return np.clip(blur((blade | core).astype(np.float32), .8), 0, 1)


def surface():
    c = Canvas(2048, 2048, albedo=(.5, .5, .5), gloss=.3)
    # --- reactor vessel: dull Inconel with weld seams, heat tint, and a bolted head ring
    sy, sx, X, Y, w, h = zone_view(c, SURF['vessel'])
    g = grime(h, w, 401, base=5)
    c.albedo[sy, sx] = np.array((.40, .39, .37), np.float32) * (.82 + .36 * g)[..., None]
    c.gloss[sy, sx] = .34
    H = fbm(h, w, 402, base=70, octaves=3) * .25
    heat = np.exp(-((Y - h * .55) / (h * .24)) ** 2)
    tint = np.dstack([1 + .10 * heat, 1 - .04 * heat, 1 - .22 * heat])
    for t in (.18, .42, .68, .86):
        d = np.abs(Y - h * t) - 3.5
        H += fill(d, 1.5) * 1.8
        c.albedo[sy, sx] *= (1 - np.exp(-np.abs(d) / 3)[..., None] * .22)
        ripple = (np.sin(X * 2 * np.pi / 7) * .5 + .5) * fill(d, 1)
        H += ripple * .5
    for i in range(32):
        bolt(H, c.albedo[sy, sx], X, Y, (i + .5) / 32 * w, h * .93, 4)
    c.height[sy, sx] += H
    c.albedo[sy, sx] += scratches(h, w, 403, n=240)[..., None] * .03

    # --- shadow shield: tungsten and LiH plates
    sy, sx, X, Y, w, h = zone_view(c, SURF['shield'])
    g = grime(h, w, 411, base=4)
    c.albedo[sy, sx] = np.array((.26, .26, .28), np.float32) * (.82 + .36 * g)[..., None]
    c.gloss[sy, sx] = .38
    H = fbm(h, w, 412, base=90, octaves=2) * .15
    for i in range(3):
        for j in range(3):
            cx, cy = w * (i + .5) / 3, h * (j + .5) / 3
            sd = sd_rrect(X, Y, cx, cy, w / 6 - 8, h / 6 - 8, 8)
            H += bevel(sd, 5) * 2.4
            c.albedo[sy, sx] *= (1 - np.exp(-np.abs(sd) / 2.5)[..., None] * .5)
            for fx in (-1, 0, 1):
                for fy in (-1, 0, 1):
                    if fx or fy:
                        bolt(H, c.albedo[sy, sx], X, Y, cx + fx * (w / 6 - 22), cy + fy * (h / 6 - 22), 4.5, 2.2)
    c.height[sy, sx] += H
    m = fill(sd_rrect(X, Y, w / 2, h / 2, w * .17, h * .17, 6))
    c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - m[..., None]) + np.array((.82, .66, .10), np.float32) * m[..., None]
    tm = trefoil_mask(X, Y, w / 2, h / 2, w * .135)
    c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - tm[..., None]) + np.array((.03, .03, .03), np.float32) * tm[..., None]
    x0, y0 = SURF['shield'][:2]
    stencil(c, 'RADIATION SHIELD', x0 + 138, y0 + 400, 30, (.72, .70, .62))
    stencil(c, 'NO EVA REAR ARC WITHIN 100 M', x0 + 92, y0 + 444, 22, (.72, .70, .62))

    # --- heat-pipe panel: white, longitudinal pipes, root manifold darker, tip stencil
    sy, sx, X, Y, w, h = zone_view(c, SURF['heatpipe'])
    c.albedo[sy, sx] = np.array((.84, .84, .82), np.float32) * (.94 + .1 * grime(h, w, 421, base=5))[..., None]
    c.gloss[sy, sx] = .42
    H = np.zeros((h, w), np.float32)
    pipes = (np.cos(X * 2 * np.pi / (w / 7)) * .5 + .5) ** 2.4
    H += pipes * 3.2
    c.albedo[sy, sx] *= (.88 + .16 * pipes)[..., None]
    for t in np.linspace(.08, .92, 7):
        H += fill(np.abs(Y - h * t) - 2, 1) * 1.1
        c.albedo[sy, sx] *= (1 - fill(np.abs(Y - h * t) - 1, 1)[..., None] * .10)
    root = Y > h * .92
    c.albedo[sy, sx][root] = np.array((.5, .5, .52), np.float32)
    rim = sd_rrect(X, Y, w / 2, h / 2, w / 2 - 6, h / 2 - 6, 4)
    c.albedo[sy, sx] *= (1 - np.exp(-np.abs(rim) / 3)[..., None] * .35)
    H += bevel(rim, 4) * 1.2
    c.height[sy, sx] += H
    x0, y0 = SURF['heatpipe'][:2]
    stencil(c, 'HOT', x0 + 26, y0 + 22, 30, (.7, .08, .05))

    # --- HV cable wound on the drum: orange with dark helix (U around, V across the drum)
    sy, sx, X, Y, w, h = zone_view(c, SURF['cable'])
    wraps = 26.0
    ph = (Y / h * wraps + X / w) % 1
    prof = np.sqrt(np.clip(1 - (2 * ph - 1) ** 2, 0, 1))
    c.albedo[sy, sx] = np.array((.80, .34, .06), np.float32) * (.32 + .78 * prof)[..., None]
    c.gloss[sy, sx] = .36
    c.height[sy, sx] += prof * 4.5
    bands = ((X // (w / 9)) % 2 == 0) & (np.abs(ph - .5) < .46)
    c.albedo[sy, sx] = np.where(((X % (w / 9)) < 4)[..., None], c.albedo[sy, sx] * .3, c.albedo[sy, sx])

    # --- titanium chevron strip
    sy, sx, X, Y, w, h = zone_view(c, SURF['tread'])
    c.albedo[sy, sx] = np.array((.56, .55, .52), np.float32) * (.86 + .3 * grime(h, w, 431, base=6))[..., None]
    c.gloss[sy, sx] = .52
    c.albedo[sy, sx] += scratches(h, w, 432, n=500, length=(4, 30))[..., None] * .12
    c.height[sy, sx] += ((Y % 26) < 7) * 1.1

    # --- control box face
    sy, sx, X, Y, w, h = zone_view(c, SURF['ctrl'])
    c.albedo[sy, sx] = np.array((.72, .72, .71), np.float32) * (.95 + .1 * grime(h, w, 441, base=4))[..., None]
    c.gloss[sy, sx] = .3
    H = np.zeros((h, w), np.float32)
    sd = sd_rrect(X, Y, w / 2, h / 2, w / 2 - 10, h / 2 - 10, 8)
    H += -bevel(sd, 3) * 1.5
    c.albedo[sy, sx] *= (1 - np.exp(-np.abs(sd) / 2)[..., None] * .4)
    r = rng(442)
    for j in range(2):
        for i in range(4):
            cx, cy = 42 + i * 56, 54 + j * 56
            H += bevel(sd_circle(X, Y, cx, cy, 20), 5) * 3.5 - bevel(sd_circle(X, Y, cx, cy, 10), 3) * 3.5
            mm = fill(sd_circle(X, Y, cx, cy, 10))
            col = np.array((.72, .55, .22) if r.random() < .5 else (.05, .05, .05), np.float32)
            c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - mm[..., None]) + col * mm[..., None]
    for i in range(5):
        mm = fill(sd_rrect(X, Y, 44 + i * 32, 158, 10, 5, 2))
        col = np.array(((.1, .6, .15), (.1, .6, .15), (.85, .55, .1), (.1, .6, .15), (.7, .1, .06))[i], np.float32)
        c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - mm[..., None]) + col * mm[..., None]
    c.height[sy, sx] += H
    x0, y0 = SURF['ctrl'][:2]
    stencil(c, 'REACTOR CONTROL', x0 + 34, y0 + 16, 20)
    stencil(c, 'SCRAM', x0 + 40, y0 + 184, 22, (.7, .08, .05))
    stencil(c, '440 V DC', x0 + 130, y0 + 186, 18)
    stencil(c, 'SHAB-PWR-1', x0 + 40, y0 + 216, 18)

    # --- wheel hub
    sy, sx, X, Y, w, h = zone_view(c, SURF['hub'])
    c.albedo[sy, sx] = np.array((.34, .34, .36), np.float32) * (.9 + .2 * grime(h, w, 451, base=5))[..., None]
    c.gloss[sy, sx] = .48
    rr = np.hypot(X - w / 2, Y - h / 2)
    a = np.arctan2(Y - h / 2, X - w / 2)
    c.height[sy, sx] += ((rr % 22) < 4) * 1.8
    c.albedo[sy, sx] *= (.82 + .25 * ((rr % 22) < 4))[..., None]
    for i in range(10):
        t = 2 * np.pi * i / 10
        H2 = c.height[sy, sx]
        bolt(H2, c.albedo[sy, sx], X, Y, w / 2 + math.cos(t) * w * .3, h / 2 + math.sin(t) * h * .3, 6, 3)

    # --- chassis trim (reused on brackets and side boxes)
    sy, sx, X, Y, w, h = zone_view(c, SURF['chassis'])
    c.albedo[sy, sx] = np.array((.72, .72, .71), np.float32) * (.93 + .14 * grime(h, w, 461, base=6))[..., None]
    c.gloss[sy, sx] = .3
    H = fbm(h, w, 462, base=80, octaves=2) * .1
    for cx in np.arange(128, w, 256):
        sd = sd_rrect(X, Y, cx, h / 2, 118, h / 2 - 12, 6)
        H += bevel(sd, 3) * 1.8
        c.albedo[sy, sx] *= (1 - np.exp(-np.abs(sd) / 2)[..., None] * .4)
        for fx in (-1, 1):
            for fy in (-1, 0, 1):
                bolt(H, c.albedo[sy, sx], X, Y, cx + fx * 102, h / 2 + fy * (h / 2 - 26), 3.5)
    c.height[sy, sx] += H

    sy, sx, X, Y, w, h = zone_view(c, SURF['cdeck'])
    c.albedo[sy, sx] = np.array((.36, .37, .38), np.float32) * (.88 + .24 * grime(h, w, 471, base=5))[..., None]
    c.gloss[sy, sx] = .34
    d = ((X + (Y // 18) % 2 * 9) % 18 - 9) ** 2 + ((Y % 18) - 9) ** 2 * 6
    c.height[sy, sx] += (d < 40) * 1.2
    c.albedo[sy, sx] *= (.86 + .28 * (d < 40))[..., None]

    # --- trefoil label
    sy, sx, X, Y, w, h = zone_view(c, SURF['trefoil'])
    c.albedo[sy, sx] = np.array((.84, .68, .10), np.float32)
    c.gloss[sy, sx] = .3
    tm = trefoil_mask(X, Y, w / 2, h * .43, w * .35)
    c.albedo[sy, sx] = c.albedo[sy, sx] * (1 - tm[..., None]) + np.array((.03, .03, .03), np.float32) * tm[..., None]
    x0, y0 = SURF['trefoil'][:2]
    stencil(c, 'CAUTION', x0 + 72, y0 + 212, 28)

    # --- dark electronics enclosure
    sy, sx, X, Y, w, h = zone_view(c, SURF['dark_box'])
    c.albedo[sy, sx] = np.array((.16, .16, .17), np.float32) * (.9 + .2 * grime(h, w, 475, base=5))[..., None]
    c.gloss[sy, sx] = .3
    H = np.zeros((h, w), np.float32)
    sd = sd_rrect(X, Y, w / 2, h / 2, w / 2 - 10, h / 2 - 10, 6)
    H += bevel(sd, 3) * 2
    for fx in (-1, 1):
        for fy in (-1, 1):
            bolt(H, c.albedo[sy, sx], X, Y, w / 2 + fx * (w / 2 - 22), h / 2 + fy * (h / 2 - 22), 4.5, 2)
    c.height[sy, sx] += H

    # --- solid-oxide stack: alternating ceramic and interconnect plates
    sy, sx, X, Y, w, h = zone_view(c, SURF['soec'])
    pitch = 9.0
    plate = (Y % pitch) < 5
    c.albedo[sy, sx] = np.where(plate[..., None], np.array((.60, .58, .52), np.float32), np.array((.13, .12, .11), np.float32))
    c.albedo[sy, sx] *= (.82 + .3 * grime(h, w, 481, base=6))[..., None]
    c.gloss[sy, sx] = .25
    c.height[sy, sx] += blur(plate.astype(np.float32), .6) * 3
    heat = np.exp(-((Y - h * .5) / (h * .45)) ** 2)
    c.albedo[sy, sx] *= np.dstack([1 + .15 * heat, 1 - .02 * heat, 1 - .3 * heat])
    for cx in (w * .08, w * .92):
        H2 = c.height[sy, sx]
        H2 += fill(np.abs(X - cx) - 8, 1) * 3

    # --- pleated dust filter
    sy, sx, X, Y, w, h = zone_view(c, SURF['filter'])
    pleat = np.abs(((X % 14) / 14) * 2 - 1)
    c.albedo[sy, sx] = np.array((.78, .76, .68), np.float32) * (.5 + .6 * pleat)[..., None]
    c.albedo[sy, sx] *= (.78 + .4 * grime(h, w, 491, base=6))[..., None] * np.array((1, .9, .78), np.float32)
    c.gloss[sy, sx] = .08
    c.height[sy, sx] += pleat * 4

    # --- ISRU rack label plate
    sy, sx, X, Y, w, h = zone_view(c, SURF['isru'])
    c.albedo[sy, sx] = np.array((.74, .74, .73), np.float32) * (.94 + .12 * grime(h, w, 495, base=5))[..., None]
    c.gloss[sy, sx] = .3
    H = np.zeros((h, w), np.float32)
    sd = sd_rrect(X, Y, w / 2, h / 2, w / 2 - 10, h / 2 - 10, 6)
    H += bevel(sd, 3) * 1.5
    c.albedo[sy, sx] *= (1 - np.exp(-np.abs(sd) / 2)[..., None] * .35)
    for fx in (-1, 1):
        for fy in (-1, 1):
            bolt(H, c.albedo[sy, sx], X, Y, w / 2 + fx * (w / 2 - 22), h / 2 + fy * (h / 2 - 22), 4.5, 2)
    c.height[sy, sx] += H
    x0, y0 = SURF['isru'][:2]
    stencil(c, 'O2 PLANT', x0 + 40, y0 + 36, 62)
    stencil(c, 'CO2 IN  /  CO VENT  /  O2 OUT', x0 + 40, y0 + 120, 26)
    stencil(c, 'SOLID OXIDE ELECTROLYSIS 1100 K', x0 + 40, y0 + 164, 22, (.7, .08, .05))

    # --- tanks
    for k, base, txt, seed in (('lox', (.86, .86, .84), 'LOX', 501), ('h2o', (.40, .47, .56), 'H2O', 511)):
        sy, sx, X, Y, w, h = zone_view(c, SURF[k])
        c.albedo[sy, sx] = np.array(base, np.float32) * (.93 + .14 * grime(h, w, seed, base=5))[..., None]
        c.gloss[sy, sx] = .42
        H = np.zeros((h, w), np.float32)
        for t in (.12, .88):
            d = np.abs(Y - h * t) - 3
            H += fill(d, 1) * 2.6
            c.albedo[sy, sx] *= (1 - np.exp(-np.abs(d) / 2.5)[..., None] * .3)
            for i in range(24):
                bolt(H, c.albedo[sy, sx], X, Y, (i + .5) / 24 * w, h * t + (-11 if t < .5 else 11), 2.6, 1.4)
        c.height[sy, sx] += H
        x0, y0 = SURF[k][:2]
        stencil(c, txt, x0 + 58, y0 + 94, 44, (.05, .05, .06) if k == 'lox' else (.9, .9, .88))
        stencil(c, txt, x0 + 250, y0 + 94, 44, (.05, .05, .06) if k == 'lox' else (.9, .9, .88))

    # --- fin block
    sy, sx, X, Y, w, h = zone_view(c, SURF['fins'])
    fn = ((X % 16) < 6)
    c.albedo[sy, sx] = np.where(fn[..., None], np.array((.74, .74, .76), np.float32), np.array((.13, .13, .14), np.float32))
    c.gloss[sy, sx] = .5
    c.height[sy, sx] += blur(fn.astype(np.float32), .7) * 4

    # --- Stirling converter: bead-blasted casing, ring seams, copper cooler stripe
    sy, sx, X, Y, w, h = zone_view(c, SURF['stirling'])
    c.albedo[sy, sx] = np.array((.5, .5, .52), np.float32) * (.88 + .24 * grime(h, w, 521, base=6))[..., None]
    c.gloss[sy, sx] = .46
    H = np.zeros((h, w), np.float32)
    for t in (.1, .35, .62, .9):
        H += fill(np.abs(Y - h * t) - 3, 1) * 2.2
    cool = (Y > h * .66) & (Y < h * .86)
    ribs = (Y % 10) < 4
    c.albedo[sy, sx] = np.where((cool & ribs)[..., None], np.array((.70, .42, .22), np.float32), c.albedo[sy, sx])
    H += (cool & ribs) * 2.5
    c.height[sy, sx] += H

    # --- flange, valve body
    sy, sx, X, Y, w, h = zone_view(c, SURF['flange'])
    c.albedo[sy, sx] = np.array((.6, .6, .62), np.float32) * (.88 + .24 * grime(h, w, 531, base=5))[..., None]
    c.gloss[sy, sx] = .5
    rr = np.hypot(X - w / 2, Y - h / 2)
    H = fill(np.abs(rr - w * .42) - 3, 1) * 2 + fill(np.abs(rr - w * .22) - 3, 1) * 2
    for i in range(12):
        t = 2 * np.pi * i / 12
        bolt(H, c.albedo[sy, sx], X, Y, w / 2 + math.cos(t) * w * .32, h / 2 + math.sin(t) * h * .32, 7, 3)
    c.height[sy, sx] += H
    sy, sx, X, Y, w, h = zone_view(c, SURF['valve'])
    c.albedo[sy, sx] = np.array((.70, .62, .28), np.float32) * (.86 + .28 * grime(h, w, 541, base=5))[..., None]
    c.gloss[sy, sx] = .55
    c.height[sy, sx] += fill(np.abs(Y - h / 2) - 7, 1) * 3 + fill(np.abs(X - w / 2) - 7, 1) * 3
    c.save('shab_surface', nstrength=1.05, cavity=.3)


def apply_bake(c, name):
    p = os.path.join(OUT, f'ao_{name}.png')
    if os.path.exists(p):
        ao = np.asarray(Image.open(p).convert('L')).astype(np.float32) / 255
        c.ao = np.clip(blur(ao, .7), .14, 1) ** .95
        print('applied AO bake', p, round(float(ao.mean()), 3))


def panels_hor(c, H, A, X, Y, w, h, n, inset=6, seed=0, tone=.04):
    """Row of n fastened skin panels across a zone view."""
    r = rng(seed)
    for i in range(n):
        cx = w * (i + .5) / n
        sd = sd_rrect(X, Y, cx, h / 2, w / n / 2 - inset, h / 2 - inset, 3)
        A *= (1 + fill(sd)[..., None] * r.uniform(-tone, tone))
        A *= (1 - np.exp(-np.abs(sd) / 1.5)[..., None] * .45)
        H += bevel(sd, 2) * 1.2
        k = 3 if w / n > 70 else 2
        for fx in np.linspace(-1, 1, k):
            for fy in (-1, 1):
                bolt(H, A, X, Y, cx + fx * (w / n / 2 - inset - 7), h / 2 + fy * (h / 2 - inset - 7), 2.0, 1.1)


def rover_sheet():
    c = Canvas(ROVER_ATLAS, ROVER_ATLAS, albedo=(.70, .70, .69), gloss=.3)
    c.albedo *= (.93 + .12 * grime(ROVER_ATLAS, ROVER_ATLAS, 601, base=7))[..., None]
    c.height += fbm(ROVER_ATLAS, ROVER_ATLAS, 602, base=180, octaves=2) * .08
    ppm = 400.0
    # deck: fastened panels, grit-coated walkways down both sides, rear keep-out block
    sy, sx, X, Y, w, h = zone_view(c, ROV['deck'])
    A = c.albedo[sy, sx]; H = np.zeros((h, w), np.float32)
    for i in range(4):
        for j in range(3):
            cx, cy = w * (i + .5) / 4, h * (j + .5) / 3
            sd = sd_rrect(X, Y, cx, cy, w / 8 - 4, h / 6 - 4, 4)
            A *= (1 - np.exp(-np.abs(sd) / 1.5)[..., None] * .4)
            H += bevel(sd, 2) * 1.1
            for fx in (-1, 0, 1):
                for fy in (-1, 0, 1):
                    if fx or fy:
                        bolt(H, A, X, Y, cx + fx * (w / 8 - 13), cy + fy * (h / 6 - 13), 1.9, 1.0)
    # walkway strips along the long edges (U runs along chassis length, V across)
    for yy in (24, h - 24):
        m = fill(np.abs(Y - yy) - 18, 1)
        d = ((X + (Y // 9) % 2 * 4.5) % 9 - 4.5) ** 2 + ((Y % 9) - 4.5) ** 2 * 5
        A[:] = A * (1 - m[..., None]) + np.array((.26, .26, .27), np.float32) * (.85 + .3 * (d < 8))[..., None] * m[..., None]
        H += m * (d < 8) * .9
    # hazard band across the rear of the deck (rear = small U)
    m = fill(np.abs(X - 22) - 8, 1)
    st = ((X + Y) % 24) < 12
    A[:] = A * (1 - m[..., None]) + np.where(st[..., None], np.array((.82, .66, .10), np.float32), np.array((.04, .04, .04), np.float32)) * m[..., None]
    c.height[sy, sx] += H
    # sides
    for k, lab in (('sideL', 'SHAB-PWR-1'), ('sideR', 'SHAB-PWR-1')):
        sy, sx, X, Y, w, h = zone_view(c, ROV[k])
        A = c.albedo[sy, sx]; H = np.zeros((h, w), np.float32)
        panels_hor(c, H, A, X, Y, w, h, 4, 5, 603)
        c.height[sy, sx] += H
        x0, y0 = ROV[k][:2]
        stencil(c, lab, x0 + 30, y0 + 22, 22)
        stencil(c, 'DANGER  HIGH VOLTAGE', x0 + 340, y0 + 26, 15, (.7, .08, .05))
    for k, lab in (('front', 'FRONT'), ('rear', 'CABLE')):
        sy, sx, X, Y, w, h = zone_view(c, ROV[k])
        A = c.albedo[sy, sx]; H = np.zeros((h, w), np.float32)
        panels_hor(c, H, A, X, Y, w, h, 3, 5, 604)
        c.height[sy, sx] += H
        x0, y0 = ROV[k][:2]
        stencil(c, lab, x0 + 20, y0 + 28, 18)
    # lower-edge dust stain on every side band
    for k in ('sideL', 'sideR', 'front', 'rear'):
        sy, sx, X, Y, w, h = zone_view(c, ROV[k])
        pass
    apply_bake(c, 'shab_rover')
    c.save('shab_rover', nstrength=.9, cavity=.25)


def isru_sheet():
    c = Canvas(ISRU_ATLAS, ISRU_ATLAS, albedo=(.70, .70, .69), gloss=.3)
    c.albedo *= (.93 + .12 * grime(ISRU_ATLAS, ISRU_ATLAS, 611, base=7))[..., None]
    c.height += fbm(ISRU_ATLAS, ISRU_ATLAS, 612, base=180, octaves=2) * .08
    sy, sx, X, Y, w, h = zone_view(c, ISR['deck'])
    A = c.albedo[sy, sx]; H = np.zeros((h, w), np.float32)
    A *= np.array((.44, .44, .45), np.float32)
    d = ((X + (Y // 12) % 2 * 6) % 12 - 6) ** 2 + ((Y % 12) - 6) ** 2 * 5
    H += (d < 14) * .9
    A *= (.86 + .3 * (d < 14))[..., None]
    for fx in (-1, 1):
        for fy in (-1, 1):
            bolt(H, A, X, Y, w / 2 + fx * (w / 2 - 20), h / 2 + fy * (h / 2 - 20), 6, 2.5)
    c.height[sy, sx] += H
    for k, n, lab in (('front', 3, 'O2 PLANT  SHAB-ISRU-1'), ('rear', 2, 'KEEP INTAKE CLEAR'), ('left', 2, 'CO VENT ABOVE'), ('right', 2, 'LOX')):
        sy, sx, X, Y, w, h = zone_view(c, ISR[k])
        A = c.albedo[sy, sx]; H = np.zeros((h, w), np.float32)
        panels_hor(c, H, A, X, Y, w, h, n, 7, 613)
        c.height[sy, sx] += H
        x0, y0 = ISR[k][:2]
        stencil(c, lab, x0 + 22, y0 + 18, 20)
        c.albedo[sy, sx] *= (1 - (smooth(h * .6, h, Y) * .22)[..., None]) * np.array((1, .96, .9), np.float32)
    sy, sx, X, Y, w, h = zone_view(c, ISR['lip'])
    st = ((X + Y) % 28) < 14
    c.albedo[sy, sx] = np.where(st[..., None], np.array((.82, .66, .10), np.float32), np.array((.04, .04, .04), np.float32))
    apply_bake(c, 'shab_isru')
    c.save('shab_isru', nstrength=.9, cavity=.25)


def wiremesh():
    """Zinc-coated woven steel wire, tiled around the tyre. Alpha holds the cutout mask."""
    S = 512
    c = Canvas(S, S, albedo=(.66, .66, .66), gloss=.5)
    X, Y = c.x, c.y
    per = S / 18.0                      # diamonds per tile
    u = (X + Y) / per; v = (X - Y) / per
    du = np.abs((u % 1) - .5); dv = np.abs((v % 1) - .5)
    wire_a = du < .17; wire_b = dv < .17
    over = ((np.floor(u) + np.floor(v)) % 2) == 0
    mask = wire_a | wire_b
    H = np.zeros((S, S), np.float32)
    H += np.where(wire_a & (over | ~wire_b), (1 - du / .17) * 3, 0)
    H += np.where(wire_b & (~over | ~wire_a), (1 - dv / .17) * 3, 0)
    c.height += H
    c.albedo *= (.6 + .55 * np.clip(H / 3, 0, 1))[..., None]
    c.albedo *= (.8 + .35 * grime(S, S, 621, base=7))[..., None]
    alpha = blur(mask.astype(np.float32), .6)
    rgb = np.clip(c.albedo, 0, 1)
    os.makedirs(PNG, exist_ok=True)
    write_dds((np.dstack([rgb, alpha]) * 255 + .5).astype(np.uint8), 'shab_wiremesh_diff')
    nx, ny = c.normal(1.0)
    n = np.empty((S, S, 4), np.float32)
    n[..., 0] = 1; n[..., 1] = ny * .5 + .5; n[..., 2] = n[..., 1]; n[..., 3] = nx * .5 + .5
    write_dds((n * 255 + .5).astype(np.uint8), 'shab_wiremesh_nrm')
    print('shab_wiremesh written')


if __name__ == '__main__':
    which = sys.argv[1:] or ['surface', 'rover', 'isru', 'wire']
    if 'surface' in which:
        surface()
    if 'rover' in which:
        rover_sheet()
    if 'isru' in which:
        isru_sheet()
    if 'wire' in which:
        wiremesh()
