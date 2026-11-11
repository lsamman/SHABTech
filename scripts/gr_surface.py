"""Helpers for the surface parts: trim zones and small builders."""
import math
from sl import *
from greebles import Z
from surface_layout import *

SZ = {k: Zone(*v, atlas=2048, ppm=400) for k, v in SURF.items()}
RZ = {k: Zone(*v, atlas=ROVER_ATLAS, ppm=400) for k, v in ROV.items()}
IZ = {k: Zone(*v, atlas=ISRU_ATLAS, ppm=400) for k, v in ISR.items()}


def facing(origin, dir_, up=(0, 0, 1)):
    """Frame at origin: local +Z along dir_, local +Y as close to `up` as possible."""
    z = Vector(dir_).normalized()
    y = Vector(up)
    y = (y - y.dot(z) * z).normalized()
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def unity_look_frame(origin, target, side=(1, 0, 0)):
    """Frame whose Blender +Y points at target. Blender +Y becomes Unity +Z on export, so a
    Unity LookAt (FXModuleLookAtConstraint) keeps this mesh pointed down its length."""
    y = (Vector(target) - Vector(origin)).normalized()
    x = Vector(side); x = (x - x.dot(y) * y).normalized()
    z = x.cross(y)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def boxmap(x0, x1, y0, y1, z0, z1, bev, zones, flip_top=False):
    """Chamfered box with each face mapped to its own zone: zones has top, bottom, xn, xp, yn, yp.
    Unique mapping for AO-baked chassis and racks. U follows Y on the top and long sides."""
    g = Geo()

    def quad(p, uv):
        s = len(g.v)
        g.v.extend(p)
        g.face([s, s + 1, s + 2, s + 3], uv)

    b = bev
    # top (U along +Y, V along -X so the deck reads upright from the left side)
    zt = zones['top']
    quad([(x1 - b, y0 + b, z1), (x1 - b, y1 - b, z1), (x0 + b, y1 - b, z1), (x0 + b, y0 + b, z1)],
         [zt.uv(0, 0), zt.uv(1, 0), zt.uv(1, 1), zt.uv(0, 1)])
    zb = zones['bottom']
    quad([(x0 + b, y0 + b, z0), (x0 + b, y1 - b, z0), (x1 - b, y1 - b, z0), (x1 - b, y0 + b, z0)],
         [zb.uv(0, 0), zb.uv(1, 0), zb.uv(1, 1), zb.uv(0, 1)])
    # long sides. xp: seen from +X looking -X, +Y is to the viewer's right
    zp = zones['xp']
    quad([(x1, y0 + b, z0 + b), (x1, y1 - b, z0 + b), (x1, y1 - b, z1 - b), (x1, y0 + b, z1 - b)],
         [zp.uv(0, 0), zp.uv(1, 0), zp.uv(1, 1), zp.uv(0, 1)])
    zn = zones['xn']
    quad([(x0, y1 - b, z0 + b), (x0, y0 + b, z0 + b), (x0, y0 + b, z1 - b), (x0, y1 - b, z1 - b)],
         [zn.uv(0, 0), zn.uv(1, 0), zn.uv(1, 1), zn.uv(0, 1)])
    # short ends. yp: seen from +Y looking -Y, -X is to the viewer's right
    zq = zones['yp']
    quad([(x1 - b, y1, z0 + b), (x0 + b, y1, z0 + b), (x0 + b, y1, z1 - b), (x1 - b, y1, z1 - b)],
         [zq.uv(0, 0), zq.uv(1, 0), zq.uv(1, 1), zq.uv(0, 1)])
    zy = zones['yn']
    quad([(x0 + b, y0, z0 + b), (x1 - b, y0, z0 + b), (x1 - b, y0, z1 - b), (x0 + b, y0, z1 - b)],
         [zy.uv(0, 0), zy.uv(1, 0), zy.uv(1, 1), zy.uv(0, 1)])
    # chamfers: map to an edge pixel row of the neighbouring side so they stay in that panel's tone
    if b > 0:
        ed = zones['xp'].uv(.5, .96)
        edb = zones['xp'].uv(.5, .04)
        cor = [
            ((x1, y0 + b, z1 - b), (x1, y1 - b, z1 - b), (x1 - b, y1 - b, z1), (x1 - b, y0 + b, z1)),   # +X top
            ((x0 + b, y0 + b, z1), (x0 + b, y1 - b, z1), (x0, y1 - b, z1 - b), (x0, y0 + b, z1 - b)),   # -X top
            ((x1 - b, y1, z1 - b), (x0 + b, y1, z1 - b), (x0 + b, y1 - b, z1), (x1 - b, y1 - b, z1)),   # +Y top
            ((x0 + b, y0, z1 - b), (x1 - b, y0, z1 - b), (x1 - b, y0 + b, z1), (x0 + b, y0 + b, z1)),   # -Y top
            ((x1 - b, y0 + b, z0), (x1 - b, y1 - b, z0), (x1, y1 - b, z0 + b), (x1, y0 + b, z0 + b)),   # +X bottom
            ((x0, y0 + b, z0 + b), (x0, y1 - b, z0 + b), (x0 + b, y1 - b, z0), (x0 + b, y0 + b, z0)),   # -X bottom
            ((x0 + b, y1, z0 + b), (x1 - b, y1, z0 + b), (x1 - b, y1 - b, z0), (x0 + b, y1 - b, z0)),   # +Y bottom
            ((x1 - b, y0, z0 + b), (x0 + b, y0, z0 + b), (x0 + b, y0 + b, z0), (x1 - b, y0 + b, z0)),   # -Y bottom
            ((x1, y1 - b, z0 + b), (x1 - b, y1, z0 + b), (x1 - b, y1, z1 - b), (x1, y1 - b, z1 - b)),   # verticals
            ((x0 + b, y1, z0 + b), (x0, y1 - b, z0 + b), (x0, y1 - b, z1 - b), (x0 + b, y1, z1 - b)),
            ((x0, y0 + b, z0 + b), (x0 + b, y0, z0 + b), (x0 + b, y0, z1 - b), (x0, y0 + b, z1 - b)),
            ((x1 - b, y0, z0 + b), (x1, y0 + b, z0 + b), (x1, y0 + b, z1 - b), (x1 - b, y0, z1 - b)),
        ]
        for k, q in enumerate(cor):
            uv = edb if 4 <= k < 8 else ed
            quad(list(q), [uv, uv, uv, uv])
        tri = [((x1, y1 - b, z1 - b), (x1 - b, y1, z1 - b), (x1 - b, y1 - b, z1)), ((x0 + b, y1, z1 - b), (x0, y1 - b, z1 - b), (x0 + b, y1 - b, z1)),
               ((x0, y0 + b, z1 - b), (x0 + b, y0, z1 - b), (x0 + b, y0 + b, z1)), ((x1 - b, y0, z1 - b), (x1, y0 + b, z1 - b), (x1 - b, y0 + b, z1)),
               ((x1 - b, y1 - b, z0), (x1 - b, y1, z0 + b), (x1, y1 - b, z0 + b)), ((x0, y1 - b, z0 + b), (x0 + b, y1, z0 + b), (x0 + b, y1 - b, z0)),
               ((x0 + b, y0 + b, z0), (x0 + b, y0, z0 + b), (x0, y0 + b, z0 + b)), ((x1, y0 + b, z0 + b), (x1 - b, y0, z0 + b), (x1 - b, y0 + b, z0))]
        for t in tri:
            s = len(g.v)
            g.v.extend(t)
            g.face([s, s + 1, s + 2], [ed, ed, ed])
    return g


def prism(p0, p1, w, h, up=(0, 0, 1), zone=None):
    """Rectangular bar from p0 to p1. w across, h along `up`."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0)
    L = d.length
    y = d.normalized()
    z = Vector(up); z = (z - z.dot(y) * y).normalized()
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = (p0 + p1) / 2
    g = Geo()
    g.add(box(w, L, h, zone=zone, bevel=min(w, h) * .15), m)
    return g


def x_axis(g):
    """Rotate a Z-axis Geo so its axis lies along +X."""
    out = Geo(); out.add(g, Ry(90))
    return out


def fin_stack(r_in, r_out, n, pitch, thick, zone, seg=16):
    """Coaxial cooling fins along Z, centred at the origin."""
    g = Geo()
    for i in range(n):
        z = (i - (n - 1) / 2) * pitch
        g.add(cyl(r_out, thick, seg, zone=zone, bevel=thick * .25), T(0, 0, z))
    g.add(cyl(r_in, pitch * n, seg, zone=zone))
    return g


def valve(size=.05, zone=None):
    g = Geo()
    zn = zone or SZ['valve']
    g.add(box(size, size, size * 1.1, zone=zn, bevel=size * .1))
    g.add(cyl(size * .22, size * .55, 8, zone=Z.steel, center_z=False), T(0, 0, size * .55))
    g.add(box(size * 1.2, size * .22, size * .1, zone=Z.red, bevel=size * .03), T(0, 0, size * 1.1))
    return g


def ptube(path, r=.008, zone=None, sides=6):
    return tube(path, r, sides, zone=zone or Z.copper)


def smooth_path(pts, n=6):
    """Catmull-Rom through pts, for plumbing that bends instead of kinking."""
    P = [Vector(p) for p in pts]
    P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return [tuple(v) for v in out]


def strip_path(pts, w, h, up_fn, zone=None):
    """Flat rectangular strap along a polyline. up_fn(point) gives the outward direction, so
    the strap lies flat on a curved surface (wheel chevrons, cable clamps)."""
    g = Geo()
    P_ = [Vector(p) for p in pts]
    n = len(P_)
    rows = []
    for i, p in enumerate(P_):
        d = (P_[min(i + 1, n - 1)] - P_[max(i - 1, 0)]).normalized()
        up = Vector(up_fn(p)).normalized()
        side = d.cross(up).normalized() * (w / 2)
        tall = up * h
        s = len(g.v)
        g.v.extend([tuple(p - side), tuple(p + side), tuple(p + side + tall), tuple(p - side + tall)])
        rows.append(s)
    def uv(s, t):
        return zone.uv(s, t) if zone else (0, 0)
    for i in range(n - 1):
        a, b = rows[i], rows[i + 1]
        t0, t1 = i / (n - 1), (i + 1) / (n - 1)
        g.face([a + 3, a + 2, b + 2, b + 3], [uv(0, t0), uv(1, t0), uv(1, t1), uv(0, t1)])    # top
        g.face([a + 1, b + 1, b + 2, a + 2], [uv(1, t0), uv(1, t1), uv(.95, t1), uv(.95, t0)])  # side
        g.face([b, a, a + 3, b + 3], [uv(0, t1), uv(0, t0), uv(.05, t0), uv(.05, t1)])          # side
    a = rows[0]; b = rows[-1]
    g.face([a, a + 1, a + 2, a + 3], [uv(0, 0), uv(1, 0), uv(1, .05), uv(0, .05)])
    g.face([b + 1, b, b + 3, b + 2], [uv(1, 1), uv(0, 1), uv(0, .95), uv(1, .95)])
    return g
