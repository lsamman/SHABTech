"""Greebles for the lander family. Same conventions as greebles.py: local +Z out of the surface."""
import math
from sl import *
from greebles import Z, cable_bundle, junction_box, handrail
import ll as L


def copv(r=.19, zone=None):
    """Composite overwrapped pressure vessel lying on a saddle, long axis along local Y, sitting on z=0."""
    zone = zone or Z.copv
    prof = []
    n = 10
    hl = r * .55
    for i in range(n + 1):
        a = math.pi / 2 * i / n
        prof.append((r * math.sin(a) + 1e-5 if i else 0, -hl - r * math.cos(a)))
    for i in range(n + 1):
        a = math.pi / 2 * i / n
        prof.append((r * math.cos(a) if i < n else 0, hl + r * math.sin(a)))
    g = lathe(prof, 20, zone=zone)
    out = Geo()
    out.add(g, T(0, 0, r + .03) @ Rx(90))
    # boss and valve at one end, two straps and saddles
    out.add(cyl(.03, .05, 8, zone=Z.bare, center_z=False), T(0, -hl - r - .03, r + .03) @ Rx(90))
    for s in (-1, 1):
        out.add(box(r * 1.5, .03, .05, zone=Z.white, bevel=.004, center=(0, s * hl, .025)))
        strap = []
        for i in range(13):
            a = math.pi * i / 12
            strap.append((-(r + .006) * math.cos(a), s * hl, r + .03 + (r + .006) * math.sin(a)))
        out.add(tube(strap, .008, 4, zone=Z.steel, caps=False))
    return out


def gusset(l, h, t, zone):
    """Triangular web in the local YZ plane, foot along +Y from the origin, height at y=0."""
    g = Geo()
    u = zone.uv(.2, .2)
    for sx in (-t / 2, t / 2):
        g.v += [(sx, 0, 0), (sx, l, 0), (sx, 0, h)]
    g.face([0, 2, 1], [zone.uv(0, 0), zone.uv(0, 1), zone.uv(1, 0)])
    g.face([3, 4, 5], [zone.uv(0, 0), zone.uv(1, 0), zone.uv(0, 1)])
    g.face([1, 2, 5, 4], [u, u, u, u])
    g.face([0, 3, 5, 2], [u, u, u, u])
    g.face([0, 1, 4, 3], [u, u, u, u])
    return g


def avionics_box(w, d, h, zone, fin=False):
    """Box on a deck: local +Z up, with four feet and a lid zone."""
    g = Geo()
    body = box(w, d, h, zone=zone, bevel=.006, center=(0, 0, h / 2 + .012))
    # Box projection mirrors the far faces and wraps stencils off the edge, so lay the trim on by hand:
    # the whole zone on the lid, its centre band across each side, all reading the right way round.
    zc = h / 2 + .012
    for i, fi in enumerate(body.f):
        pts = [Vector(body.v[j]) for j in fi]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        ax = max(range(3), key=lambda k: abs(n[k]))
        uvs = []
        for p in pts:
            if ax == 2:
                s, t_ = (p.x + w / 2) / w, (p.y + d / 2) / d
            else:
                if ax == 1:
                    s = (p.x + w / 2) / w if n.y < 0 else 1 - (p.x + w / 2) / w
                    wid = w
                else:
                    s = (p.y + d / 2) / d if n.x > 0 else 1 - (p.y + d / 2) / d
                    wid = d
                t_ = .5 + (p.z - zc) / wid
            uvs.append(zone.uv(min(max(s, 0), 1), min(max(t_, 0), 1)))
        body.uv[i] = tuple(uvs)
    g.add(body)
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.add(box(.03, .03, .014, zone=Z.grey, center=(sx * (w / 2 - .03), sy * (d / 2 - .03), .007)))
    return g


def tank_dome(r, h, seg=32):
    """Propellant tank crown standing proud of the deck."""
    prof = [(r + .03, 0), (r + .03, .012), (r, .018)]
    for i in range(1, 9):
        a = math.pi / 2 * i / 8
        prof.append((r * math.cos(a) if i < 8 else 0, .018 + h * math.sin(a)))
    return lathe(prof, seg, zone=Z.tank_white)


def stanchion(h, zone=None):
    zone = zone or Z.yellow
    g = Geo()
    g.add(cyl(.014, h, 6, zone=zone, center_z=False))
    g.add(cyl(.028, .008, 8, zone=Z.grey, center_z=False))
    return g


def rcs_quad():
    """Rim thruster block: radial mount on a wall (+Z out, +Y up). Nozzle centres in NOZZLES."""
    g = Geo()
    g.add(box(.20, .20, .10, zone=Z.white, bevel=.012, center=(0, 0, .05)))
    g.add(box(.26, .26, .012, zone=Z.grey, bevel=.002, center=(0, 0, .006)))
    return g


RCS_NOZZLES = [((.10, 0, .05), (1, 0, 0)), ((-.10, 0, .05), (-1, 0, 0)), ((0, .10, .05), (0, 1, 0)), ((0, -.10, .05), (0, -1, 0)), ((0, 0, .10), (0, 0, 1))]


def rcs_nozzle():
    """Nozzle along local +Z from the origin (exhaust direction +Z)."""
    g = Geo()
    prof = [(0, 0), (.022, 0), (.024, .012), (.015, .018), (.032, .058), (.030, .058), (.012, .02), (0, .02)]
    g.add(lathe(prof, 10, zone=Z.dark))
    return g


def thruster_frame(frame, pos, direction):
    """Frame at pos on block `frame`, with local +Z along `direction` (block coordinates)."""
    p = frame @ Vector(pos)
    d = (frame.to_3x3() @ Vector(direction)).normalized()
    return frame_axes(p, d)


def phased_array(w=.30, h=.22):
    g = Geo()
    g.add(box(w, h, .03, zone=Z.white, bevel=.004, center=(0, 0, .015)))
    g.add(quad_patch(w * .86, h * .84, Z.hex, z=.0305))
    return g
