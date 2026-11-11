"""shab_RoverWheel: LRV-style wire-mesh wheel with titanium chevrons, hub motor, fork, and a
trailing swing arm. Hierarchy follows stock roverWheelS2 (WheelCollider, SuspensionPivot,
SteeringPivot, WheelPivot, wheel/bustedwheel). Mounts from above: part +Y up, axle along X."""
import bpy, sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
from gr_surface import *

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(11); random.seed(11)

R = .28            # tyre radius
HW = .11           # half width
Z_NODE = .46       # top of the mount plate above the hub

P = Part('shab_RoverWheel')
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)
M_sf = P.material('shab_surface', spec=(.9, .9, .9), shininess=.3)
M_wire = P.material('shab_wiremesh', shader='KSP/Alpha/Cutoff Bumped')
it = M_wire.mumatprop.float3.properties.add(); it.name = '_Cutoff'; it.value = .45


def tyre_uv(tot, repeats=7):
    def fn(az, r, z, arc):
        return (az / 360 * repeats, arc / tot * 1.0)
    return fn


def tyre_geo(r=R, hw=HW, seg=48, inner=False):
    prof = [(r - .040, -hw), (r - .018, -hw + .012), (r - .004, -hw * .62), (r, -hw * .2), (r, hw * .2), (r - .004, hw * .62), (r - .018, hw - .012), (r - .040, hw)]
    tot = sum(math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]) for i in range(1, len(prof)))
    return lathe(prof, seg, 0, 360, uv_fn=tyre_uv(tot), flip=inner)


wire = Geo()
wire.add(x_axis(tyre_geo()))
wire.add(x_axis(tyre_geo(r=R - .003, inner=True)))

# --- rotating structure: rims, bump stop, spokes, rotor, chevrons
rot = Geo()      # details atlas
rot_s = Geo()    # surface sheet: chevrons and rotor end discs
for s in (-1, 1):
    # outer rim hoop where the mesh clamps
    pr = [(R - .058, s * (HW + .002)), (R - .040, s * (HW + .004)), (R - .036, s * (HW - .004)), (R - .058, s * (HW - .006))]
    if s < 0:
        pr = pr[::-1]
    # orient so faces stay outward: run the outline in the direction lathe expects
    rot.add(x_axis(lathe([(R - .060, s * (HW - .012)), (R - .060, s * (HW + .004)), (R - .036, s * (HW + .006)), (R - .036, s * (HW - .012))][:: (1 if s > 0 else -1)], 48, zone=Z.bare)))
    # spokes
    for k in range(10):
        a = TAU * (k + (.5 if s > 0 else 0)) / 10
        hubp = (s * .058, .075 * math.cos(a), .075 * math.sin(a))
        b = a + .22
        rimp = (s * (HW - .004), (R - .058) * math.cos(b), (R - .058) * math.sin(b))
        rot.add(tube([hubp, rimp], .0062, 5, zone=Z.bare))
# inner bump-stop hoop, visible through the mesh
rot.add(x_axis(lathe([(R - .09, -.075), (R - .082, -.072), (R - .082, .072), (R - .09, .075)], 40, zone=Z.steel)))
rot.add(x_axis(lathe([(R - .092, .074), (R - .092, -.074)], 40, zone=Z.dark)))
# rotor drum on the hub
rot.add(x_axis(lathe([(.04, -.078), (.084, -.078), (.088, -.072), (.088, .072), (.084, .078), (.04, .078)], 24, zone=Z.grey)))
# rotor end disc, textured
rot_s.add(x_axis(lathe([(.084, .078), (0, .078)], 24, zone=SZ['hub'], uv_fn=lambda az, r, z, arc: SZ['hub'].uv(.5 + .5 * r / .09 * math.sin(math.radians(az)), .5 + .5 * r / .09 * math.cos(math.radians(az))))))
rot_s.add(x_axis(lathe([(0, -.078), (.084, -.078)], 24, zone=SZ['hub'], uv_fn=lambda az, r, z, arc: SZ['hub'].uv(.5 + .5 * r / .09 * math.sin(math.radians(az)), .5 + .5 * r / .09 * math.cos(math.radians(az))))))
# chevrons: titanium V strips riveted over the mesh on half the contact area
NCH = 26


def tread_r(f):
    """Tyre surface radius at |x| = f * HW, following the crowned profile."""
    return R + .0025 - .022 * max(0.0, (f - .25) / .75) ** 2


def radial_up(p):
    return (0, p[1], p[2])


for k in range(NCH):
    a0 = 360 * k / NCH
    for s in (-1, 1):
        path = []
        for f in (0, .22, .44, .66, .84, .95):
            a = math.radians(a0 + f * 7.0)
            rr = tread_r(f)
            path.append((s * f * HW, rr * math.sin(a), -rr * math.cos(a)))
        rot_s.add(strip_path(path, .017, .0045, radial_up, zone=SZ['tread']))
    # rivet plate at the crown of each V
    a = math.radians(a0)
    rot_s.add(strip_path([(-.012, (R + .0035) * math.sin(a), -(R + .0035) * math.cos(a)), (.012, (R + .0035) * math.sin(a), -(R + .0035) * math.cos(a))], .026, .003, radial_up, zone=SZ['tread']))

# --- broken-wheel stand-in: crushed mesh, a couple of chevrons hanging off
crushed = Geo()
crushed.add(wire)
pts = np.array(crushed.v, float)
rng_ = np.random.default_rng(5)
n = np.sin(pts[:, 1] * 19 + pts[:, 0] * 11) * .014 + rng_.normal(0, .004, len(pts))
rad = np.hypot(pts[:, 1], pts[:, 2]) + 1e-6
pts[:, 2] = np.where(pts[:, 2] < -.05, -.05 + (pts[:, 2] + .05) * .35, pts[:, 2])     # flat spot on the ground side
pts[:, 1:] *= (1 + n / rad)[:, None]
pts[:, 0] *= 1 + .25 * np.sin(np.arctan2(pts[:, 2], pts[:, 1]) * 3)
crushed.v = [tuple(v) for v in pts]
crushed_rot = Geo()
for k in range(10):
    a = TAU * k / 10
    crushed_rot.add(tube([(.058, .075 * math.cos(a), .075 * math.sin(a)), (.09, .17 * math.cos(a + .4), .17 * math.sin(a + .4))], .006, 5, zone=Z.bare))
    crushed_rot.add(tube([(-.058, .075 * math.cos(a), .075 * math.sin(a)), (-.09, .15 * math.cos(a - .3), .15 * math.sin(a - .3))], .006, 5, zone=Z.bare))
crushed_rot.add(x_axis(lathe([(.04, -.078), (.084, -.078), (.088, -.072), (.088, .072), (.084, .078), (.04, .078)], 16, zone=Z.dark)))

# --- fork: crown, tines, hub bearings, stator shaft, fender. Steers with the wheel.
fork = Geo()      # details atlas
fork_s = Geo()    # surface sheet
CROWN_Z = .325
TX = HW + .036           # tine X offset (wheel + clearance)
for s in (-1, 1):
    # tine: tapered box from crown to axle, with a machined relief panel
    top = (s * TX, 0, CROWN_Z)
    bot = (s * TX, 0, 0)
    fork.add(prism(bot, top, .026, .078, up=(0, 1, 0), zone=Z.grey))
    fork.add(x_axis(cyl(.052, .03, 18, zone=Z.grey, bevel=.004)), T(s * TX, 0, 0))
    fork_s.add(x_axis(lathe([(.045, s * .0165), (0, s * .0165)][:: (1 if s > 0 else -1)], 18, uv_fn=lambda az, r, z, arc: SZ['flange'].uv(.5 + .5 * r / .05 * math.sin(math.radians(az)), .5 + .5 * r / .05 * math.cos(math.radians(az))))), T(s * TX, 0, 0))
    # brake caliper on the rear of one tine, wiring on the other
    if s > 0:
        fork.add(box(.030, .05, .06, zone=Z.dark, bevel=.004, center=(s * (TX - .018), -.07, .05)))
    else:
        for i, (y_, z_) in enumerate(((.04, .28), (.046, .18), (.05, .09), (.03, .03))):
            pass
        fork.add(tube(smooth_path([(s * (TX + .017), .03, .30), (s * (TX + .017), .04, .18), (s * (TX + .017), .036, .06), (s * (TX + .02), .012, .02)]), .0045, 5, zone=Z.orange))
# stator shaft: fixed through the rotor (stationary housing, like a hub motor stator)
fork.add(x_axis(cyl(.030, 2 * TX, 12, zone=Z.steel)))
# crown bridge, gusseted
fork.add(box(2 * TX + .03, .085, .026, zone=Z.grey, bevel=.005, center=(0, 0, CROWN_Z)))
for s in (-1, 1):
    fork.add(prism((s * (TX - .002), 0, CROWN_Z - .06), (s * .04, 0, CROWN_Z - .01), .012, .05, up=(0, 1, 0), zone=Z.grey))
fork.add(cyl(.040, .03, 16, zone=Z.white, bevel=.003, center_z=False), T(0, 0, CROWN_Z + .012))
# fender over the tyre: arc about X, front to back, dust control matters on Mars
FR = R + .022


def fender_prof():
    return [(FR - .012, -HW - .022), (FR, -HW - .016), (FR + .004, 0), (FR, HW + .016), (FR - .012, HW + .022)]


fender = lathe(fender_prof(), 20, -75, 75, zone=Z.dark)
# lathe axis Z -> X; the arc centre (az 0 faces -Y) must end up facing +Z (over the tyre)
fork.add(fender, Rx(-90) @ Ry(90))
fender_in = lathe([(p[0] - .004, p[1]) for p in fender_prof()], 20, -75, 75, zone=Z.black, flip=True)
fork.add(fender_in, Rx(-90) @ Ry(90))
# fender stays
for s in (-1, 1):
    for y_ in (-.17, .17):
        fork.add(tube([(s * TX, y_ * .35, CROWN_Z - .12), (s * (HW + .012), y_, math.sqrt(max(FR ** 2 - y_ ** 2, 0)) - .004)], .0048, 5, zone=Z.grey))

# --- king-pin: moves with the suspension, does not steer
king = Geo()
king.add(cyl(.032, Z_NODE - CROWN_Z - .03, 14, zone=Z.steel, center_z=False), T(0, 0, CROWN_Z + .04))
king.add(cyl(.05, .022, 16, zone=Z.grey, bevel=.004, center_z=False), T(0, 0, CROWN_Z + .036))
# swing-arm lug sticking rearward from the collar
king.add(box(.03, .06, .024, zone=Z.grey, bevel=.004, center=(0, -.04, CROWN_Z + .05)))
ARM_TIP = Vector((0, -.052, CROWN_Z + .05))
DAMP_LOW = Vector((0, .05, CROWN_Z + .05))
king.add(box(.024, .05, .024, zone=Z.grey, bevel=.004, center=(0, .03, CROWN_Z + .05)))

# --- base: mount plate, steering motor sleeve, arm clevis, damper lug. Fixed to the rover.
base = Geo()
base_s = Geo()
base.add(box(.22, .24, .014, zone=Z.white, bevel=.003, center=(0, 0, Z_NODE - .007)))
for sx_ in (-1, 1):
    for sy_ in (-1, 1):
        base.add(cyl(.0075, .006, 6, zone=Z.steel, center_z=False), T(sx_ * .09, sy_ * .10, Z_NODE))
base.add(cyl(.052, .075, 18, zone=Z.white, bevel=.005, center_z=False), T(0, 0, Z_NODE - .089))
base.add(cyl(.042, .01, 14, zone=Z.rubber, center_z=False), T(0, 0, Z_NODE - .099))     # dust seal
base_s.add(box(.075, .055, .05, zone=SZ['dark_box'], bevel=.005, center=(.075, 0, Z_NODE - .055)))        # steering motor
base.add(tube(smooth_path([(.11, 0, Z_NODE - .05), (.125, -.03, Z_NODE - .03), (.10, -.09, Z_NODE - .012)]), .005, 5, zone=Z.orange))
PIV = Vector((0, -.205, Z_NODE - .07))
for s in (-1, 1):
    base.add(prism((s * .026, -.205, Z_NODE - .10), (s * .026, -.205, Z_NODE - .013), .012, .05, up=(0, 1, 0), zone=Z.grey))
base.add(x_axis(cyl(.012, .075, 8, zone=Z.steel)), T(PIV.x, PIV.y, PIV.z))
DAMP_UP = Vector((0, .135, Z_NODE - .03))
base.add(box(.03, .04, .03, zone=Z.grey, bevel=.004, center=(0, .135, Z_NODE - .03)))
base.add(prism((0, .06, Z_NODE - .013), (0, .135, Z_NODE - .016), .03, .012, zone=Z.grey))

# --- objects, parenting as in stock roverWheelS2
wc = P.empty('WheelCollider', parent=P.model)
mp = wc.muproperties
mp.collider = 'MU_COL_WHEEL'; mp.radius = R; mp.mass = 1.0; mp.suspensionDistance = 0.0; mp.center = (0, 0, 0); mp.layer = 27
mp.suspensionSpring.spring = 1.0; mp.suspensionSpring.damper = .02; mp.suspensionSpring.targetPosition = .1
mp.forwardFriction.extremumSlip = .4; mp.forwardFriction.extremumValue = 1; mp.forwardFriction.asymptoteSlip = .8; mp.forwardFriction.asymptoteValue = .5; mp.forwardFriction.stiffness = 1
mp.sideFriction.extremumSlip = .2; mp.sideFriction.extremumValue = 1; mp.sideFriction.asymptoteSlip = .5; mp.sideFriction.asymptoteValue = .75; mp.sideFriction.stiffness = 1

o_base = P.mesh('base', base, M_det)
P.mesh('base_motor', base_s, M_sf, parent=o_base)
col = P.hull_collider('base_collider', [(-.11, -.12, Z_NODE), (.11, -.12, Z_NODE), (-.11, .12, Z_NODE), (.11, .12, Z_NODE),
                                        (-.05, -.05, Z_NODE - .1), (.05, -.05, Z_NODE - .1), (-.05, .05, Z_NODE - .1), (.05, .05, Z_NODE - .1)], parent=o_base)
col.muproperties.layer = 26

susp = P.empty('SuspensionPivot', parent=P.model)
steer = P.empty('SteeringPivot', parent=susp)
pivot = P.empty('WheelPivot', parent=steer)
P.mesh('kingpin', king, M_det, parent=susp)
P.mesh('bracket', fork, M_det, parent=steer)
P.mesh('bracket_hub', fork_s, M_sf, parent=steer)
wheel = P.empty('wheel', parent=pivot)
P.mesh('tyre', wire, M_wire, parent=wheel)
P.mesh('rotor', rot, M_det, parent=wheel)
P.mesh('tread', rot_s, M_sf, parent=wheel, smooth_angle=30)
ce = P.empty('collisionEnhancer', parent=wheel)
ce.muproperties.collider = 'MU_COL_SPHERE'; ce.muproperties.radius = R * .72; ce.muproperties.center = (0, 0, 0); ce.muproperties.layer = 26
busted = P.mesh('bustedwheel', crushed, M_wire, parent=pivot)
busted.muproperties.tag = 'Icon_Hidden'
br = P.mesh('bustedrotor', crushed_rot, M_det, parent=busted)
br.muproperties.tag = 'Icon_Hidden'
ce2 = P.empty('collisionEnhancer.001', parent=busted)    # exporter strips .001; ModuleWheelDamage looks up one name
ce2.muproperties.collider = 'MU_COL_SPHERE'; ce2.muproperties.radius = R * .8; ce2.muproperties.center = (0, 0, 0); ce2.muproperties.layer = 26

# --- swing arm and damper: rotators that track the moving hub, driven by FXModuleLookAtConstraint
arm_target = P.empty('armTarget', T(*ARM_TIP), susp)
arm_fr = unity_look_frame(PIV, ARM_TIP)
L = (ARM_TIP - PIV).length
arm = Geo()
for s in (-1, 1):
    arm.add(prism((s * .018, .0, 0), (s * .010, L - .012, 0), .010, .03, up=(0, 0, 1), zone=Z.white))
arm.add(box(.03, .03, .022, zone=Z.white, bevel=.003, center=(0, L - .012, 0)))
arm.add(x_axis(cyl(.016, .056, 10, zone=Z.grey)))
world = Geo(); world.add(arm, arm_fr)
P.mesh('swingArm', world, M_det, frame=arm_fr, parent=o_base)

dmp_fr = unity_look_frame(DAMP_UP, DAMP_LOW)
Ld = (DAMP_LOW - DAMP_UP).length
sl = Geo()
sl.add(tube([(0, 0, 0), (0, Ld * .55, 0)], .017, 10, zone=Z.white))
coil = []
for i in range(40):
    t = i / 39
    a = t * TAU * 5
    coil.append((.025 * math.cos(a), Ld * .05 + t * Ld * .9, .025 * math.sin(a)))
sl.add(tube(coil, .0034, 5, zone=Z.yellow, caps=False))
w2 = Geo(); w2.add(sl, dmp_fr)
P.mesh('damperUpper', w2, M_det, frame=dmp_fr, parent=o_base)
dmp2_fr = unity_look_frame(DAMP_LOW, DAMP_UP)
rd = Geo(); rd.add(tube([(0, 0, 0), (0, Ld * .75, 0)], .008, 8, zone=Z.steel))
w3 = Geo(); w3.add(rd, dmp2_fr)
P.mesh('damperRod', w3, M_det, frame=dmp2_fr, parent=susp)

P.node('top', (0, 0, Z_NODE), (0, 0, 1), 0)
P.export(out)
P.save_blend(out)
