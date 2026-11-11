"""SHAB interior: two floors inside the PCM. Everything is authored in the part frame used by
build_pcm.py; the 'model' empty then carries the fixed rotation from part space to KSP's
internal space, measured off HabTech's Destiny: internal Unity = -(part Blender coords).
Writes internals/shab_PCM_IVA.mu, internals/shab_PCM_IVA_shell.mu (FreeIva walk collider) and
internals/shab_PCM_IVA.cfg (seats, cameras and every PROP are generated here, so transforms
and config can't drift apart)."""
import bpy, sys, os, math, re, glob
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
import layout as L
from iva_layout import *

out = sys.argv[sys.argv.index('--') + 1]
ROOTDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IDIR = os.path.join(ROOTDIR, 'internals')
enable_addon(); clean_scene()
np.random.seed(11)
Z = {k: Zone(*v, atlas=ATLAS, ppm=400) for k, v in ZONES.items()}

P = Part('shab_PCM_IVA')
M_iva = P.material('shab_iva', spec=(.25, .25, .25), shininess=.3)
M_glass = P.material('shab_ivaglass', shader='KSP/Alpha/Translucent', name='ivaglass')
R_IVA = Matrix(((-1, 0, 0), (0, 0, -1), (0, -1, 0)))     # part Blender -> internal Blender


def pos(az, r, z):
    a = math.radians(az)
    return Vector((r * math.sin(a), -r * math.cos(a), z))


def inw(az, z, r):
    """Frame on the wall looking at the axis: +Z toward the axis, +Y up, +X viewer's right."""
    return on_cyl(az, z, r) @ Ry(180)


def plane_frame(c, zaxis, up=(0, 0, 1)):
    z_ = Vector(zaxis).normalized(); up = Vector(up)
    x_ = up.cross(z_).normalized(); y_ = z_.cross(x_)
    m = Matrix((x_, y_, z_)).transposed().to_4x4(); m.translation = Vector(c)
    return m


# ------------------------------------------------------------------ prop list -> cfg
PROPS = []


def prop_axes(name, origin, uy, uz, scale=1.0):
    """Place a prop by where its Unity +Y and +Z axes point, in part space."""
    uy = Vector(uy).normalized(); uz = (Vector(uz) - Vector(uz).dot(uy) * uy).normalized()
    # Blender local axes: bx = Unity x, by = Unity z, bz = Unity y
    bz, by = uy, uz
    bx = by.cross(bz)
    M3 = Matrix((bx, by, bz)).transposed()
    q = (R_IVA @ M3).to_quaternion()
    p = Vector(origin)
    sc = (scale, scale, scale) if not isinstance(scale, tuple) else scale
    PROPS.append((name, (-p.x, -p.y, -p.z), (-q.x, -q.z, -q.y, q.w), sc))


def on_panel(F, name, x=0, y=0, z=0, scale=1.0, roll=0.0):
    """Instrument-style prop on a panel frame: Unity +Y is the face normal, Unity -Z is 'up'
    on the dial (checked against Orion's and the stock lander can's IVAs)."""
    M = F @ T(x, y, z) @ Rz(roll)
    prop_axes(name, M.translation, M.to_3x3().col[2], -M.to_3x3().col[1], scale)


# ------------------------------------------------------------------ wall with rectangular holes
def wall(r, z0, z1, holes, zone, tile=60.0, daz=7.5):
    """Inward-facing cylinder. holes: list of (az_c, half_az, z_lo, z_hi). UV tile per bay."""
    azs = set(float(a) for a in np.arange(-180, 180.01, daz))
    zs = {z0, z1}
    for ac, ha, zl, zh in holes:
        azs |= {ac - ha, ac + ha}; zs |= {zl, zh}
    azs = sorted(azs); zs = sorted(zs)
    g = Geo(); idx = {}
    n = len(azs)

    def vid(i, j):
        k = (i % (n - 1), j)
        if k not in idx:
            idx[k] = len(g.v); g.v.append(tuple(pos(azs[i], r, zs[j])))
        return idx[k]
    for i in range(n - 1):
        a0, a1 = azs[i], azs[i + 1]
        ac = (a0 + a1) / 2
        for j in range(len(zs) - 1):
            zc = (zs[j] + zs[j + 1]) / 2
            if any(abs(ac - h[0]) < h[1] and h[2] < zc < h[3] for h in holes):
                continue
            tile0 = math.floor((ac + 30) / tile) * tile - 30
            s1 = 1 - (a1 - tile0) / tile; s0 = 1 - (a0 - tile0) / tile   # viewer's right = -az
            t0 = (zs[j] - z0) / (z1 - z0); t1 = (zs[j + 1] - z0) / (z1 - z0)
            g.face([vid(i + 1, j), vid(i, j), vid(i, j + 1), vid(i + 1, j + 1)],
                   [zone.uv(s1, t0), zone.uv(s0, t0), zone.uv(s0, t1), zone.uv(s1, t1)])
    return g


def oriented(g, pts, uvs, toward):
    """Add a quad whose normal points toward the given point."""
    i0 = len(g.v)
    g.v.extend(tuple(p) for p in pts)
    idx = list(range(i0, i0 + len(pts)))
    a, b, c_ = Vector(pts[0]), Vector(pts[1]), Vector(pts[2])
    n = (b - a).cross(c_ - a)
    cen = sum((Vector(p) for p in pts), Vector()) / len(pts)
    if n.dot(Vector(toward) - cen) < 0:
        idx = idx[::-1]; uvs = list(uvs)[::-1]
    g.face(idx, uvs)


def reveal(az, zc, ha_in, hh_in, hw_out, hh_out, r_in, r_out, zone, n=6):
    """Lining between a hole cut in the cylindrical wall and a flat opening further out."""
    g = Geo()
    cen = pos(az, r_in * .5, zc)
    F = inw(az, zc, r_out)
    azs = [az + ha_in - 2 * ha_in * i / n for i in range(n + 1)]   # viewer left to right
    xs = [-hw_out + 2 * hw_out * i / n for i in range(n + 1)]
    for side in (1, -1):                                           # top, bottom
        zi = zc + side * hh_in; yo = side * hh_out
        for i in range(n):
            pts = [pos(azs[i], r_in, zi), pos(azs[i + 1], r_in, zi), F @ Vector((xs[i + 1], yo, 0)), F @ Vector((xs[i], yo, 0))]
            oriented(g, pts, [zone.uv(0, 0), zone.uv(1, 0), zone.uv(1, 1), zone.uv(0, 1)], cen)
    for side, a_ in ((-1, azs[0]), (1, azs[-1])):                  # left, right
        pts = [pos(a_, r_in, zc - hh_in), pos(a_, r_in, zc + hh_in), F @ Vector((side * hw_out, hh_out, 0)), F @ Vector((side * hw_out, -hh_out, 0))]
        oriented(g, pts, [zone.uv(0, 0), zone.uv(1, 0), zone.uv(1, 1), zone.uv(0, 1)], cen)
    return g


def bag_wall(az0, az1, z0, z1, nx, ny, r=R_WALL, bulge=.05, standoff=.004, res=5):
    """Strapped soft water bags against the hull wall: pillows, inward-facing."""
    g = Geo(); zn = Z['water']
    nu, nv = nx * res, ny * res
    rr = np.random.RandomState(int(abs(az0) * 7 + z0 * 100) & 0xffff)
    bag_bulge = rr.uniform(.8, 1.15, (nx, ny))
    for i in range(nu + 1):
        for j in range(nv + 1):
            u, v = i / nu, j / nv
            fu = (u * nx) % 1; fv = (v * ny) % 1
            bi = min(int(u * nx), nx - 1); bj = min(int(v * ny), ny - 1)
            pil = (math.sin(math.pi * fu) * math.sin(math.pi * fv)) ** .45
            rad = r - standoff - bulge * bag_bulge[bi, bj] * pil
            g.v.append(tuple(pos(az0 + (az1 - az0) * u, rad, z0 + (z1 - z0) * v)))
    W = nv + 1
    for i in range(nu):
        for j in range(nv):
            bi = i // res; bj = j // res
            flip = (bi + bj) % 2
            f0 = (i % res) / res; f1 = ((i % res) + 1) / res
            g0 = (j % res) / res; g1 = ((j % res) + 1) / res
            s0 = (flip + (1 - f0)) / 2; s1 = (flip + (1 - f1)) / 2
            a, b, c_, d = i * W + j, (i + 1) * W + j, (i + 1) * W + j + 1, i * W + j + 1
            g.face([b, a, d, c_], [zn.uv(s1, g0), zn.uv(s0, g0), zn.uv(s0, g1), zn.uv(s1, g1)])
    return g


def plate(F, w, h, zone, nx=1, ny=1, zoff=0.0):
    g = Geo(); g.add(quad_patch(w, h, zone, z=zoff, nx=nx, ny=ny), F); return g


def rack(az, zc, w, h, zone, r_front=None, depth=.12, side='frame'):
    """Flat equipment rack against the curved wall, front facing the axis."""
    rb = math.sqrt(R_WALL ** 2 - (w / 2) ** 2) - .003
    rf = r_front or (rb - depth)
    g = Geo()
    F = inw(az, zc, rf)
    g.add(quad_patch(w, h, Z[zone]), F)
    d = rb - rf
    g.add(box(w, h, d, zone=Z[side], bevel=.004, center=(0, 0, -d / 2 - .001)), F)
    return g, F


def disc_with_hole(R, z, hc, hr, zone, up=True, seg=48, rings=4):
    """Disc at height z, optional circular hole. Planar UV over 1.64 m. Faces +Z if up."""
    g = Geo()
    n = seg
    for i in range(n + 1):
        a = TAU * i / n
        d = Vector((math.cos(a), math.sin(a)))
        if hr:
            c_ = Vector(hc)
            # ray from the hole centre to the outer circle
            b_ = c_.dot(d); t_ = -b_ + math.sqrt(b_ * b_ - (c_.dot(c_) - R * R))
            for k in range(rings + 1):
                rr = hr + (t_ - hr) * k / rings
                p = c_ + d * rr
                g.v.append((p.x, p.y, z))
        else:
            for k in range(rings + 1):
                rr = R * (k + .001) / rings
                g.v.append((d.x * rr, d.y * rr, z))

    def uv(i_):
        x_, y_, _ = g.v[i_]
        return zone.uv(.5 + x_ / 1.64, .5 + y_ / 1.64)
    W = rings + 1
    for i in range(n):
        for k in range(rings):
            a, b, c_, d = i * W + k, (i + 1) * W + k, (i + 1) * W + k + 1, i * W + k + 1
            q = [d, c_, b, a] if up else [a, b, c_, d]    # i runs CCW seen from +Z, k runs outward
            g.face(q, [uv(v) for v in q])
    return g


def rail_tube(path, r=.008, zone='rail', sides=6):
    return tube(path, r, sides, zone=Z[zone])


# ================================================================== shell
sh = Geo()
wh = math.degrees(math.asin((L.WIN_W + .06) / 2 / R_WALL))
wz = (L.WIN_H + .06) / 2
dh = math.degrees(math.asin((L.HATCH_W + .04) / 2 / R_WALL))
dz = (L.HATCH_H + .04) / 2
sh.add(wall(R_WALL, Z_FLOOR, Z_DECK_BOT, [(L.WIN_AZ, wh, L.WIN_Z[0] - wz, L.WIN_Z[0] + wz), (L.HATCH_AZ, dh, L.HATCH_Z - dz, L.HATCH_Z + dz)], Z['wall']))
sh.add(wall(R_WALL, Z_DECK_TOP, Z_CEIL, [(L.WIN_AZ, wh, L.WIN_Z[1] - wz, L.WIN_Z[1] + wz)], Z['wall']))
for zw in L.WIN_Z:
    sh.add(reveal(L.WIN_AZ, zw, wh, wz, L.WIN_W / 2 + .005, L.WIN_H / 2 + .005, R_WALL, .955, Z['frame']))
sh.add(reveal(L.HATCH_AZ, L.HATCH_Z, dh, dz, L.HATCH_W / 2, L.HATCH_H / 2, R_WALL, .925, Z['frame']))
# crown liner and upper tunnel: stays inside the outer crown (see build_pcm.py profile)
crown = lathe([(R_WALL, Z_CEIL), (.81, 1.18), (.76, 1.30), (.66, 1.44), (.53, 1.54), (.46, 1.58), (.46, Z_HATCH_TOP)], 48, zone=Z['crown'], flip=True)
crown.add(lathe([(.475, Z_HATCH_TOP), (0.0, Z_HATCH_TOP)], 32, zone=Z['frame'], flip=True))
deck_top = disc_with_hole(R_WALL + .015, Z_DECK_TOP, HATCH_C, HATCH_R, Z['deck'], up=True)
deck_bot = disc_with_hole(R_WALL + .015, Z_DECK_BOT, HATCH_C, HATCH_R, Z['ceiling'], up=False)
floor_low = disc_with_hole(R_WALL + .015, Z_FLOOR, None, 0, Z['deck'], up=True, rings=3)
# hatch coaming: lining of the hole, then a raised lip on the upper floor
hc3 = Vector((HATCH_C[0], HATCH_C[1], 0))
coam = lathe([(HATCH_R, Z_DECK_BOT - .02), (HATCH_R, Z_DECK_TOP + .035), (HATCH_R + .018, Z_DECK_TOP + .04), (HATCH_R + .03, Z_DECK_TOP + .005)], 32, zone=Z['yellow'], flip=True)
tmp = Geo(); tmp.add(lathe([(HATCH_R + .03, Z_DECK_BOT - .005), (HATCH_R + .012, Z_DECK_BOT - .025), (HATCH_R, Z_DECK_BOT - .02)], 32, zone=Z['yellow'], flip=True))
coam.add(tmp)
coam_g = Geo(); coam_g.add(coam, T(hc3.x, hc3.y, 0))

# bulkhead with door opening: three plates around the hole, on both faces
bx_ = math.sqrt(R_WALL ** 2 - BULK_Y ** 2)
bulk = Geo()
zn = Z['bulkhead']
zl, zh = Z_FLOOR, Z_DECK_BOT
dzl, dzh = DOOR_Z - DOOR_H / 2, DOOR_Z + DOOR_H / 2
dx = DOOR_W / 2
xbreaks = [-bx_, -dx, dx, bx_]; zbreaks = [zl, dzl, dzh, zh]
for side, yb, normal in ((1, BULK_Y + BULK_T / 2, (0, 1, 0)), (-1, BULK_Y - BULK_T / 2, (0, -1, 0))):
    for i in range(3):
        for j in range(3):
            if i == 1 and j == 1:
                continue
            x0, x1 = xbreaks[i], xbreaks[i + 1]; z0_, z1_ = zbreaks[j], zbreaks[j + 1]
            pts = [(x0, yb, z0_), (x1, yb, z0_), (x1, yb, z1_), (x0, yb, z1_)]
            # viewer's right is -x from the cabin, +x from the vestibule
            uvs = []
            for p in pts:
                s = .5 + (p[0] / (2 * bx_)) * (-side)
                uvs.append(zn.uv(s, (p[2] - zl) / (zh - zl)))
            oriented(bulk, pts, uvs, (0, yb + side, z0_))
# door jamb
for pts, tw in (([(-dx, BULK_Y - BULK_T / 2, dzl), (-dx, BULK_Y + BULK_T / 2, dzl), (-dx, BULK_Y + BULK_T / 2, dzh), (-dx, BULK_Y - BULK_T / 2, dzh)], (0, BULK_Y, DOOR_Z)),
                ([(dx, BULK_Y - BULK_T / 2, dzl), (dx, BULK_Y + BULK_T / 2, dzl), (dx, BULK_Y + BULK_T / 2, dzh), (dx, BULK_Y - BULK_T / 2, dzh)], (0, BULK_Y, DOOR_Z)),
                ([(-dx, BULK_Y - BULK_T / 2, dzh), (dx, BULK_Y - BULK_T / 2, dzh), (dx, BULK_Y + BULK_T / 2, dzh), (-dx, BULK_Y + BULK_T / 2, dzh)], (0, BULK_Y, DOOR_Z)),
                ([(-dx, BULK_Y - BULK_T / 2, dzl), (dx, BULK_Y - BULK_T / 2, dzl), (dx, BULK_Y + BULK_T / 2, dzl), (-dx, BULK_Y + BULK_T / 2, dzl)], (0, BULK_Y, DOOR_Z))):
    z_ = Z['frame']
    oriented(bulk, pts, [z_.uv(0, 0), z_.uv(1, 0), z_.uv(1, 1), z_.uv(0, 1)], tw)

# ================================================================== furnishing geometry
fur = Geo()
soft = Geo()

# ---- water band round the top of the upper floor, and the wall under the window
soft.add(bag_wall(-180, 180, .90, Z_CEIL + .03, 18, 1, bulge=.055))
soft.add(bag_wall(44, 76, Z_DECK_TOP + .01, .50, 2, 2, bulge=.06))
soft.add(bag_wall(76, 92, -.05, .86, 1, 2, bulge=.06))

# ---- flight station at az -90: console, MFD board, leg-space cabinet
CON_W, CON_H = .78, .48
CON_Z = .36
g, F_con = rack(-90, CON_Z, CON_W, CON_H, 'console', r_front=.70)
fur.add(g)
g, F_mfd = rack(-90, CON_Z + CON_H / 2 + .14, CON_W, .28, 'dark', r_front=.71)
fur.add(g)
g, F_low = rack(-90, (Z_DECK_TOP + CON_Z - CON_H / 2) / 2, CON_W, CON_Z - CON_H / 2 - Z_DECK_TOP, 'lockers', r_front=.765, depth=.02)
fur.add(g)
# under-console knee brace
fur.add(rail_tube([tuple(F_low @ Vector((-.3, -.02, .0))), tuple(F_low @ Vector((-.3, -.02, .10))), tuple(F_low @ Vector((.3, -.02, .10))), tuple(F_low @ Vector((.3, -.02, .0)))], .007))


def CF(fx, fy):
    return (fx - .5) * CON_W, (.5 - fy) * CON_H


LIFT = {'AltimeterThreeHands': .014, 'IndicatorPanel': .016}
for nm, fx, fy, sc in (('NavBall', .50, .34, 2.1), ('AltimeterThreeHands', .10, .25, 1.5), ('VSI', .21, .25, 1.5),
                       ('IndicatorPanel', .165, .46, 1.3), ('AtmosphereDepth', .80, .25, 1.4), ('RadarAltimeter', .89, .25, 1.5),
                       ('AxisIndicatorPitch', .77, .46, 1.4), ('AxisIndicatorRoll', .84, .46, 1.4), ('AxisIndicatorYaw', .91, .46, 1.4),
                       ('genericClusterSwitches01', .165, .80, 1.3), ('ledPanelSpeed', .44, .73, 1.4), ('genericClusterButtons', .44, .83, 1.3),
                       ('genericClusterKnobs', .44, .90, 1.2), ('genericClusterSwitches03', .62, .80, 1.2),
                       ('ButtonSquare', .78, .82, 2.6), ('throttle', .895, .82, .75)):
    x_, y_ = CF(fx, fy)
    on_panel(F_con, nm, x_, y_, .002 + LIFT.get(nm, 0), sc)
for i, nm in enumerate(('htProps_MFD_orion1', 'htProps_MFD_orion2', 'htProps_MFD_orion3')):
    on_panel(F_mfd, nm, -.25 + i * .25, 0, .002, .95)

# ---- four sleep/stowage cubbies, az -45..25, two up two down
CUB_R = .60
CUB_W = .44
for col, az_c in enumerate((-27.0, 7.5)):
    for row, (z0_, z1_) in enumerate(((Z_DECK_TOP + .02, .32), (.34, .885))):
        zc = (z0_ + z1_) / 2; hh = (z1_ - z0_)
        F = inw(az_c, zc, CUB_R)
        rb = math.sqrt(R_WALL ** 2 - (CUB_W / 2) ** 2) - .004
        d = rb - CUB_R
        # back wall, sides, top, bottom seen from inside the cubby
        fur.add(quad_patch(CUB_W, hh, Z['sleep']), F @ T(0, 0, -d))
        cen = F @ Vector((0, 0, .05))
        for (xa, ya, xb, yb) in ((-CUB_W / 2, -hh / 2, -CUB_W / 2, hh / 2), (CUB_W / 2, -hh / 2, CUB_W / 2, hh / 2), (-CUB_W / 2, hh / 2, CUB_W / 2, hh / 2), (-CUB_W / 2, -hh / 2, CUB_W / 2, -hh / 2)):
            pts = [F @ Vector((xa, ya, 0)), F @ Vector((xb, yb, 0)), F @ Vector((xb, yb, -d)), F @ Vector((xa, ya, -d))]
            z_ = Z['tan']
            oriented(fur, pts, [z_.uv(0, 0), z_.uv(1, 0), z_.uv(1, 1), z_.uv(0, 1)], cen)
        # frame round the opening
        fur.add(rounded_rect_ring(CUB_W + .06, hh + .05, .012, .034, .012, seg=2, zone=Z['frame'], base=0), F)
        # sleeping bag strapped upright to the back wall, plus a pillow pad at the top
        bag = tube([(0.02, -hh * .36, -d + .05), (0.02, hh * .18, -d + .055)], .085, 10, zone=Z['pad'], r_fn=lambda t: .075 + .012 * math.sin(math.pi * t))
        fur.add(bag, F)
        fur.add(box(.17, .09, .05, zone=Z['softwhite'], bevel=.018, center=(.02, hh * .30, -d + .04)), F)
        # curtain gathered to one side
        cg = Geo(); nw = 14; cw = .11
        cx0 = -CUB_W / 2 + .005 if col == 0 else CUB_W / 2 - cw - .005
        for i in range(nw + 1):
            for j in (0, 1):
                xx = cx0 + cw * i / nw
                zz = .022 + .012 * math.sin(i * 1.9)
                cg.v.append((xx, -hh / 2 + .01 + (hh - .02) * j, zz - .03))
        zc_ = Z['curtain']
        for i in range(nw):
            a = i * 2
            cg.face([a, a + 2, a + 3, a + 1], [zc_.uv(i / nw, 0), zc_.uv((i + 1) / nw, 0), zc_.uv((i + 1) / nw, 1), zc_.uv(i / nw, 1)])
        soft.add(cg, F)
        # name plate
        fur.add(box(.09, .022, .004, zone=Z['white'], center=(CUB_W / 2 - .07, hh / 2 + .004, .012)), F)
        # personal effects
        on_panel(F, ('htProps_cargoBag_small_blue', 'htProps_cargoBag_small_white', 'htProps_cargoBag_small_red', 'htProps_cargoBag_small_blue')[col * 2 + row], -.11 if col else .13, -hh * .30, -d + .04, .6)
# a toy on the top cubby's shelf, because a four-year trip is long
F_toy = inw(7.5, .40, CUB_R)
prop_axes('htProps_dinoToy_styracosaurus', F_toy @ Vector((-.05, .02, -.08)), (0, 0, 1), F_toy.to_3x3().col[0], .13)
# handrail between the cubby columns
# ---- exercise device at az 40: bike on a fold-down base, plus resistance straps on the wall
BF = T(*pos(38, .50, Z_DECK_TOP)) @ Rz(38 + 90)
bike = Geo()
bike.add(box(.46, .16, .012, zone=Z['dark'], bevel=.003, center=(0, 0, .006)))
bike.add(tube([(-.16, 0, .01), (-.09, 0, .25), (.13, 0, .40)], .012, 6, zone=Z['frame']))     # seat post to bars
bike.add(tube([(.16, 0, .01), (.13, 0, .40)], .012, 6, zone=Z['frame']))
bike.add(tube([(-.09, 0, .25), (-.09, 0, .34)], .011, 6, zone=Z['rail']))
bike.add(box(.11, .075, .026, zone=Z['rubber'], bevel=.008, center=(-.09, 0, .352)))           # saddle
bike.add(tube([(.13, -.13, .425), (.13, -.06, .40), (.13, .06, .40), (.13, .13, .425)], .009, 6, zone=Z['rubber']))
bike.add(Geo().add(cyl(.09, .032, 20, zone=Z['dark'], bevel=.005), T(.02, 0, .13) @ Rx(90)))    # flywheel
bike.add(Geo().add(cyl(.03, .05, 12, zone=Z['steel'], bevel=.004), T(.02, 0, .13) @ Rx(90)))
for s_ in (-1, 1):
    bike.add(tube([(.02, s_ * .03, .13), (.02 + s_ * .06, s_ * .04, .13 - s_ * .05), (.02 + s_ * .06, s_ * .075, .13 - s_ * .05)], .006, 5, zone=Z['steel']))
    bike.add(box(.055, .04, .012, zone=Z['rubber'], center=(.02 + s_ * .06, s_ * .09, .13 - s_ * .05)))
bike.add(plate(T(.14, 0, .445) @ Rx(0) @ Ry(55), .10, .06, Z['bike']))
fur.add(bike, BF)
# treadmill harness straps on the wall behind it
for a_ in (28, 42):
    p0 = pos(a_, R_WALL - .01, .45); p1 = pos(a_ + 4, .70, Z_DECK_TOP + .34)
    soft.add(tube([tuple(p0), tuple((p0 + p1) / 2 + Vector((0, 0, -.03))), tuple(p1)], .007, 5, zone=Z['hose'], caps=False))
    fur.add(Geo().add(box(.04, .06, .012, zone=Z['frame'], bevel=.002), inw(a_, .45, R_WALL - .006)))

# ---- window frames, glass and the camera on its hook
glass = Geo()
for i, zw in enumerate(L.WIN_Z):
    F = inw(L.WIN_AZ, zw, R_WALL - .012)
    fur.add(rounded_rect_ring(L.WIN_W + .14, L.WIN_H + .14, .05, .055, .022, seg=4, zone=Z['frame'], base=-.016), F)
    # sill
    fur.add(box(L.WIN_W + .12, .012, .05, zone=Z['frame'], bevel=.003, center=(0, -(L.WIN_H / 2 + .05), .018)), F)
    glass.add(quad_patch(L.WIN_W + .04, L.WIN_H + .04, Zone(0, 0, 64, 64, atlas=64), z=-.05), F)
# handrails either side of the upper window (Handrail01 = short: long axis Unity z, base toward +y)
F_wu = inw(L.WIN_AZ, L.WIN_Z[1], R_WALL)


def handrail(F, x, y, nm='htProps_Handrail01', vertical=True):
    """HabTech rail: Unity +Y points at the wall, the rail runs along Unity Z."""
    M = F @ T(x, y, 0)
    prop_axes(nm, M.translation, -M.to_3x3().col[2], M.to_3x3().col[1] if vertical else M.to_3x3().col[0])


handrail(F_wu, -.24, 0); handrail(F_wu, .24, 0)
prop_axes('htProps_CameraDSLR', (F_wu @ T(.0, -L.WIN_H / 2 - .035, .05)).translation, (0, 0, 1), F_wu.to_3x3().col[2], .7)

# ---- galley at az 105: HabTech cabinets, food prep, fold-away table
GAL_W = .528
rb = math.sqrt(R_WALL ** 2 - (GAL_W / 2) ** 2) - .004
G_r = rb - .05
for zc_, kind in ((Z_DECK_TOP + .264 + .005, 'low'), (Z_DECK_TOP + .264 * 3 + .012, 'high')):
    F = inw(112, zc_, G_r)
    on_panel(F, 'htProps_cabinet3x3', 0, 0, 0, 1.0)
    if kind == 'low':
        for dx_ in (-.176, 0, .176):
            on_panel(F, 'htProps_galleyCupboard1x1', dx_, -.176, 0)
        on_panel(F, 'htProps_galleyCupboard2x1', -.176, .088, 0)
        on_panel(F, 'htProps_galleyFoodPrep1x2', .088 - .088, .088, 0, 1.0)
    else:
        for dx_ in (-.176, 0, .176):
            on_panel(F, 'htProps_galleyCupboard1x1', dx_, .176, 0)
        on_panel(F, 'htProps_cabinetMonitor', .176, -.088, 0)
        on_panel(F, 'htProps_cabinetMonitorScreen_scripts', .176, -.088, 0)
        on_panel(F, 'htProps_cabinetPanel_01_2x2', -.08, -.088, 0)
# fold-away table: hinged to the galley front, extends toward the axis
F_tab = inw(112, .19, G_r - .05)
prop_axes('htProps_tableGalley', F_tab.translation, (0, 0, 1), F_tab.to_3x3().col[0])
# a stool that hasn't been stowed, and a few bags on the wall beside the ladder
F_stool = pos(118, .36, Z_DECK_TOP + .05)
prop_axes('htProps_seat_stool', F_stool, (0, 0, 1), (1, 0, 0))
F_bags = inw(145, .25, R_WALL - .05)
on_panel(F_bags, 'htProps_cargoBag_small_firstAid', 0, .18, 0, 1.0)
on_panel(F_bags, 'htProps_fireExtinguisher', 0, -.18, .01, 1.0)
soft.add(bag_wall(133, 158, -.20, .88, 2, 3, bulge=.05))

# ---- science: rack over a freezer cabinet, az 210, with a fold-down bench
g, F_sci = rack(210, .56, .528, .56, 'science', r_front=.67, depth=.10)
fur.add(g)
F = inw(210, Z_DECK_TOP + .264 + .005, G_r)
on_panel(F, 'htProps_cabinet3x3', 0, 0, 0, 1.0)
on_panel(F, 'htProps_scienceFreezer', -.176, .176, 0)
on_panel(F, 'htProps_scienceFreezer', 0, .176, 0)
on_panel(F, 'htProps_scienceFreezer', .176, .176, 0)
on_panel(F, 'htProps_cabinetPanel_01_2x2', 0, -.088, 0)
F_bn = inw(210, .275, .67)
prop_axes('htProps_workBench', F_bn.translation, (0, 0, 1), F_bn.to_3x3().col[0], .8)
for k_, (x_, nm) in enumerate(((-.12, 'htProps_labFlaskGreen'), (-.04, 'htProps_labFlaskEmpty'), (.0, 'htProps_labFlaskGreen'))):
    prop_axes(nm, (F_bn @ T(x_, 0, .08 + k_ * .02)).translation, (0, 0, 1), (1, 0, 0))
prop_axes('htProps_sampleCase', (F_bn @ T(.13, .04, .10)).translation, (0, 0, 1), F_bn.to_3x3().col[0], .6)

# ---- ladder on the wall through the deck hatch
LAD_W = .20
LAD_R = .745
rail0 = Z_FLOOR + .01
rail1 = .42
Fl = inw(LADDER_AZ, 0, LAD_R)
for s_ in (-1, 1):
    a0 = Fl @ Vector((s_ * LAD_W / 2, rail0, 0)); a1 = Fl @ Vector((s_ * LAD_W / 2, rail1, 0))
    fur.add(tube([tuple(a0), tuple(a1)], .011, 6, zone=Z['yellow']))
    fur.add(tube([tuple(a1), tuple(Fl @ Vector((s_ * LAD_W / 2, rail1 + .05, -.05)))], .011, 6, zone=Z['yellow']))
    for z_ in (rail0 + .25, -.9, -.12, .2):
        p = Fl @ Vector((s_ * LAD_W / 2, z_, 0))
        q = Fl @ Vector((s_ * LAD_W / 2, z_, -(R_WALL - LAD_R - .01)))
        fur.add(tube([tuple(p), tuple(q)], .007, 5, zone=Z['frame']))
n_r = int((rail1 - rail0) / .14)
for i in range(n_r):
    y_ = rail0 + .10 + i * .14
    fur.add(tube([tuple(Fl @ Vector((-LAD_W / 2, y_, 0))), tuple(Fl @ Vector((LAD_W / 2, y_, 0)))], .0075, 6, zone=Z['yellow']))
# guard rail round the open hatch on the upper floor (open on the ladder side and the access side)
hx0, hy0 = HATCH_C
pts = []
for a_ in np.linspace(math.radians(-150), math.radians(40), 12):
    pts.append((hx0 + (HATCH_R + .045) * math.cos(a_), hy0 + (HATCH_R + .045) * math.sin(a_), Z_DECK_TOP + .34))
fur.add(rail_tube(pts, .009, 'yellow'))
for k_ in (0, 5, 11):
    p = pts[k_]
    fur.add(rail_tube([p, (p[0], p[1], Z_DECK_TOP + .01)], .008, 'yellow'))

# ---- upper floor: crown rails and tunnel ladder to the CBM hatch
for a_ in (-120, 0, 120):
    Fc = plane_frame(pos(a_, .60, 1.45), (math.sin(math.radians(a_)) * -.6, math.cos(math.radians(a_)) * .6, -.8), up=(0, 0, 1))
    handrail(Fc, 0, 0, 'htProps_Handrail01', vertical=False)
tun = []
for z_ in np.arange(1.22, 1.70, .1):
    r_ = np.interp(z_, [1.18, 1.30, 1.44, 1.54, 1.58, 1.72], [.81, .76, .66, .53, .46, .46]) - .025
    fur.add(tube([tuple(pos(LADDER_AZ - 11, r_, float(z_))), tuple(pos(LADDER_AZ + 11, r_, float(z_)))], .0065, 5, zone=Z['yellow']))
F_top = plane_frame((0, 0, Z_HATCH_TOP - .004), (0, 0, -1), up=(0, 1, 0))
prop_axes('htProps_HatchCBM', F_top.translation, (0, 0, -1), pos(LADDER_AZ, 1, 0), 1.25)

# ================================================================== lower floor
# ---- vestibule floor grate, door sill step
vest = Geo()
yb = BULK_Y - BULK_T / 2
TILE = .11
z_ = Z['grate']
for i in range(-8, 8):
    for j in range(-8, 8):
        x0, x1 = i * TILE, (i + 1) * TILE
        y1 = yb - j * TILE; y0 = y1 - TILE
        if y1 > yb + 1e-6 or max(x0 ** 2, x1 ** 2) + y0 ** 2 > (R_WALL - .004) ** 2:
            continue
        i0 = len(vest.v)
        vest.v.extend([(x0, y0, Z_FLOOR + .006), (x1, y0, Z_FLOOR + .006), (x1, y1, Z_FLOOR + .006), (x0, y1, Z_FLOOR + .006)])
        vest.face([i0, i0 + 1, i0 + 2, i0 + 3], [z_.uv(0, 0), z_.uv(1, 0), z_.uv(1, 1), z_.uv(0, 1)])
fur.add(vest)
fur.add(box(L.HATCH_W + .06, .16, L.HATCH_Z - L.HATCH_H / 2 - Z_FLOOR, zone=Z['grate'], bevel=.006, center=(0, -.74, (Z_FLOOR + L.HATCH_Z - L.HATCH_H / 2) / 2)))

# ---- EVA door, cabin side
F_door = inw(L.HATCH_AZ, L.HATCH_Z, .925)
fur.add(quad_patch(L.HATCH_W + .02, L.HATCH_H + .02, Z['door']), F_door)
fur.add(rounded_rect_ring(L.HATCH_W + .05, L.HATCH_H + .05, .06, .04, .05, seg=4, zone=Z['frame'], base=-.002), F_door)
# handwheel, spokes and hub
wheel = Geo()
wheel.add(tube([(.11 * math.cos(a_), .11 * math.sin(a_), .05) for a_ in np.linspace(0, TAU, 21)[:-1]], .012, 8, zone=Z['red'], closed=True, caps=False))
wheel.add(cyl(.03, .05, 12, zone=Z['steel'], bevel=.004, center_z=False))
for a_ in (0, 120, 240):
    r_ = math.radians(a_)
    wheel.add(tube([(0, 0, .04), (.11 * math.cos(r_), .11 * math.sin(r_), .05)], .007, 5, zone=Z['steel']))
fur.add(wheel, F_door @ T(0, -.10, 0))
# grab bars and a pressure gauge
for s_ in (-1, 1):
    fur.add(rail_tube([tuple(F_door @ Vector((s_ * .235, y_, z_))) for y_, z_ in ((-.25, .002), (-.25, .05), (.25, .05), (.25, .002))], .009, 'yellow'))
fur.add(box(.08, .08, .018, zone=Z['dark'], bevel=.003, center=(.14, .12, .01)), F_door)
fur.add(cyl(.028, .01, 16, zone=Z['white'], center_z=False), F_door @ T(.14, .12, .019))
fur.add(Geo().add(tube([(0, 0, 0), (.0, 0, .05)], .018, 8, zone=Z['steel']), F_door @ T(-.14, .12, .002)))   # vent valve

# ---- suits at az +-46, on wall stands; kerbal-proportioned
def suit():
    g = Geo()
    zs_ = Z['suit']
    # legs
    for s_ in (-1, 1):
        g.add(tube([(s_ * .055, 0, .06), (s_ * .06, .005, .22), (s_ * .06, 0, .40)], .05, 8, zone=zs_, r_fn=lambda t: .044 + .018 * t))
        g.add(box(.08, .14, .06, zone=Z['glove'], bevel=.018, center=(s_ * .06, -.02, .03)))    # boots
    # torso (hard upper) and a soft waist
    torso = lathe([(0, .38), (.10, .38), (.115, .44), (.135, .56), (.145, .66), (.115, .74), (.05, .76), (0, .76)], 14, zone=zs_)
    g.add(torso, S(1, .78, 1))
    # arms relaxed at the sides
    for s_ in (-1, 1):
        g.add(tube([(s_ * .15, 0, .69), (s_ * .19, -.01, .55), (s_ * .19, -.04, .42)], .04, 8, zone=zs_, r_fn=lambda t: .044 - .01 * t))
        g.add(box(.05, .06, .075, zone=Z['glove'], bevel=.018, center=(s_ * .19, -.045, .375)))
        g.add(cyl(.05, .03, 10, zone=Z['frame'], bevel=.004), T(s_ * .165, 0, .685) @ Ry(s_ * 60))
    # neck ring and helmet
    g.add(cyl(.082, .022, 16, zone=Z['frame'], bevel=.004), T(0, 0, .775))
    hel = []
    for k_ in range(13):
        t_ = math.pi * k_ / 12
        hel.append((.13 * math.sin(t_) + 1e-4, .90 - .13 * math.cos(t_)))
    g.add(lathe(hel, 18, zone=Z['softwhite']))
    # gold visor patch
    vis = Geo()
    nv_ = 8
    for i in range(nv_ + 1):
        for j in range(nv_ + 1):
            th = math.radians(-58 + 116 * i / nv_); ph = math.radians(-28 + 62 * j / nv_)
            r_ = .1345
            vis.v.append((r_ * math.sin(th) * math.cos(ph), -r_ * math.cos(th) * math.cos(ph), .90 + r_ * math.sin(ph)))
    for i in range(nv_):
        for j in range(nv_):
            a = i * (nv_ + 1) + j
            vis.face([a, a + nv_ + 1, a + nv_ + 2, a + 1], [Z['gold'].uv(.2 + .6 * i / nv_, .2 + .6 * j / nv_)] * 1 + [Z['gold'].uv(.3, .3)] * 3)
    g.add(vis)
    # PLSS backpack, control box on the chest
    g.add(box(.30, .15, .36, zone=Z['white'], bevel=.022, center=(0, .155, .60)))
    g.add(box(.13, .05, .07, zone=Z['dark'], bevel=.006, center=(0, -.115, .60)))
    # hoses
    for s_ in (-1, 1):
        g.add(tube([(s_ * .07, -.09, .57), (s_ * .13, -.075, .50), (s_ * .13, .03, .44)], .007, 5, zone=Z['hose']))
    return g


for s_ in (1, -1):
    Fs = T(s_ * .45, -.44, Z_FLOOR + .01) @ Rz(180)      # suit's -Y (its front) faces the bulkhead
    fur.add(suit(), Fs)
    # donning stand behind each suit
    fur.add(box(.30, .025, .80, zone=Z['frame'], bevel=.005, center=(0, .215, .44)), Fs)
    fur.add(box(.20, .05, .02, zone=Z['frame'], center=(0, .20, .06)), Fs)

# ---- dust station on the vestibule side of the bulkhead
F_vest = Matrix(((1, 0, 0, 0), (0, 0, -1, BULK_Y - BULK_T / 2 - .002), (0, 1, 0, 0), (0, 0, 0, 1)))   # X = +x, Y = up, Z = -y
F_d = F_vest @ T(.585, -.92, 0)
fur.add(box(.31, .19, .008, zone=Z['frame'], center=(0, 0, .003)), F_d)
fur.add(quad_patch(.30, .175, Z['dust'], z=.008), F_d)
# vacuum hose coiled on a bracket, brush on a clip
coil = []
for t_ in np.linspace(0, TAU * 2.6, 56):
    coil.append((.585 + .075 * math.cos(t_), BULK_Y - BULK_T / 2 - .03 - .004 * t_, -1.32 + .075 * math.sin(t_)))
soft.add(tube(coil, .010, 6, zone=Z['hose'], caps=False))
soft.add(tube([coil[-1], (.51, BULK_Y - .13, -1.38), (.48, BULK_Y - .14, -1.47)], .010, 6, zone=Z['hose'], caps=False))
fur.add(tube([(.48, BULK_Y - .14, -1.47), (.47, BULK_Y - .14, -1.60)], .016, 8, zone=Z['dark']))
fur.add(box(.20, .03, .04, zone=Z['frame'], center=(.585, BULK_Y - BULK_T / 2 - .012, -1.32)))
br = Geo()
br.add(box(.03, .022, .20, zone=Z['yellow'], bevel=.004, center=(0, 0, .10)))
br.add(box(.06, .05, .05, zone=Z['dark'], bevel=.006, center=(0, -.006, 0)))
fur.add(br, T(.46, BULK_Y - BULK_T / 2 - .03, -.76))
fur.add(box(.05, .025, .02, zone=Z['frame'], center=(.46, BULK_Y - BULK_T / 2 - .012, -.66)))
# blower bar across the top of the vestibule
fur.add(box(.60, .05, .05, zone=Z['frame'], bevel=.006, center=(-.10, BULK_Y - BULK_T / 2 - .03, -.44)))
on_panel(F_vest, 'htProps_airVent01', -.45, -.46, .002, 1.0, roll=90)
on_panel(F_vest, 'htProps_airVent01', .25, -.46, .002, 1.0, roll=90)
on_panel(F_vest @ T(-.585, -.95, 0), 'htProps_cargoBag_small_white', 0, 0, .05, 1.0)
on_panel(F_vest @ T(-.585, -.72, 0), 'htProps_cargoBag_small_red', 0, 0, .05, 1.0)

# ---- bulkhead door: two prop leaves, cabin and vestibule faces
door_c = Vector((0, BULK_Y, DOOR_Z))
sc_door = (DOOR_W / .786, 1.0, DOOR_H / 1.098)
prop_axes('htProps_HatchDoor', door_c + Vector((0, .005, 0)), (0, 1, 0), (0, 0, 1), sc_door)
prop_axes('htProps_HatchDoor', door_c + Vector((0, -.005, 0)), (0, -1, 0), (0, 0, 1), sc_door)

# ---- ECLSS on the back wall, with real tanks and plumbing
for az_ in (128, 214):
    g, Fe = rack(az_, -.78, .50, .50, 'eclss', r_front=.67, depth=.10); fur.add(g)
    g, Fr = rack(az_, -1.30, .50, .52, 'rack', r_front=.67, depth=.10); fur.add(g)
# tanks either side of the ladder, feed lines along the wall and across the ceiling
for az_, zb in ((152, -1.66), (183, -1.66)):
    c_ = pos(az_, .70, 0)
    prof = [(0, 0), (.05, .004), (.075, .03), (.078, .08), (.078, .42), (.075, .47), (.05, .495), (0, .50)]
    fur.add(lathe(prof, 16, zone=Z['white']), T(c_.x, c_.y, zb))
    for z_ in (.06, .44):
        fur.add(Geo().add(tube([(.085 * math.cos(a_), .085 * math.sin(a_), 0) for a_ in np.linspace(0, TAU, 17)[:-1]], .006, 5, zone=Z['frame'], closed=True, caps=False), T(c_.x, c_.y, zb + z_)))
    top = (c_.x, c_.y, zb + .50)
    pp = Vector(top); wallp = pos(az_ + (10 if az_ < 170 else -10), R_WALL - .02, -.56)
    fur.add(tube([top, (pp.x, pp.y, zb + .62), tuple(wallp + Vector((0, 0, -.50))), tuple(wallp), tuple(pos(az_ + (10 if az_ < 170 else -10), R_WALL - .02, Z_DECK_BOT - .03))], .012, 6, zone=Z['copper' if az_ < 170 else 'hose']))
    v = pp + Vector((0, 0, .12))
    fur.add(tube([(v.x - .03, v.y, v.z), (v.x + .03, v.y, v.z)], .012, 6, zone=Z['red']))
# ceiling service runs
for off, zn_ in ((-.02, 'hose'), (.0, 'dark'), (.02, 'copper')):
    pts = [tuple(pos(a_, .70 + off, Z_DECK_BOT - .02 - abs(off) * .3)) for a_ in np.arange(100, 262, 10)]
    fur.add(tube(pts, .008, 5, zone=Z[zn_], caps=False))
for a_ in np.arange(105, 262, 30):
    F_ = plane_frame(pos(a_, .70, Z_DECK_BOT), (0, 0, -1), up=(math.sin(math.radians(a_)), -math.cos(math.radians(a_)), 0))
    fur.add(box(.09, .022, .03, zone=Z['frame'], center=(0, 0, .02)), F_)

# ---- radiation shelter niche at az -96: padded wings, a roof, water bags all round
A0_, A1_ = -128, -68
ZR = -.52
soft.add(bag_wall(A0_, A1_, Z_FLOOR + .01, ZR, 3, 3, bulge=.05))
for a_, nside in ((A0_, 1), (A1_, -1)):
    p0, p1 = pos(a_, R_WALL - .005, Z_FLOOR + .002), pos(a_, .54, Z_FLOOR + .002)
    t_ = .06
    tang = Vector((math.cos(math.radians(a_)), math.sin(math.radians(a_)), 0))     # d(pos)/d(az)
    for side, zone_ in ((nside, 'shelter'), (-nside, 'frame')):
        o_ = tang * side * t_ / 2
        pts = [p0 + o_, p1 + o_, p1 + o_ + Vector((0, 0, ZR - Z_FLOOR)), p0 + o_ + Vector((0, 0, ZR - Z_FLOOR))]
        z_ = Z[zone_]
        oriented(fur, pts, [z_.uv(0, 0), z_.uv(1, 0), z_.uv(1, 1), z_.uv(0, 1)], tuple((p0 + p1) / 2 + tang * side * 1.0 + Vector((0, 0, .5))))
    pts = [p1 - tang * t_ / 2, p1 + tang * t_ / 2, p1 + tang * t_ / 2 + Vector((0, 0, ZR - Z_FLOOR)), p1 - tang * t_ / 2 + Vector((0, 0, ZR - Z_FLOOR))]
    z_ = Z['frame']
    oriented(fur, pts, [z_.uv(0, 0), z_.uv(1, 0), z_.uv(1, 1), z_.uv(0, 1)], (0, 0, -1))
# roof: curved slab of pad, facing down and out
roof = lathe([(.54, ZR), (R_WALL - .004, ZR)], 12, A0_, A1_, zone=Z['shelter'], flip=False)
fur.add(roof)
fur.add(lathe([(R_WALL - .004, ZR + .06), (.54, ZR + .06)], 12, A0_, A1_, zone=Z['frame'], flip=False))
fur.add(lathe([(.54, ZR), (.54, ZR + .06)], 12, A0_, A1_, zone=Z['frame'], flip=True))

# ---- seats and their side gear on the lower floor
on_panel(inw(92, -.70, .745), 'htProps_cabinet2x2', 0, 0, 0, 1.0)
on_panel(inw(92, -.70, .745), 'htProps_cabinetMonitor', -.088, .08, 0)
on_panel(inw(92, -.70, .745), 'htProps_cabinetMonitorScreen_grid', -.088, .08, 0)
on_panel(inw(92, -.70, .745), 'htProps_cabinetPanel_01_1x2', 0, -.09, 0)

# ---- tube lights and vents
for z_, a_ in ((-.415, 15), (-.415, 150), (-.415, -140)):
    pass
for a_ in (-15, 110, 200):                                                       # upper floor, on the crown
    n_ = Vector((-math.sin(math.radians(a_)) * .62, math.cos(math.radians(a_)) * .62, -.78))
    tan_ = Vector((math.cos(math.radians(a_)), math.sin(math.radians(a_)), 0))
    prop_axes('htProps_tubeLight', pos(a_, .66, 1.40) + n_ * .02, tan_, n_)
for (x_, y_) in ((-.38, .28), (.46, .10), (-.05, -.08)):                         # lower floor, on the ceiling
    prop_axes('htProps_tubeLight', (x_, y_, Z_DECK_BOT - .002), (1, 0, 0), (0, 0, -1))
prop_axes('htProps_tubeLight', (.0, BULK_Y - .10 - .28, Z_DECK_BOT - .002), (1, 0, 0), (0, 0, -1))   # vestibule
for a_, z_ in ((-20, .92), (120, .92), (225, .92)):
    pass
for a_, z_ in ((100, -.48), (250, -.48)):
    on_panel(inw(a_, z_, R_WALL - .004), 'htProps_airVent01', 0, 0, 0, 1.0, roll=90)

# ================================================================== objects
P.mesh('shell', sh, M_iva, smooth_angle=30)
P.mesh('crown', crown, M_iva, smooth_angle=60)
P.mesh('deck_top', deck_top, M_iva, smooth_angle=5)
P.mesh('deck_bot', deck_bot, M_iva, smooth_angle=5)
P.mesh('floor_low', floor_low, M_iva, smooth_angle=5)
P.mesh('bulkhead', bulk, M_iva, smooth_angle=20)
P.mesh('coaming', coam_g, M_iva, smooth_angle=50)
P.mesh('furnishings', fur, M_iva, smooth_angle=40)
P.mesh('soft', soft, M_iva, smooth_angle=75)
P.mesh('glass', glass, M_glass)

# ---- seats: two at the flight station, one in the shelter, one facing it
SEATS = []


def seat(idx, x, y, zfloor, fwd, nm, prop='htProps_seat_Orion2'):
    c_ = Vector((x, y, zfloor + .131))
    fwd = Vector(fwd).normalized(); up = Vector((0, 0, 1))
    F = Matrix((fwd.cross(up), fwd, up)).transposed().to_4x4(); F.translation = c_
    P.empty(f'seat{idx}', F, P.model)
    prop_axes(prop, c_, up, -fwd)
    SEATS.append((f'seat{idx}', nm))


seat(1, -.40, -.21, Z_DECK_TOP, (-1, 0, 0), 'Flight Station Left')
seat(2, -.40, .21, Z_DECK_TOP, (-1, 0, 0), 'Flight Station Right')
seat(3, -.40, .05, Z_FLOOR, (1, 0, 0), 'Storm Shelter')
seat(4, .44, .10, Z_FLOOR, (-1, 0, 0), 'ECLSS Watch')

# ---- window cameras: double-click the window. Local Y looks out, local Z is part up.
CAMS = []


def window_cam(idx, az, z, nm):
    d = pos(az, 1, 0)
    up = Vector((0, 0, 1))
    F = Matrix((d.cross(up), d, up)).transposed().to_4x4(); F.translation = pos(az, .72, z)
    P.empty(nm, F, P.model)
    C = F.copy(); C.translation = pos(az, .875, z)
    o = P.empty(nm + 'collider', C, P.model)
    mp = o.muproperties
    mp.collider = 'MU_COL_BOX'; mp.isTrigger = False; mp.size = (.30, .06, .36); mp.center = (0, 0, 0)
    CAMS.append((nm + 'collider', nm))


window_cam(1, L.WIN_AZ, L.WIN_Z[1], 'cameraWindowUpper')
window_cam(2, L.WIN_AZ, L.WIN_Z[0], 'cameraWindowLower')

# ---- lights
for nm, p_, en in (('lightUpperA', pos(-40, .40, .80), 1000), ('lightUpperB', pos(150, .40, .80), 1000), ('lightUpperC', (0.1, 0, 1.25), 700),
                   ('lightLowerA', pos(120, .35, -.55), 700), ('lightLowerB', pos(-120, .25, -.65), 500), ('lightVest', (0, -.55, -.58), 700)):
    ld = bpy.data.lights.new(nm, 'POINT')
    ld.energy = en; ld.color = (1, .96, .88)
    ld.use_custom_distance = True; ld.cutoff_distance = 2.2
    ld.mulightprop.cullingMask = [True] * 32     # the add-on default leaves out layer 16, the IVA layer
    o = bpy.data.objects.new(nm, ld); P.coll.objects.link(o)
    P.place(o, Matrix.Translation(p_), P.model)

# carry part space into internal space, set layer 16 on everything under the model
P.model.rotation_mode = 'QUATERNION'
P.model.rotation_quaternion = R_IVA.to_quaternion()
bpy.context.view_layer.update()
for o in P.coll.objects:
    if o is not P.root and o is not P.model:
        o.muproperties.layer = 16

P.export(IDIR)
os.replace(os.path.join(IDIR, 'shab_PCM_IVA.json'), os.path.join(out, 'shab_PCM_IVA.json'))

# ================================================================== FreeIva walk shell
S2 = Part('shab_PCM_IVA_shell')
wallg = Geo()
n = 28
zb_ = [Z_FLOOR, Z_DECK_BOT, Z_DECK_TOP, Z_CEIL, 1.30, 1.44, 1.54, 1.58, Z_HATCH_TOP]
rb_ = [R_WALL, R_WALL, R_WALL, R_WALL, .76, .66, .53, .46, .46]
wallg.add(lathe(list(zip(rb_, zb_)), n, flip=True))
wallg.add(lathe([(.46, Z_HATCH_TOP), (0, Z_HATCH_TOP)], n, flip=True))
wallg.add(disc_with_hole(R_WALL, Z_FLOOR, None, 0, Z['deck'], up=True, seg=n, rings=1))
wallg.add(disc_with_hole(R_WALL, Z_DECK_TOP, HATCH_C, HATCH_R, Z['deck'], up=True, seg=n, rings=1))
wallg.add(disc_with_hole(R_WALL, Z_DECK_BOT, HATCH_C, HATCH_R, Z['deck'], up=False, seg=n, rings=1))
for side, yb_ in ((1, BULK_Y), (-1, BULK_Y)):
    for i in range(3):
        for j in range(3):
            if i == 1 and j == 1:
                continue
            x0, x1 = xbreaks[i], xbreaks[i + 1]; z0_, z1_ = zbreaks[j], zbreaks[j + 1]
            oriented(wallg, [(x0, yb_, z0_), (x1, yb_, z0_), (x1, yb_, z1_), (x0, yb_, z1_)], [(0, 0)] * 4, (0, yb_ + side, z0_))
me = wallg.to_mesh('shellCollider')
o = bpy.data.objects.new('shellCollider', me); S2.coll.objects.link(o)
S2.place(o, Matrix(), S2.model)
o.muproperties.collider = 'MU_COL_MESH'; o.muproperties.isConvex = False; o.hide_render = True
S2.model.rotation_mode = 'QUATERNION'; S2.model.rotation_quaternion = R_IVA.to_quaternion()
for x_ in S2.coll.objects:
    if x_ is not S2.root and x_ is not S2.model:
        x_.muproperties.layer = 16
bpy.context.view_layer.update()
S2.export(IDIR)
os.replace(os.path.join(IDIR, 'shab_PCM_IVA_shell.json'), os.path.join(out, 'shab_PCM_IVA_shell.json'))

# ================================================================== cfg
fmt = lambda v: ', '.join(f'{x:.5f}'.rstrip('0').rstrip('.') if '.' in f'{x:.5f}' else f'{x}' for x in v)
L_ = ['// Generated by scripts/build_iva.py: edit the script, not this file.', 'INTERNAL', '{', '\tname = shab_PCM_IVA', '\tMODEL', '\t{', '\t\tmodel = SHABTech/Internals/shab_PCM_IVA', '\t}']
for nm, disp in SEATS:
    L_ += ['\tMODULE', '\t{', '\t\tname = InternalSeat', f'\t\tseatTransformName = {nm}', '\t\tallowCrewHelmet = false', f'\t\tdisplayseatName = {disp}', '\t}']
for col_, cam in CAMS:
    L_ += ['\tMODULE', '\t{', '\t\tname = InternalCameraSwitch', f'\t\tcolliderTransformName = {col_}', f'\t\tcameraTransformName = {cam}', '\t}']
for nm, p_, q_, sc in PROPS:
    L_ += ['\tPROP', '\t{', f'\t\tname = {nm}', f'\t\tposition = {fmt(p_)}', f'\t\trotation = {fmt(q_)}', f'\t\tscale = {fmt(sc)}', '\t}']
L_ += ['}', '']
open(os.path.join(IDIR, 'shab_PCM_IVA.cfg'), 'w').write('\n'.join(L_))
print('PROPS', len(PROPS), sorted({p[0] for p in PROPS}))
