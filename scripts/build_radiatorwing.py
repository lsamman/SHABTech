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
import mech_layout as ML

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(31)

P = Part('shab_RadiatorWing')
M_wing = P.material('shab_mech', spec=(.8, .8, .8), shininess=.3)
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


ZA, ZB = .010, SPAN - .010   # sheet ends: clear of the hinge knuckles
ZM = .012                   # manifold centre in from each sheet end


def ytube(x, y0, y1, z, r, sides=10, zone=None, caps=True):
    return tube([(x, y0, z), (x, y1, z)], r, sides, zone=zone or Z.steel, caps=caps)


def panel_sheet(x0):
    """Face sheets in local coords: x normal, y width, z span, mid plane at x0. Pumped-loop artwork from shab_mech."""
    g = Geo()
    hw = W / 2
    hx = TH / 2

    def uvs(ys, zs, mirror=False):
        return [ML.rect_uv(ML.WING, (y + hw) / W if not mirror else 1 - (y + hw) / W, z / SPAN) for y, z in zip(ys, zs)]
    ys = [-hw, hw, hw, -hw]; zs = [ZA, ZA, ZB, ZB]
    oriented_quad(g, [(x0 + hx, y, z) for y, z in zip(ys, zs)], uvs(ys, zs), (1, 0, 0))
    oriented_quad(g, [(x0 - hx, y, z) for y, z in zip(ys, zs)], uvs(ys, zs, True), (-1, 0, 0))
    return g


def panel_trim(x0, tip_x=None, root='knuckle'):
    """Edge stiffeners, end closeouts, coolant manifolds with fittings, hinge knuckles and rotary fluid joints.
    Local coords as panel_sheet. root: 'yoke' for the first panel (motor flange and the root swivel), 'knuckle'
    for a panel hung on the previous one's tip hinge. tip_x: hinge line of the next panel, or None."""
    g = Geo()
    hw = W / 2
    L_ = ZB - ZA
    zc = (ZA + ZB) / 2
    for s in (-1, 1):
        # C-section edge rail with an outboard lip, bolted corner fittings
        g.add(box(TH + .004, .012, L_, zone=Z.white, bevel=.0015, center=(x0, s * (hw - .002), zc)))
        g.add(box(.006, .005, L_ - .05, zone=Z.white, bevel=.001, center=(x0, s * (hw + .0065), zc)))
        for z_ in (ZA + .013, ZB - .013):
            g.add(box(TH + .005, .028, .026, zone=Z.grey, bevel=.002, center=(x0, s * (hw - .012), z_)))
            for sx_ in (-1, 1):
                g.add(cyl(.0032, .0018, 6, zone=Z.steel, center_z=False), T(x0 + sx_ * (TH / 2 + .0025), s * (hw - .012), z_) @ Ry(90 * sx_))
        # rail splice plates at third points
        for z_ in (ZA + L_ / 3, ZA + 2 * L_ / 3):
            g.add(box(TH + .0055, .016, .03, zone=Z.white, bevel=.0015, center=(x0, s * (hw - .004), z_)))
    for z_ in (ZA + .003, ZB - .003):
        g.add(box(TH + .001, W - .02, .006, zone=Z.white, bevel=.001, center=(x0, 0, z_)))
    # supply and return manifolds across both ends, with weld collars and B-nut end fittings
    for zm in (ZA + ZM, ZB - ZM):
        g.add(ytube(x0, -hw + .028, hw - .028, zm, .0078, 12, Z.white))
        for y_ in (-.13, -.045, .045, .13):
            g.add(ytube(x0, y_ - .004, y_ + .004, zm, .0088, 12, Z.grey))
        for s in (-1, 1):
            g.add(ytube(x0, s * (hw - .03), s * (hw - .018), zm, .0093, 6, Z.bare))
    # tie-down bosses the launch snubbers bear on
    for y_ in (-.15, .15):
        g.add(cyl(.0095, TH + .006, 10, zone=Z.steel, bevel=.0015), T(x0, y_, SPAN * .78) @ Ry(90))
    if tip_x is not None:
        # hinge to the next panel: our knuckles inboard, theirs outboard; rotary fluid joint each side
        dx = tip_x - x0
        for s in (-1, 1):
            g.add(ytube(tip_x, s * .05, s * .075, SPAN, .0065, 10, Z.grey))
            g.add(box(abs(dx) + .010, .025, .016, zone=Z.grey, bevel=.002, center=(x0 + dx / 2, s * .0625, SPAN - .008)))
            g.add(ytube(tip_x, s * .145, s * .165, SPAN, .0078, 10, Z.bare))
            g.add(box(abs(dx) + .008, .016, .010, zone=Z.grey, bevel=.0015, center=(x0 + dx / 2, s * .155, SPAN - .009)))
            g.add(pipe_run([(x0, s * (hw - .022), ZB - ZM), (x0, s * .155, ZB - ZM + .001), ((x0 + tip_x) / 2, s * .155, SPAN - .004), (tip_x, s * .155, SPAN)], r=.0036, zone=Z.copper, round_=.006))
        g.add(ytube(tip_x, -.112, .112, SPAN, .0026, 6, Z.steel))
    if root == 'knuckle':
        for s in (-1, 1):
            g.add(ytube(0, s * .077, s * .102, 0, .0065, 10, Z.grey))
            g.add(box(abs(x0) + .010, .025, .016, zone=Z.grey, bevel=.002, center=(x0 / 2, s * .0895, .008)))
            g.add(ytube(0, s * .165, s * .185, 0, .0078, 10, Z.bare))
            g.add(pipe_run([(0, s * .175, 0), (x0 / 2, s * .175, .006), (x0, s * .175, ZA + ZM)], r=.0036, zone=Z.copper, round_=.005))
    else:
        # root hinge on the yoke: two knuckles, the motor's output flange (+y) and the root swivel's rotor (-y)
        for s in (-1, 1):
            g.add(ytube(0, s * .087, s * .113, 0, .0085, 12, Z.grey))
            g.add(box(.012, .026, .02, zone=Z.grey, bevel=.002, center=(x0, s * .1, .01)))
        g.add(ytube(0, .205, .213, 0, .0112, 14, Z.grey))
        g.add(box(.010, .012, .024, zone=Z.grey, bevel=.0015, center=(x0, .207, .014)))
        g.add(ytube(0, -.213, -.205, 0, .0098, 12, Z.bare))
        g.add(pipe_run([(x0, -(hw - .022), ZA + ZM), (x0, -.209, ZA + ZM), (0, -.209, .004)], r=.0036, zone=Z.copper, round_=.006))
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
# hold-down snubbers beside the stack: cup-cone pins, clear of the yoke's sweep when it tracks
for sx in (-1, 1):
    for z_ in (-.13, .24):
        base.add(box(.022, .074, .03, zone=Z.grey, bevel=.003, center=(sx * .216, .049, z_)))
        base.add(cyl(.008, .012, 8, zone=Z.steel), T(sx * .205, .082, z_) @ Ry(90))
    # bolts along the rails
    for z_ in np.linspace(-.3, .3, 7):
        base.add(cyl(.0055, .004, 6, zone=Z.steel, center_z=False), T(sx * .222, .012, float(z_)) @ Rx(-90))
# latch post for the launch retainer strap (the strap itself is animated below)
base.add(box(.012, .08, .018, zone=Z.grey, bevel=.002, center=(.223, .05, .285)))
# tracking bearing under the root: outer race bolted to the tray, pinion housing, coolant feed through the race
race = T(0, 0, Z0) @ Rx(-90)
base.add(lathe([(.0745, .012), (.0745, .0150), (.0730, .0160), (.0675, .0160), (.0675, .0130)], 40, zone=Z.grey), race)
base.add(bolt_ring(.071, 18, br=.0024, h=.0012, zone=Z.steel), race @ T(0, 0, .016))
base.add(box(.032, .004, .026, zone=Z.grey, bevel=.001, center=(-.088, .014, Z0 - .02)))
base.add(cyl(.009, .004, 10, zone=Z.bare, center_z=False), T(-.088, .016, Z0 - .02) @ Rx(-90))
for sx in (-1, 1):
    base.add(box(.07, .006, .03, zone=Z.access, bevel=.0015, center=(sx * .15, .015, -.322)))
    base.add(tube([(sx * .12, .0145, -.322), (sx * .09, .0145, -.322), (sx * .072, .0145, -.31)], .0026, 6, zone=Z.copper))
    for k in (-1, 1):
        base.add(cyl(.0028, .0015, 6, zone=Z.steel, center_z=False), T(sx * .15 + k * .026, .018, -.322) @ Rx(-90))
P.mesh('rad_base', base, M_det, smooth_angle=38)

pivot = P.empty('radPivot', Fp, P.model)

# yoke on the turntable: turns with the pivot. Knuckles, the deploy motor and gearhead (+y), the root rotary
# fluid joint (-y) and the flex-hose service loop from the bearing's coolant union to that joint.
yk = Geo()
yk.add(cyl(.066, .004, 40, zone=Z.white, bevel=.001), T(0, 0, -.0115))
yk.add(box(.03, .30, .0035, zone=Z.white, bevel=.001, center=(-.017, 0, -.0078)))
for s in (-1, 1):
    for y0_, y1_ in ((.06, .085), (.115, .14)):
        yk.add(ytube(0, s * y0_, s * y1_, 0, .0085, 12, Z.white))
        yk.add(box(.019, y1_ - y0_, .0085, zone=Z.white, bevel=.0015, center=(-.0125, s * (y0_ + y1_) / 2, -.005)))
yk.add(bolt_ring(.058, 12, br=.0022, h=.001, zone=Z.steel), T(0, 0, -.0095))
# deploy actuator: harmonic-drive gearhead and motor on the hinge axis, cable to the yoke
yk.add(ytube(0, .2135, .232, 0, .0112, 14, Z.white))
yk.add(ytube(0, .232, .236, 0, .0118, 14, Z.grey))
yk.add(ytube(0, .236, .25, 0, .0090, 12, Z.dark))
yk.add(ytube(0, .25, .2525, 0, .0060, 10, Z.grey))
yk.add(box(.022, .024, .0055, zone=Z.white, bevel=.001, center=(-.012, .222, -.0085)))
yk.add(box(.018, .012, .005, zone=Z.white, bevel=.001, center=(-.012, .16, -.0085)))
yk.add(box(.012, .010, .010, zone=Z.grey, bevel=.001, center=(-.006, .243, .007)))
yk.add(tube([(-.006, .243, .012), (-.014, .243, .012), (-.02, .23, .004), (-.02, .18, -.004)], .0022, 5, zone=Z.black))
# root swivel stator, its bracket, and the hose loop
yk.add(ytube(0, -.236, -.2135, 0, .0098, 12, Z.bare))
yk.add(ytube(0, -.24, -.236, 0, .0106, 6, Z.grey))
yk.add(box(.022, .026, .0055, zone=Z.white, bevel=.001, center=(-.012, -.225, -.0085)))
loop = [(-.024, -.02, -.006), (-.026, -.13, -.005)]
for k in range(17):
    a = math.radians(-90 + 360 * k / 16)
    loop.append((-.034 + .011 * math.cos(a), -.168 + .011 * math.sin(a) - .011, -.005 + .0035 * k / 16))
loop += [(-.026, -.205, -.0005), (-.012, -.222, 0.0)]
yk.add(tube(loop, .0028, 6, zone=Z.bare, caps=True))
for y_ in (-.06, -.11):
    yk.add(box(.010, .006, .006, zone=Z.grey, center=(-.024, y_, -.0055)))
mesh_local('rad_yoke', yk, M_det, Fp, pivot)

# launch retainer strap: hinged at one rail, swings clear before the root hinge moves
STRAP_O = Vector((-.223, .012, .285))
frS = T(*STRAP_O)
st = Geo()
st.add(box(.012, .08, .018, zone=Z.grey, bevel=.002, center=(STRAP_O.x, .05, STRAP_O.z)))
st.add(box(.45, .005, .018, zone=Z.yellow, center=(0, .0905, STRAP_O.z)))
st.add(box(.03, .008, .024, zone=Z.steel, bevel=.002, center=(.21, .0905, STRAP_O.z)))
st_open = Geo(); st_open.add(st, frS @ Rz(115) @ frS.inverted())   # swings out, away from the hull
oS = P.mesh('rad_strap', st_open, M_det, frame=frS)

# ------------------------------------------------------------- panels
F1 = Fp.copy()
F2 = F1 @ T(-D, 0, SPAN)
F3 = F2 @ T(2 * D, 0, SPAN)

o1 = P.empty('rad_p1', F1, pivot)
mesh_local('rad_p1_sheet', panel_sheet(0), M_wing, F1, o1, 20)
mesh_local('rad_p1_trim', panel_trim(0, -D, 'yoke'), M_det, F1, o1)
o2 = P.empty('rad_p2', F2, o1)
mesh_local('rad_p2_sheet', panel_sheet(D), M_wing, F2, o2, 20)
mesh_local('rad_p2_trim', panel_trim(D, 2 * D), M_det, F2, o2)
o3 = P.empty('rad_p3', F3, o2)
mesh_local('rad_p3_sheet', panel_sheet(-D), M_wing, F3, o3, 20)
mesh_local('rad_p3_trim', panel_trim(-D, None), M_det, F3, o3)


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
    P.key('deploy', oS, f, rotation_quaternion=Quaternion((0, 0, 1), math.radians(115 * ease(f / 20.0) - 115)))
P.bake_clips(0)
P.export(out)
P.save_blend(out)
