"""Mars-link high-gain antenna: 1.1 m Cassegrain dish on a two-axis gimbal and folding mast.
Part axes: +Y out of the surface (Unity +Z), +Z up the ship (Unity +Y). Origin on the surface.
Deployed pose is authored; stowed: mast folded along +Z, dish flat, concave side outward."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
from gr_power import *
import sm_layout as L

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(41)

P = Part('shab_HGA')
M_sm = P.material('shab_sm', spec=(.9, .9, .9), shininess=.4)
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)

RD = .55            # dish radius
FOC = .44           # focal length
HINGE_Y = .05
MAST = .60
AZ_Y = HINGE_Y + MAST
EL_OFF = .105       # elevation axis above the azimuth bearing
EL_Y = AZ_Y + EL_OFF
BACK = .082         # dish vertex distance from the elevation axis along the boresight
ELEV = 42.0         # deployed elevation of the boresight above the part's +Y
FR = 180            # 6 s clip


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def Qx(d):
    return Quaternion((1, 0, 0), math.radians(d))


def Qy(d):
    return Quaternion((0, 1, 0), math.radians(d))


def depth(r):
    return r * r / (4 * FOC)


# ------------------------------------------------------------- base and hinge
base = Geo()
base.add(cyl(.15, .014, 24, zone=Z.white, bevel=.004, center_z=False), Rx(-90))
base.add(bolt_ring(.13, 12, zone=Z.steel), Rx(-90) @ T(0, 0, .014))
for s in (-1, 1):
    base.add(box(.018, HINGE_Y + .02, .07, zone=Z.white, bevel=.003, center=(s * .042, (HINGE_Y + .03) / 2, 0)))
base.add(tube([(-.055, HINGE_Y, 0), (.055, HINGE_Y, 0)], .009, 10, zone=Z.steel))
base.add(box(.07, .03, .05, zone=Z.access, bevel=.004, center=(.09, .029, -.07)))
base.add(pipe_run([(.07, .03, -.05), (.03, .04, -.02), (0, HINGE_Y - .012, -.012)], r=.005, zone=Z.black, round_=.012))
# stowed-mast cradle at the far end of the mount, on a short foot
base.add(box(.09, .03, .03, zone=Z.white, bevel=.004, center=(0, .03, .38)))
base.add(box(.05, .02, .05, zone=Z.rubber, center=(0, .05, .38)))
base.add(box(.12, .012, .12, zone=Z.white, bevel=.003, center=(0, .006, .38)))
base.add(box(.05, .010, .24, zone=Z.white, bevel=.002, center=(0, .005, .22)))     # rail back to the main plate, follows the hull
for z_ in (.16, .22, .28):
    base.add(cyl(.005, .003, 6, zone=Z.steel, center_z=False), T(0, .010, z_) @ Rx(-90))
P.mesh('hga_base', base, M_det)

# ------------------------------------------------------------- mast (rest: straight out along +Y)
frM = T(0, HINGE_Y, 0)
mast = Geo()
to_y = Rx(-90)
mast.add(box(.05, .05, .05, zone=Z.white, bevel=.005, center=(0, HINGE_Y + .02, 0)))
mast.add(cyl(.022, MAST - .08, 14, zone=Z.white, center_z=False), T(0, HINGE_Y + .03, 0) @ to_y)
mast.add(lathe([(.022, 0), (.03, .012), (.03, .05), (.022, .06)], 14, zone=Z.bare), T(0, HINGE_Y + .05, 0) @ to_y)
mast.add(lathe([(.022, 0), (.034, .012), (.034, .04)], 14, zone=Z.bare), T(0, AZ_Y - .05, 0) @ to_y)
path = [(.028, HINGE_Y + .05 + i * (MAST - .12) / 6, 0) for i in range(7)]
mast.add(tube(path, .0045, 5, zone=Z.black, caps=False))
for i in range(1, 6):
    mast.add(box(.012, .012, .03, zone=Z.grey, center=(.027, HINGE_Y + .05 + i * (MAST - .12) / 6, 0)))
oM = P.mesh('hga_mast', mast, M_det, frame=frM)

# ------------------------------------------------------------- azimuth stage
frA = T(0, AZ_Y, 0)
az = Geo()
az.add(cyl(.062, .05, 24, zone=Z.white, bevel=.004, center_z=False), frA @ to_y)
az.add(lathe([(.068, 0), (.068, .012), (.058, .016)], 24, zone=Z.steel), frA @ to_y @ T(0, 0, -.004))
az.add(bolt_ring(.052, 8, zone=Z.steel), frA @ to_y @ T(0, 0, .05))
az.add(box(.04, .04, .035, zone=Z.access, bevel=.004, center=(.075, AZ_Y + .02, 0)))
# elevation fork
for s in (-1, 1):
    az.add(box(.016, EL_OFF + .03, .05, zone=Z.white, bevel=.003, center=(s * .082, AZ_Y + .03 + (EL_OFF - .02) / 2, 0)))
az.add(box(.17, .016, .05, zone=Z.white, bevel=.003, center=(0, AZ_Y + .05, 0)))
oA = P.mesh('hga_az', az, M_det, parent=oM, frame=frA)

# ------------------------------------------------------------- elevation stage and dish
frE = T(0, EL_Y, 0)
oE = P.empty('hga_el', frE, oA)
# dish frame: local +Z is the boresight, vertex at BACK along it from the elevation axis
fD = frE @ Rx(-90 + ELEV) @ T(0, 0, BACK)      # Rx(-90) takes +Z to +Y; +ELEV tips it toward +Z

rings = [0, .07, .14, .22, .30, .38, .46, RD]
inner = lathe([(r_, depth(r_)) for r_ in reversed(rings)], 48, uv_fn=lambda az_, r, z, arc: L.dish_in_uv(az_, min(r, .555)))
back = lathe([(r_, depth(r_) - .006) for r_ in rings] + [(RD + .004, depth(RD))], 48, uv_fn=lambda az_, r, z, arc: L.dish_out_uv(az_, min(r, .555)))
dish_sheet = Geo()
dish_sheet.add(inner, fD); dish_sheet.add(back, fD)
P.mesh('hga_dish', dish_sheet, M_sm, parent=oE, frame=frE, smooth_angle=50)

d = Geo()
# rim hoop
hoop = [(RD * math.cos(TAU * i / 48), RD * math.sin(TAU * i / 48), depth(RD)) for i in range(48)]
d.add(tube(hoop, .006, 6, zone=Z.white, closed=True, caps=False), fD)
# back structure: eight ribs, mid hoop, central hub
for i in range(8):
    a = TAU * i / 8
    pts = []
    for k in range(7):
        r_ = .06 + (RD - .06) * k / 6
        pts.append((r_ * math.cos(a), r_ * math.sin(a), depth(r_) - .014 - .018 * (1 - r_ / RD)))
    d.add(tube(pts, .0065, 5, zone=Z.white, caps=False), fD)
    p0 = (.27 * math.cos(a), .27 * math.sin(a), depth(.27) - .03)
    p1 = (.08 * math.cos(a + .35), .08 * math.sin(a + .35), -.05)
    d.add(rod(p0, p1, r=.0045, sides=5, zone=Z.grey), fD)
mid = [(.30 * math.cos(TAU * i / 32), .30 * math.sin(TAU * i / 32), depth(.30) - .022) for i in range(32)]
d.add(tube(mid, .004, 5, zone=Z.white, closed=True, caps=False), fD)
d.add(lathe([(.085, -.075), (.085, .012), (.07, .018)], 24, zone=Z.white), fD)
d.add(lathe([(0, -.075), (.085, -.075)], 24, zone=Z.white), fD)
# trunnions into the fork, on the elevation axis
d.add(tube([(-.074, EL_Y, 0), (.074, EL_Y, 0)], .018, 12, zone=Z.steel))
d.add(box(.17, .05, .06, zone=Z.white, bevel=.006, center=(0, EL_Y, 0)))
# Cassegrain feed: horn on the vertex, subreflector on three struts, cable up the horn
d.add(lathe([(.03, 0), (.03, .05), (.05, .16), (.052, .165), (.046, .165), (.026, .05), (0, .05)], 16, zone=Z.white), fD)
SUB_Z = .25
d.add(lathe([(.09, SUB_Z), (.09, SUB_Z - .004), (.03, SUB_Z - .026), (0, SUB_Z - .03)], 20, zone=Z.white), fD)
d.add(lathe([(.09, SUB_Z), (.05, SUB_Z + .012), (0, SUB_Z + .014)], 20, zone=Z.grey), fD)
for i in range(3):
    a = TAU * i / 3 + .5
    root = (RD * .62 * math.cos(a), RD * .62 * math.sin(a), depth(RD * .62) + .002)
    tip = (.07 * math.cos(a), .07 * math.sin(a), SUB_Z - .012)
    d.add(rod(root, tip, r=.006, sides=6, zone=Z.white), fD)
    d.add(box(.03, .03, .008, zone=Z.grey, center=root), fD)
P.mesh('hga_dish_details', d, M_det, parent=oE, frame=frE, smooth_angle=50)

# ------------------------------------------------------------- colliders
P.hull_collider('col_base', [Vector((.15 * math.cos(TAU * i / 8), y, .15 * math.sin(TAU * i / 8))) for i in range(8) for y in (0, HINGE_Y + .03)])
P.hull_collider('col_mast', [Vector((sx * .035, y, sz * .035)) for sx in (-1, 1) for sz in (-1, 1) for y in (HINGE_Y, AZ_Y + .05)], parent=oM, frame=frM)
pts = [fD @ Vector((RD * math.cos(TAU * i / 14), RD * math.sin(TAU * i / 14), depth(RD))) for i in range(14)]
pts += [fD @ Vector((.09 * math.cos(TAU * i / 6), .09 * math.sin(TAU * i / 6), -.075)) for i in range(6)]
pts += [fD @ Vector((.09 * math.cos(TAU * i / 6), .09 * math.sin(TAU * i / 6), SUB_Z)) for i in range(6)]
P.hull_collider('col_dish', pts, parent=oE, frame=frE)

# ------------------------------------------------------------- keys
# stowed: mast along +Z, and the dish boresight straight out from the surface so it lies flat
QE0 = Qx(90).inverted() @ Qx(-ELEV)
for f in range(0, FR + 1, 10):
    t = f / FR
    P.key('deploy', oM, f, rotation_quaternion=Qx(90 * (1 - ease(f / 90.0))))
    # azimuth swings out and back to show the second axis, clearing the mast on the way
    P.key('deploy', oA, f, rotation_quaternion=Qy(-35 * math.sin(math.pi * ease((f - 50) / 110.0))))
    u = ease((f - 40) / 130.0)
    P.key('deploy', oE, f, rotation_quaternion=Qx((-90 - ELEV) * (1 - u)))
P.bake_clips(0)
P.export(out)
P.save_blend(out)
