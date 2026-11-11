"""Reusable greeble builders. All return a Geo in a local frame: +Z is out of the surface,
+Y is up the part, and the origin sits on the mounting surface. Add with on_cyl(...)."""
import math
from sl import *
import layout as L


class Zones:
    """Details-atlas zones by name."""

    def __init__(self, atlas=2048):
        self.z = {k: Zone(*v, atlas=atlas, ppm=500) for k, v in L.DET.items()}

    def __getattr__(self, k):
        try:
            return self.__dict__['z'][k]
        except KeyError:
            raise AttributeError(k)


Z = Zones()


def handrail(length, standoff=.045, bar=.014, posts=None, zone=None):
    """Straight EVA handrail along local Y, centred, on stand-off posts. Rounded-rect bar."""
    zone = zone or Z.gold
    g = Geo()
    # bar with chamfered corners, tapered ends
    g.add(box(bar, length, bar * .8, zone=zone, bevel=bar * .22, center=(0, 0, standoff)))
    n = posts or max(2, int(length / .24) + 1)
    for i in range(n):
        y = -length / 2 + .02 + (length - .04) * i / (n - 1)
        g.add(box(bar * .6, bar * .6, standoff, zone=Z.gold if zone is Z.gold else Z.grey, bevel=.001, center=(0, y, standoff / 2)))
        g.add(box(bar * 2.1, bar * 2.1, .004, zone=Z.grey, center=(0, y, .002)))
    return g


def rail_grip_band(length, count=3):
    g = Geo()
    return g


def bolt_ring(r, n, br=.0045, h=.004, sides=6, zone=None):
    """Hex bolt heads in a circle, in the local XY plane."""
    g = Geo()
    proto = cyl(br, h, sides, zone=zone or Z.steel, center_z=False)
    for i in range(n):
        a = TAU * i / n
        g.add(proto, T(r * math.cos(a), r * math.sin(a), 0))
    return g


def patch_antenna(w=.13):
    g = Geo()
    g.add(box(w, w, .012, zone=Z.white, bevel=.002, center=(0, 0, .006)))
    g.add(cyl(w * .36, .012, 16, zone=Z.white, bevel=.002, center_z=False), T(0, 0, .012))
    g.add(bolt_ring(w * .44, 8, zone=Z.steel), T(0, 0, .012))
    # coax out the side
    g.add(tube([(w * .5, 0, .006), (w * .56, 0, .006), (w * .6, -.03, .003)], .004, 5, zone=Z.gold))
    return g


def blade_antenna(h=.16):
    g = Geo()
    g.add(box(.05, .09, .006, zone=Z.white, bevel=.001, center=(0, 0, .003)))
    b = Geo()
    # tapered swept blade in the local YZ plane
    pts = [(-.04, 0), (.04, 0), (.04, .4 * h), (.005, h), (-.015, h)]
    t = .005
    for s in (-1, 1):
        for (y, z) in pts:
            b.v.append((s * t, y, z + .006))
    n = len(pts)
    uvz = Z.white
    def U(y, z):
        return uvz.uv((y + .05) / .1, z / (h * 1.1))
    b.face([0, 1, 2, 3], [U(*pts[0]), U(*pts[1]), U(*pts[2]), U(*pts[3])][::1])
    b.f[-1] = (3, 2, 1, 0); b.uv[-1] = (U(*pts[3]), U(*pts[2]), U(*pts[1]), U(*pts[0]))
    b.face([0, 3, 4], [U(*pts[0]), U(*pts[3]), U(*pts[4])])
    b.f[-1] = (4, 3, 0); b.uv[-1] = (U(*pts[4]), U(*pts[3]), U(*pts[0]))
    b.face([n, n + 1, n + 2, n + 3], [U(*pts[0]), U(*pts[1]), U(*pts[2]), U(*pts[3])])
    b.face([n, n + 3, n + 4], [U(*pts[0]), U(*pts[3]), U(*pts[4])])
    for i in range(n):
        j = (i + 1) % n
        b.face([i, j, n + j, n + i], [U(*pts[i]), U(*pts[j]), U(*pts[j]), U(*pts[i])])
    g.add(b)
    return g


def frgf(scale=1.0):
    """Flight-releasable grapple fixture: base, shaft, cam, target post, alignment fins."""
    g = Geo()
    g.add(cyl(.095, .012, 24, zone=Z.white, bevel=.003, center_z=False))
    g.add(bolt_ring(.082, 12, zone=Z.steel), T(0, 0, .012))
    g.add(cyl(.024, .105, 12, zone=Z.white, bevel=.003, center_z=False), T(0, 0, .012))
    g.add(cyl(.034, .018, 12, zone=Z.white, bevel=.003, center_z=False), T(0, 0, .105))
    g.add(box(.012, .05, .02, zone=Z.bare, bevel=.002, center=(0, .03, .11)))
    # three cam wedges
    w = box(.05, .01, .06, zone=Z.white, bevel=.002, center=(.05, 0, .03))
    for a in (0, 120, 240):
        g.add(w, T(0, 0, .012) @ Rz(a))
    # visual target
    g.add(box(.12, .08, .004, zone=Z.black, center=(0, .16, .012)))
    g.add(cyl(.009, .10, 8, zone=Z.white, center_z=False), T(0, .16, .012))
    g.add(cyl(.016, .004, 12, zone=Z.white, center_z=False), T(0, .16, .112))
    if scale != 1:
        out = Geo(); out.add(g, S(scale)); return out
    return g


def wide_camera():
    """Pan-tilt camera on a short boom with a sun shade: looks along local -Y."""
    g = Geo()
    g.add(cyl(.018, .05, 8, zone=Z.white, center_z=False))
    g.add(box(.05, .04, .03, zone=Z.white, bevel=.003, center=(0, 0, .06)))
    g.add(tube([(0, .03, .08), (0, -.05, .08)], .022, 12, zone=Z.white))
    g.add(tube([(0, -.05, .08), (0, -.085, .08)], .028, 12, zone=Z.black, caps=False))
    return g


def exterior_lamp(w=.09, h=.05):
    g = Geo()
    g.add(box(w, h, .022, zone=Z.white, bevel=.003, center=(0, 0, .011)))
    return g


def lamp_lens(w=.09, h=.05):
    g = Geo()
    g.add(box(w * .78, h * .72, .005, zone=Z.lamp, bevel=.001, center=(0, 0, .0245)))
    return g


def vent_stub(r=.018):
    g = Geo()
    g.add(cyl(r * 2.4, .006, 12, zone=Z.grey, center_z=False))
    g.add(cyl(r, .03, 10, zone=Z.bare, center_z=False, r2=r * 1.25), T(0, 0, .006))
    return g


def qd_panel(w=.18, h=.12):
    """Umbilical quick-disconnect plate with a textured connector face."""
    g = Geo()
    g.add(box(w, h, .018, zone=Z.grey, bevel=.002, center=(0, 0, .009)))
    g.add(quad_patch(w * .82, h * .78, Z.connector, z=.0185))
    return g


def junction_box(w=.09, h=.07, d=.03):
    g = Geo()
    g.add(box(w, h, d, zone=Z.access, bevel=.003, center=(0, 0, d / 2)))
    for sx_ in (-1, 1):
        for sy_ in (-1, 1):
            g.add(cyl(.004, .003, 6, zone=Z.steel, center_z=False), T(sx_ * (w / 2 - .008), sy_ * (h / 2 - .008), d))
    return g


def cable_bundle(path, r=.006, n=3, zone=None):
    """A few parallel wires laid along a polyline, offset slightly, with tie wraps every so often."""
    g = Geo()
    offs = [(0, 0)] if n == 1 else [(math.cos(TAU * i / n) * r * 1.3, math.sin(TAU * i / n) * r * 1.3) for i in range(n)]
    for k, (ox, oy) in enumerate(offs):
        pts = [Vector(p) + Vector((ox, 0, oy)) for p in path]
        g.add(tube(pts, r, 5, zone=zone or (Z.black if k else Z.dark), caps=False))
    return g


def ladder(length, width=.17, rung_every=.11, standoff=.05):
    """EVA ladder along local Y on the surface: side rails and round rungs."""
    g = Geo()
    for s in (-1, 1):
        g.add(box(.016, length, .012, zone=Z.yellow, bevel=.002, center=(s * width / 2, 0, standoff)))
        n = max(2, int(length / .3) + 1)
        for i in range(n):
            y = -length / 2 + .02 + (length - .04) * i / (n - 1)
            g.add(box(.012, .012, standoff, zone=Z.grey, center=(s * width / 2, y, standoff / 2)))
    nr = int(length / rung_every)
    for i in range(nr):
        y = -length / 2 + rung_every * (i + .5)
        g.add(tube([(-width / 2, y, standoff), (width / 2, y, standoff)], .0065, 6, zone=Z.yellow))
    return g


def grate_platform(w=.34, d=.22, t=.012):
    """Porch grating cantilevered from the hull: local +Z is out, +Y is up."""
    g = Geo()
    g.add(quad_patch(w, d, Z.grating), T(0, 0, d / 2) @ Rx(-90))
    g.add(box(w, t, d, zone=Z.dark, bevel=.002, center=(0, -t / 2 - .0005, d / 2)))
    for s in (-1, 1):
        g.add(tube([(s * w / 2, -.005, .01), (s * w / 2, -.12, .005)], .007, 6, zone=Z.grey))
        g.add(tube([(s * w / 2, -.012, d), (s * w / 2, -.12, .02)], .006, 6, zone=Z.grey))
    return g


def radiator_panel(r, a0, a1, z0, z1, uv_zone=None):
    """Body-mounted curved radiator: white panel with fluid tubes in the texture."""
    zn = uv_zone or Z.radpanel

    def uv(az, z):
        return zn.uv((az - a0) / (a1 - a0), (z - z0) / (z1 - z0))
    return curved_panel(r, a0, a1, z0, z1, raise_=.010, chamfer=.006, seg=6, uv_fn=uv)


def bracket_clamp(r=.012, w=.022):
    g = Geo()
    g.add(box(w, .012, r * 2.4, zone=Z.grey, bevel=.002, center=(0, 0, r * 1.2)))
    return g


def ogive_tip_fin():
    return Geo()
