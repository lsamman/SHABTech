"""Fold-out radiator wing for the PCM's bays: three panels stowed flat along the ship axis,
unfolding zig-zag straight out from the hull. Deployed pose is authored; keys give stowed.
Part axes: +Y out of the hull (Unity +Z), +Z up the ship (Unity +Y). Origin on the surface.
Pivot: local Z along the wing (radial), so the panel stays edge-on to the sun."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
from gr_power import *
import sm_layout as L

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(31)

P = Part('shab_RadiatorWing')
M_sm = P.material('shab_sm', spec=(.85, .85, .85), shininess=.35)
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)

W = .40            # panel width across the bay
SPAN = .60         # panel length along the wing
TH = .016          # panel thickness
E = .0025
D = TH / 2 + E     # hinge offset from a panel's mid plane, so panels stack with pitch 2D
H0 = .026          # height of the root hinge above the surface
Z0 = -.30          # root hinge position along the ship axis
FR = 150           # 5 s clip


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def Qy(d):
    return Quaternion((0, 1, 0), math.radians(d))


# pivot axes: local x = part Z (panel normal), local y = part X (width), local z = part Y (span)
Fp = Matrix(((0, 1, 0, 0), (0, 0, 1, H0), (1, 0, 0, Z0), (0, 0, 0, 1)))


def panel_sheet(x0):
    """Panel in local coords: x normal, y width, z span from 0 to SPAN, mid plane at x0."""
    g = Geo()
    hw = W / 2
    hx = TH / 2

    def uvs(ys, zs):
        return [L.rad_uv((y + hw) / W, z / SPAN) for y, z in zip(ys, zs)]
    ys = [-hw, hw, hw, -hw]; zs = [0, 0, SPAN, SPAN]
    oriented_quad(g, [(x0 + hx, y, z) for y, z in zip(ys, zs)], uvs(ys, zs), (1, 0, 0))
    oriented_quad(g, [(x0 - hx, y, z) for y, z in zip(ys, zs)], uvs([-y for y in ys], zs), (-1, 0, 0))
    return g


def panel_trim(x0, root_lugs, tip_lugs, tip_x):
    """Edge rails, end headers, hinge lugs and rotary fluid joints, in local coords."""
    g = Geo()
    hw = W / 2
    for s in (-1, 1):
        g.add(box(TH + .004, .012, SPAN, zone=Z.white, bevel=.002, center=(x0, s * (hw - .002), SPAN / 2)))
    # end headers: the fluid manifolds
    for z_ in (.016, SPAN - .016):
        g.add(tube([(x0, -hw + .008, z_), (x0, hw - .008, z_)], .0095, 8, zone=Z.white))
    # hinge lugs at the tip, on the outboard hinge line
    for y_ in (-.13, .13):
        if tip_lugs:
            g.add(box(tip_x * 1.4 if False else .026, .03, .03, zone=Z.grey, bevel=.003, center=(x0 + (tip_x - x0) * .55, y_, SPAN - .006)))
            g.add(tube([(tip_x, y_ - .018, SPAN), (tip_x, y_ + .018, SPAN)], .0065, 8, zone=Z.steel))
        if root_lugs:
            g.add(box(.026, .03, .03, zone=Z.grey, bevel=.003, center=(x0 * .45, y_ + .036, .006)))
            g.add(tube([(0, y_ + .036 - .015, 0), (0, y_ + .036 + .015, 0)], .0065, 8, zone=Z.bare))
    # rotary fluid joint on the hinge axis, each side
    if tip_lugs:
        for s in (-1, 1):
            y_ = s * (hw - .035)
            g.add(tube([(tip_x, y_ - .022, SPAN), (tip_x, y_ + .022, SPAN)], .0105, 10, zone=Z.bare))
            g.add(pipe_run([(tip_x, y_, SPAN), ((tip_x + x0) / 2, y_, SPAN - .012), (x0, y_, SPAN - .016)], r=.0048, zone=Z.copper, round_=.008))
    # tie-down boss on each panel face near the tip
    for y_ in (-.15, .15):
        g.add(cyl(.009, TH + .006, 8, zone=Z.steel), Matrix.Translation((x0, y_, SPAN * .78)) @ Ry(90))
    return g


def mesh_local(name, geo, mat, frame, parent, smooth=38):
    g = Geo(); g.add(geo, frame)
    return P.mesh(name, g, mat, parent=parent, frame=frame, smooth_angle=smooth)


# ------------------------------------------------------------- static tray
base = Geo()
base.add(box(.46, .012, .68, zone=Z.white, bevel=.003, center=(0, .006, 0)))
# curved-hull feet down into the blanket
for sx in (-1, 1):
    base.add(box(.04, .05, .66, zone=Z.white, bevel=.003, center=(sx * .205, -.023, 0)))
for sz in (-1, 1):
    base.add(box(.41, .03, .03, zone=Z.grey, bevel=.003, center=(0, -.012, sz * .32)))
# hold-down snubbers beside the stack: cup-cone pins, tall enough to reach the top panel
for sx in (-1, 1):
    for z_ in (-.18, .24):
        base.add(box(.022, .074, .03, zone=Z.grey, bevel=.003, center=(sx * .216, .049, z_)))
        base.add(cyl(.008, .012, 8, zone=Z.steel), T(sx * .205, .082, z_) @ Ry(90))
    # bolts along the rails
    for z_ in np.linspace(-.3, .3, 7):
        base.add(cyl(.0055, .004, 6, zone=Z.steel, center_z=False), T(sx * .222, .012, float(z_)) @ Rx(-90))
# latch post for the launch retainer strap (the strap itself is animated below)
base.add(box(.012, .08, .018, zone=Z.grey, bevel=.002, center=(.223, .05, .285)))
# root hinge clevises and the coolant feed through the tray
for y_ in (-.13, .13):
    base.add(box(.03, .05, .03, zone=Z.white, bevel=.003, center=(y_ + .036, .022, Z0)))
    base.add(box(.03, .05, .03, zone=Z.white, bevel=.003, center=(y_ - .036, .022, Z0)))
base.add(box(.14, .03, .06, zone=Z.access, bevel=.004, center=(0, .027, -.325)))
for sx in (-1, 1):
    base.add(pipe_run([(sx * .04, .027, -.325), (sx * .16, .02, -.33), (sx * .17, H0 + .002, Z0)], r=.0052, zone=Z.copper, round_=.012))
    base.add(tube([(sx * .165, H0, Z0 - .001), (sx * .19, H0, Z0 - .001)], .0115, 10, zone=Z.bare))
P.mesh('rad_base', base, M_det, smooth_angle=38)

pivot = P.empty('radPivot', Fp, P.model)

# launch retainer strap: hinged at one rail, swings clear before the root hinge moves
STRAP_O = Vector((-.223, .012, .285))
frS = T(*STRAP_O)
st = Geo()
st.add(box(.012, .08, .018, zone=Z.grey, bevel=.002, center=(STRAP_O.x, .05, STRAP_O.z)))
st.add(box(.45, .005, .018, zone=Z.yellow, center=(0, .0905, STRAP_O.z)))
st.add(box(.03, .008, .024, zone=Z.steel, bevel=.002, center=(.21, .0905, STRAP_O.z)))
st_open = Geo(); st_open.add(st, frS @ Rz(-115) @ frS.inverted())
oS = P.mesh('rad_strap', st_open, M_det, frame=frS)

# ------------------------------------------------------------- panels
F1 = Fp.copy()
F2 = F1 @ T(-D, 0, SPAN)
F3 = F2 @ T(2 * D, 0, SPAN)

o1 = P.empty('rad_p1', F1, pivot)
mesh_local('rad_p1_sheet', panel_sheet(0), M_sm, F1, o1, 20)
mesh_local('rad_p1_trim', panel_trim(0, True, True, -D), M_det, F1, o1)
o2 = P.empty('rad_p2', F2, o1)
mesh_local('rad_p2_sheet', panel_sheet(D), M_sm, F2, o2, 20)
mesh_local('rad_p2_trim', panel_trim(D, False, True, 2 * D), M_det, F2, o2)
o3 = P.empty('rad_p3', F3, o2)
mesh_local('rad_p3_sheet', panel_sheet(-D), M_sm, F3, o3, 20)
mesh_local('rad_p3_trim', panel_trim(-D, False, False, 0), M_det, F3, o3)


def hull_for(frame, x0, parent, name):
    pts = [frame @ Vector((x0 + sx * (TH / 2 + .006), sy * W / 2, z)) for sx in (-1, 1) for sy in (-1, 1) for z in (0, SPAN)]
    return P.hull_collider(name, pts, parent=parent, frame=frame)


hull_for(F1, 0, o1, 'col_p1')
hull_for(F2, D, o2, 'col_p2')
hull_for(F3, -D, o3, 'col_p3')
P.hull_collider('col_base', [Vector((sx * .23, y, sz * .34)) for sx in (-1, 1) for y in (-.03, .012) for sz in (-1, 1)])

# ------------------------------------------------------------- keys: root swings up, then outer panels straighten
for f in range(0, FR + 1, 10):
    P.key('deploy', o1, f, rotation_quaternion=Qy(90 * (1 - ease(f / 60.0))))
    P.key('deploy', o2, f, rotation_quaternion=Qy(-180 * (1 - ease((f - 25) / 85.0))))
    P.key('deploy', o3, f, rotation_quaternion=Qy(180 * (1 - ease((f - 55) / 95.0))))
# strap rest = open; stowed = latched across the pack. It swings away over the first 20 frames.
for f in (0, 5, 10, 15, 20, FR):
    P.key('deploy', oS, f, rotation_quaternion=Quaternion((0, 0, 1), math.radians(-115 * ease(f / 20.0) + 115)))
P.bake_clips(0)
P.export(out)
P.save_blend(out)
