"""Helpers for the service module and power parts: thrusters, tanks, oriented quads."""
import math
from sl import *
from greebles import Z, bolt_ring, junction_box, vent_stub, qd_panel, handrail


def oriented_quad(g, pts, uvs, normal):
    """Add a quad (or tri) with winding forced to agree with `normal`."""
    i0 = len(g.v)
    for p in pts:
        g.v.append(tuple(p))
    a, b, c = Vector(pts[0]), Vector(pts[1]), Vector(pts[2])
    idx = list(range(i0, i0 + len(pts)))
    uv = list(uvs)
    if (b - a).cross(c - a).dot(Vector(normal)) < 0:
        idx.reverse(); uv.reverse()
    g.face(idx, uv)


def frame_y(origin, y_dir, up=(0, 0, 1)):
    """Frame whose local +Y is y_dir: on an empty this is Unity local +Z, the axis stock
    ModuleRCSFX thrusters exhaust along."""
    y = Vector(y_dir).normalized()
    u = Vector(up)
    if abs(u.dot(y)) > .95:
        u = Vector((1, 0, 0))
    z = (u - u.dot(y) * y).normalized()
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def nozzle(r_exit, length, r_throat=None, seg=12, outer=None, inner=None):
    """Small bell: throat at the origin, exit at +Z. Faces out and in."""
    rt = r_throat or r_exit * .36
    g = Geo()
    prof = [(rt, 0)]
    for i in range(1, 6):
        t = i / 5
        prof.append((rt + (r_exit - rt) * (t ** .62), length * t))
    g.add(lathe(prof, seg, zone=outer or Z.nozzle))
    prof2 = [(r_exit, length), (r_exit * .96, length - .001)]
    for i in range(4, -1, -1):
        t = i / 5
        prof2.append(((rt + (r_exit - rt) * (t ** .62)) * .95, length * t + .0005))
    prof2.append((0, 0.0))
    g.add(lathe(prof2, seg, zone=inner or Z.nozzle_in))
    return g


def dome(r, seg=24, rings=7, zone=None, squash=1.0):
    """Hemisphere bulging toward -Z, equator at the origin. Outward faces."""
    prof = []
    for i in range(rings + 1):
        a = math.pi / 2 * i / rings
        prof.append((r * math.sin(a), -r * squash * math.cos(a)))
    return lathe(prof, seg, zone=zone or Z.tank_grey)


def rod(a, b, r=.006, sides=6, zone=None):
    return tube([a, b], r, sides, zone=zone or Z.grey)


def pipe_run(points, r=.007, zone=None, sides=6, round_=.03):
    """Polyline with softened corners: each interior corner is replaced by a short arc."""
    pts = [Vector(p) for p in points]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, p, b = pts[i - 1], pts[i], pts[i + 1]
        d1 = (a - p); d2 = (b - p)
        s = min(round_, d1.length * .45, d2.length * .45)
        p1 = p + d1.normalized() * s; p2 = p + d2.normalized() * s
        for k in range(5):
            t = k / 4
            out.append((1 - t) ** 2 * p1 + 2 * (1 - t) * t * p + t ** 2 * p2)
    out.append(pts[-1])
    return tube(out, r, sides, zone=zone or Z.steel)
