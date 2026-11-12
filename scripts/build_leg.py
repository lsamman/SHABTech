"""shab_Leg: folding, telescoping landing leg for the lander's rim nodes. Same transform layout as
Squad's LT-2 (leg > wheelCollider, pistonbase > piston > foot, deployTgt) so the stock wheel modules
drive it. Everything is authored in the deployed pose; frame 0 of legDeploy is the stowed pose.
Part frame: origin on the node at the deck wall, -Y is radially outward, +Z is up the vessel."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
import ll as L
import mech_layout as ML

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(23)
P = Part('shab_Leg')
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)
M_mech = P.material('shab_mech', spec=(.85, .85, .85), shininess=.3)

N = 90                          # clip length: 3 s
F_SWING, F_SLIDE, F_DONE = 60, 15, 72   # finished before TsubSys = 0.83 hands the piston to the suspension

# deck heights in the deck frame, converted to this part's frame (origin at LEG_Z)
Z0 = L.LEG_Z
HINGE = Vector((0, -.22, .55 - Z0))     # r = 2.72, inside the 5.85 m envelope
SOLE_Z = (L.DECK_BOT - L.RIM_H - 1.0) - Z0    # one metre below the stowed HIAD
SUSP = .40; RADIUS = .12
WC_Z = SOLE_Z + RADIUS + SUSP
TILT = math.radians(30)
U = Vector((0, -math.sin(TILT), -math.cos(TILT)))   # strut axis, deployed
STRUT_LEN = (HINGE.z - WC_Z) / math.cos(TILT)
KNEE = HINGE + U * STRUT_LEN
OUTER_LEN = .95
INNER_LEN = .93
STEP = (STRUT_LEN - INNER_LEN) / 3.0
Q_STOW = Quaternion((1, 0, 0), TILT)    # +30 deg about X swings the deployed strut to vertical
print(f'strut length {STRUT_LEN:.3f}, knee y={KNEE.y:.3f} z={KNEE.z:.3f}, wheelCollider z={WC_Z:.3f}, sole z={SOLE_Z:.3f}, foot radius from axis {2.5 - KNEE.y:.3f}')


def along(p0, length, r, zone, sides=12, r2=None):
    """Tube from p0 along U."""
    return tube([p0, p0 + U * length], r, sides, zone=zone)


leg = P.empty('leg', parent=P.model)

# ---- rim bracket: fixed to the deck
brk = Geo()
plate = T(0, -.006, 0) @ Rx(90)
brk.add(box(.52, .78, .02, zone=Z.white, bevel=.004, center=(0, .05, 0)), plate)
for sx_ in (-1, 1):
    for sz_ in (-.30, 0.0, .40):
        brk.add(cyl(.012, .012, 6, zone=Z.steel, center_z=False), T(sx_ * .23, -.016, sz_) @ Rx(90))
    # clevis arms reaching out to the hinge
    brk.add(box(.018, .24, .11, zone=Z.white, bevel=.004, center=(sx_ * .085, -.12, HINGE.z)))
    brk.add(cyl(.05, .018, 12, zone=Z.grey, center_z=True), T(sx_ * .085, HINGE.y, HINGE.z) @ Ry(90))
    # gusset from the wall to the top of each clevis arm, bolted doubler under the hinge bosses
    brk.add(box(.014, .10, .16, zone=Z.white, bevel=.003, center=(sx_ * .085, -.06, HINGE.z + .12)))
    brk.add(cyl(.032, .006, 12, zone=Z.grey, center_z=True), T(sx_ * .097, HINGE.y, HINGE.z) @ Ry(90))
    for k in range(6):
        a = math.radians(30 + 60 * k)
        brk.add(cyl(.0055, .004, 6, zone=Z.steel, center_z=False), T(sx_ * .1, HINGE.y + .022 * math.cos(a), HINGE.z + .022 * math.sin(a)) @ Ry(90 * sx_))
brk.add(tube([(-.085, HINGE.y, HINGE.z), (.085, HINGE.y, HINGE.z)], .018, 10, zone=Z.steel))
# deploy actuator anchor: clevis on the wall above the hinge
ACT_A = Vector((0, -.035, .43))
for sx_ in (-1, 1):
    brk.add(box(.010, .05, .05, zone=Z.white, bevel=.002, center=(sx_ * .03, -.025, ACT_A.z)))
brk.add(tube([ACT_A + Vector((-.038, 0, 0)), ACT_A + Vector((.038, 0, 0))], .008, 8, zone=Z.steel))
# harness: connector box on the wall plate, one lead to the actuator motor, one down past the hinge
brk.add(junction_box(.07, .06, .022), T(.16, -.016, .30) @ Rx(90))
brk.add(tube([(.16, -.03, .332), (.16, -.03, .40), (.10, -.03, .45), (.045, -.03, .45)], .0045, 6, zone=Z.black))
brk.add(tube([(.16, -.03, .268), (.16, -.03, .20), (.13, -.03, .12), (.13, -.03, .0)], .0045, 6, zone=Z.black))
for z_ in (.37, .16, .06):
    brk.add(box(.016, .012, .01, zone=Z.grey, center=(.16 if z_ > .3 else (.145 if z_ > .1 else .13), -.022, z_)))
LUGS = [Vector((sx_ * .24, -.05, -.30)) for sx_ in (-1, 1)]
for p in LUGS:
    brk.add(box(.05, .09, .07, zone=Z.white, bevel=.005, center=tuple(p + Vector((0, .018, 0)))))
    brk.add(tube([p + Vector((-.034, 0, 0)), p + Vector((.034, 0, 0))], .009, 8, zone=Z.steel))
P.mesh('bracket', brk, M_det, parent=leg)

# ---- wheel collider: at the piston's unloaded position, aligned with the part (axis = vessel up)
wc = P.empty('wheelCollider', T(KNEE.x, KNEE.y, KNEE.z), leg)
wc.muproperties.layer = 27     # stock LT-2: WheelColliders layer, ignores layer 26 below

# ---- telescoping strut: four nested tubes
s1 = Geo()
STRUT_Z = Zone(*ML.STRUT, atlas=ML.ATLAS, ppm=(ML.STRUT[3] - 2) / OUTER_LEN)
sleeve = along(HINGE, OUTER_LEN, .062, STRUT_Z, 20)
W_ = Vector((0, math.cos(TILT), -math.sin(TILT)))        # across the strut, toward the deck wall
# gland nut and wiper at the sleeve's open end, trunnion block at the hinge
s1.add(tube([HINGE + U * (OUTER_LEN - .04), HINGE + U * (OUTER_LEN + .004)], .069, 16, zone=Z.grey))
s1.add(tube([HINGE + U * (OUTER_LEN + .004), HINGE + U * (OUTER_LEN + .012)], .057, 16, zone=Z.rubber))
s1.add(box(.09, .08, .07, zone=Z.white, bevel=.008), frame_axes(HINGE + U * .02, U, x=Vector((1, 0, 0))))
# lug the deploy actuator pushes on
ACT_D, ACT_OFF = .24, .075
lugc = HINGE + U * ACT_D + W_ * (ACT_OFF - .02)
s1.add(box(.05, .045, .06, zone=Z.white, bevel=.004), frame_axes(lugc, U, x=Vector((1, 0, 0))))
s1.add(tube([HINGE + U * ACT_D + W_ * ACT_OFF + Vector((-.03, 0, 0)), HINGE + U * ACT_D + W_ * ACT_OFF + Vector((.03, 0, 0))], .008, 8, zone=Z.steel))
for sx_ in (-1, 1):
    s1.add(box(.008, .03, .028, zone=Z.white, bevel=.002), frame_axes(HINGE + U * ACT_D + W_ * ACT_OFF + Vector((sx_ * .024, 0, 0)), U, x=Vector((1, 0, 0))))
s1.add(tube([HINGE + Vector((-.06, 0, 0)), HINGE + Vector((.06, 0, 0))], .04, 12, zone=Z.grey))
# collar for the V-braces, band clamps, a conduit along the tube
COLLAR_D = .55
s1.add(tube([HINGE + U * (COLLAR_D - .035), HINGE + U * (COLLAR_D + .035)], .074, 16, zone=Z.grey))
for sx_ in (-1, 1):
    s1.add(tube([HINGE + U * COLLAR_D + Vector((sx_ * .07, 0, 0)), HINGE + U * COLLAR_D + Vector((sx_ * .092, 0, 0))], .02, 10, zone=Z.grey))
    s1.add(bolt_ring(.062, 6, br=.004, h=.003, zone=Z.steel), frame_axes(HINGE + U * (COLLAR_D + .035), U))
for d in (.2, .85):
    s1.add(tube([HINGE + U * (d - .012), HINGE + U * (d + .012)], .068, 16, zone=Z.steel))
off = Vector((.0, -math.cos(TILT), math.sin(TILT))) * .074
s1.add(tube([HINGE + U * .1 + off, HINGE + U * .9 + off], .010, 6, zone=Z.black))
base_fr = T(HINGE.x, HINGE.y, HINGE.z)
pb = P.mesh('pistonbase', s1, M_det, parent=leg, frame=base_fr)
P.mesh('sleeve', sleeve, M_mech, parent=pb, frame=base_fr, smooth_angle=50)

sections = []
parent = pb
radii = (.052, .043, .034)
for k, r in enumerate(radii):
    d0 = STEP * (k + 1)
    p0 = HINGE + U * d0                     # section origin when deployed
    g = Geo()
    g.add(along(p0, INNER_LEN, r, Z.bare if k < 2 else Z.steel, 14))
    g.add(tube([p0 + U * (INNER_LEN - .01 if k < 2 else .0), p0 + U * (INNER_LEN + .01 if k < 2 else .02)], r + .010, 14, zone=Z.grey))
    if k == 2:
        # elbow at the knee: end caps of the crush cartridge (its housing is on the mech sheet, below)
        g.add(lathe([(.044, .135), (.071, .135), (.071, .10), (.066, .095)], 20, zone=Z.grey), T(KNEE.x, KNEE.y, KNEE.z))
        g.add(lathe([(.066, -.135), (.071, -.14), (.071, -.16), (.050, -.165), (.046, -.165)], 20, zone=Z.grey), T(KNEE.x, KNEE.y, KNEE.z))
        g.add(lathe([(.047, -.165), (.047, -.172), (.03, -.175)], 16, zone=Z.rubber), T(KNEE.x, KNEE.y, KNEE.z))
        g.add(bolt_ring(.064, 10, br=.0045, h=.003, zone=Z.steel), T(KNEE.x, KNEE.y, KNEE.z + .135))
        g.add(box(.06, .10, .06, zone=Z.white, bevel=.008, center=tuple(KNEE + Vector((0, .07, .08)))))
        # crush-stroke indicator: a pointer on the cap reading a scale on the housing
        g.add(box(.012, .02, .008, zone=Z.red, bevel=.001, center=tuple(KNEE + Vector((0, -.078, .132)))))
    o = P.mesh(f'strut{k + 2}', g, M_det, parent=parent, frame=T(p0.x, p0.y, p0.z))
    if k == 2:
        CART_Z = Zone(*ML.CART, atlas=ML.ATLAS, ppm=(ML.CART[3] - 2) / .235)
        P.mesh('cartridge', tube([KNEE + Vector((0, 0, -.135)), KNEE + Vector((0, 0, .10))], .066, 20, zone=CART_Z, caps=False), M_mech,
               parent=o, frame=T(p0.x, p0.y, p0.z), smooth_angle=50)
    rest = o.location.copy()
    # nested inside its parent when stowed
    stow_loc = rest - U * STEP
    P.key('legDeploy', o, 0, location=stow_loc)
    P.key('legDeploy', o, F_SLIDE, location=stow_loc)
    P.key('legDeploy', o, F_DONE, location=rest)
    P.key('legDeploy', o, N, location=rest)
    sections.append(o)
    parent = o

P.key('legDeploy', pb, 0, rotation_quaternion=Q_STOW)
P.key('legDeploy', pb, F_SWING, rotation_quaternion=Quaternion())
P.key('legDeploy', pb, N, rotation_quaternion=Quaternion())

# target the wheel module moves the piston to while (un)folding, as on the stock leg
P.empty('deployTgt', T(KNEE.x, KNEE.y, KNEE.z), pb)

# ---- piston: suspension slides this; rod and footpad hang below
pist_g = Geo()
pist_g.add(tube([KNEE + Vector((0, 0, .02)), KNEE + Vector((0, 0, -.06))], .044, 12, zone=Z.grey))
pi = P.mesh('piston', pist_g, M_det, parent=pb, frame=T(KNEE.x, KNEE.y, KNEE.z))
loc_dep = pi.location.copy()
loc_stow = (HINGE + U * OUTER_LEN) - HINGE    # relative to pistonbase, at the nested tube tip
Q_PST = Quaternion((1, 0, 0), -TILT)    # keeps the rod and pad vertical while stowed
P.key('legDeploy', pi, 0, location=loc_stow, rotation_quaternion=Q_PST)
P.key('legDeploy', pi, F_SLIDE, location=loc_stow, rotation_quaternion=Q_PST)
P.key('legDeploy', pi, F_DONE, location=loc_dep, rotation_quaternion=Quaternion())
P.key('legDeploy', pi, N, location=loc_dep, rotation_quaternion=Quaternion())

# ---- foot: pivots freely under the piston (ModuleWheelBogey)
FOOT_C = KNEE + Vector((0, 0, -SUSP))
ft = Geo()
# rod runs from the foot's ball joint up inside the sleeve
ft.add(tube([FOOT_C + Vector((0, 0, .03)), FOOT_C + Vector((0, 0, SUSP + .10))], .026, 12, zone=Z.bare))
PAD_R = .20
pad_prof = [(0, -RADIUS), (PAD_R - .05, -RADIUS), (PAD_R - .02, -RADIUS + .02), (PAD_R, -RADIUS + .05), (PAD_R, -RADIUS + .09), (PAD_R - .03, -RADIUS + .11), (.07, -.01), (.04, .02), (.026, .03)]
# pad shell on the mech sheet: sole and rim plain, top polar-mapped (tread annulus, bolt circles)
pad = Geo()
pad.add(lathe([(r, z + FOOT_C.z) for r, z in pad_prof[:5]], 32, uv_fn=lambda az, r, z, arc: ML.polar_uv(ML.SOLE, az, r, ML.PAD_RMAX)), T(FOOT_C.x, FOOT_C.y, 0))
pad.add(lathe([(r, z + FOOT_C.z) for r, z in pad_prof[4:]], 32, uv_fn=lambda az, r, z, arc: ML.polar_uv(ML.PADTOP, az, r, ML.PAD_RMAX)), T(FOOT_C.x, FOOT_C.y, 0))
# ball-joint flange
ft.add(lathe([(.066, -.008), (.066, .0), (.05, .007)], 24, zone=Z.grey), T(FOOT_C.x, FOOT_C.y, FOOT_C.z))
ft.add(bolt_ring(.058, 12, br=.0042, h=.003, zone=Z.steel), T(FOOT_C.x, FOOT_C.y, FOOT_C.z + .002))
# touchdown sensor: probe sprung down to the sole line, switch box on the rim, lead up to the ball joint
SN = T(FOOT_C.x, FOOT_C.y, FOOT_C.z)
ft.add(box(.045, .03, .028, zone=Z.white, bevel=.004, center=(0, -.183, -.004)), SN)
ft.add(box(.02, .03, .008, zone=Z.grey, bevel=.002, center=(0, -.205, -.006)), SN)
ft.add(tube([(0, -.214, -.006), (0, -.214, -RADIUS + .014)], .0045, 8, zone=Z.bare), SN)
ft.add(tube([(0, -.214, -.03), (0, -.214, -.07)], .0075, 8, zone=Z.yellow), SN)
ft.add(cyl(.013, .005, 12, zone=Z.black, bevel=.0015, center_z=False), SN @ T(0, -.214, -RADIUS + .009))
ft.add(tube([(0, -.17, .006), (0, -.12, .0), (0, -.075, .006), (0, -.056, .03)], .004, 5, zone=Z.black), SN)
ft.add(box(.03, .02, .006, zone=Z.red, center=(0, -.183, .0115)), SN)
# crushable honeycomb ring and eight radial stiffeners
ft.add(lathe([(PAD_R + .004, FOOT_C.z - RADIUS + .05), (PAD_R + .004, FOOT_C.z - RADIUS + .085)], 24, zone=Z.hex), T(FOOT_C.x, FOOT_C.y, 0))
for k in range(8):
    a = k * 45.0 + 22.5
    ft.add(box(.010, .10, .03, zone=Z.white, bevel=.002, center=(0, .115, .002)), T(FOOT_C.x, FOOT_C.y, FOOT_C.z) @ Rz(a))
ft.add(tube([FOOT_C + Vector((0, 0, .0)), FOOT_C + Vector((0, 0, .05))], .05, 12, zone=Z.grey))
foot_fr = T(FOOT_C.x, FOOT_C.y, FOOT_C.z)
fo = P.mesh('foot', ft, M_det, parent=pi, frame=foot_fr)
P.mesh('foot_pad', pad, M_mech, parent=fo, frame=foot_fr, smooth_angle=40)
floc_dep = fo.location.copy()
floc_stow = Vector((0, 0, -.12))
P.key('legDeploy', fo, 0, location=floc_stow)
P.key('legDeploy', fo, F_SLIDE, location=floc_stow)
P.key('legDeploy', fo, F_DONE, location=floc_dep)
P.key('legDeploy', fo, N, location=floc_dep)

# ---- V-braces: sleeve pivots on the wall lug, rod pivots on the strut collar. Keyed at three points.
def collar_at(deg):
    """Collar position at hinge angle deg (0 = deployed, 30 = stowed), side offset applied by the caller."""
    q = Quaternion((1, 0, 0), math.radians(deg))
    return HINGE + q @ (U * COLLAR_D)


BR = .23     # three-stage telescoping brace: lug sleeve, sliding middle tube, collar rod (stowed span .238 m, deployed .481 m)
for side, lug in zip((-1, 1), LUGS):
    side_off = Vector((side * .074, 0, 0))
    # sleeve on the lug
    keysA = []; keysB = []
    for f, deg in ((0, 30), (F_SWING // 2, 15), (F_SWING, 0), (N, 0)):
        c = collar_at(deg) + side_off
        d = (c - lug).normalized()
        keysA.append((f, lug.copy(), d))
        keysB.append((f, c.copy(), -d))
    d0 = keysA[-1][2]
    frA = frame_axes(lug, d0)
    ga = Geo()
    ga.add(tube([Vector((0, 0, .02)), Vector((0, 0, BR))], .026, 12, zone=Z.white))
    ga.add(tube([Vector((0, 0, BR - .035)), Vector((0, 0, BR + .004))], .031, 12, zone=Z.grey))
    ga.add(tube([Vector((0, 0, BR + .004)), Vector((0, 0, BR + .01))], .02, 10, zone=Z.rubber))
    ga.add(tube([Vector((0, 0, .008)), Vector((0, 0, .03))], .02, 10, zone=Z.grey))
    ga.add(cyl(.021, .05, 12, zone=Z.grey, bevel=.003), Ry(90))
    ga.add(box(.03, .01, .012, zone=Z.yellow, bevel=.001, center=(0, .028, BR * .55)))
    oa = P.mesh(f'braceSleeve{"LR"[side > 0]}', Geo().add(ga, frA), M_det, parent=leg, frame=frA)
    c0 = keysB[-1][1]; dB = keysB[-1][2]
    frB = frame_axes(c0, dB)
    gb = Geo()
    gb.add(tube([Vector((0, 0, .01)), Vector((0, 0, BR))], .016, 10, zone=Z.bare))
    gb.add(tube([Vector((0, 0, .012)), Vector((0, 0, .04))], .021, 6, zone=Z.grey))
    gb.add(cyl(.017, .03, 12, zone=Z.grey, bevel=.002), Ry(90))
    ob = P.mesh(f'braceRod{"LR"[side > 0]}', Geo().add(gb, frB), M_det, parent=leg, frame=frB)
    gm = Geo()
    gm.add(tube([Vector((0, 0, 0)), Vector((0, 0, BR))], .0205, 10, zone=Z.white))
    gm.add(tube([Vector((0, 0, BR - .02)), Vector((0, 0, BR + .003))], .0245, 10, zone=Z.grey))
    gm.add(tube([Vector((0, 0, BR + .003)), Vector((0, 0, BR + .008))], .0175, 8, zone=Z.rubber))
    ln = (keysB[-1][1] - lug).length
    frM = frame_axes(lug + d0 * (ln - BR) / 2, d0)
    om = P.mesh(f'braceMid{"LR"[side > 0]}', Geo().add(gm, frM), M_det, parent=leg, frame=frM)
    ref = Vector((1, 0, 0))
    for (f, l_, d_), (fb, c_, db) in zip(keysA, keysB):
        fa_ = frame_axes(l_, d_, x=ref).to_quaternion()
        fb_ = frame_axes(c_, db, x=ref).to_quaternion()
        ln = (c_ - l_).length
        P.key('legDeploy', oa, f, rotation_quaternion=fa_, location=l_)
        P.key('legDeploy', ob, f, rotation_quaternion=fb_, location=c_)
        P.key('legDeploy', om, f, rotation_quaternion=fa_, location=l_ + d_ * (ln - BR) / 2)

# ---- deploy actuator: electromechanical ram from the wall clevis to the sleeve lug, aimed like the braces
def act_lug(deg):
    return HINGE + Quaternion((1, 0, 0), math.radians(deg)) @ (U * ACT_D + W_ * ACT_OFF)


ACT_BODY, ACT_ROD = .30, .25
akeys = []
for f in (0, 10, 20, 30, 40, 50, F_SWING, N):
    t_ = min(1.0, f / F_SWING)
    deg = 30 * (1 - t_ * t_ * (3 - 2 * t_))
    L_ = act_lug(deg)
    akeys.append((f, L_, (L_ - ACT_A).normalized()))
print('actuator length stowed %.3f deployed %.3f' % ((akeys[0][1] - ACT_A).length, (akeys[-1][1] - ACT_A).length))
dA = akeys[-1][2]
frC = frame_axes(ACT_A, dA, x=Vector((1, 0, 0)))
gc = Geo()
gc.add(cyl(.016, .046, 12, zone=Z.grey, bevel=.002), Ry(90))
gc.add(tube([Vector((0, 0, .012)), Vector((0, 0, ACT_BODY))], .022, 14, zone=Z.white))
gc.add(tube([Vector((0, 0, .02)), Vector((0, 0, .06))], .026, 14, zone=Z.grey))
gc.add(tube([Vector((0, 0, ACT_BODY - .03)), Vector((0, 0, ACT_BODY + .004))], .026, 14, zone=Z.grey))
gc.add(tube([Vector((0, 0, ACT_BODY + .004)), Vector((0, 0, ACT_BODY + .009))], .016, 10, zone=Z.rubber))
# motor and gearbox alongside, outboard of the ram
gc.add(box(.036, .05, .05, zone=Z.white, bevel=.004, center=(0, .03, .05)))
gc.add(tube([Vector((0, .042, .075)), Vector((0, .042, .20))], .017, 12, zone=Z.dark))
gc.add(tube([Vector((0, .042, .20)), Vector((0, .042, .21))], .012, 10, zone=Z.grey))
gc.add(box(.02, .012, .03, zone=Z.connector, bevel=.002, center=(0, .062, .15)))
oc = P.mesh('actuatorBody', Geo().add(gc, frC), M_det, parent=leg, frame=frC)
frR = frame_axes(akeys[-1][1], -dA, x=Vector((1, 0, 0)))
gr = Geo()
gr.add(cyl(.0135, .034, 12, zone=Z.grey, bevel=.002), Ry(90))
gr.add(tube([Vector((0, 0, .01)), Vector((0, 0, ACT_ROD))], .012, 12, zone=Z.bare))
gr.add(tube([Vector((0, 0, .012)), Vector((0, 0, .032))], .016, 6, zone=Z.grey))
orr = P.mesh('actuatorRod', Geo().add(gr, frR), M_det, parent=leg, frame=frR)
for f, L_, d_ in akeys:
    P.key('legDeploy', oc, f, rotation_quaternion=frame_axes(ACT_A, d_, x=Vector((1, 0, 0))).to_quaternion(), location=ACT_A.copy())
    P.key('legDeploy', orr, f, rotation_quaternion=frame_axes(L_, -d_, x=Vector((1, 0, 0))).to_quaternion(), location=L_.copy())

# ---- colliders: capsules like the stock leg
col = P.empty('pistonbaseCollider', frame_axes(HINGE + U * (OUTER_LEN / 2), -U), pb)
mp = col.muproperties; mp.collider = 'MU_COL_CAPSULE'; mp.isTrigger = False; mp.radius = .07; mp.height = OUTER_LEN; mp.direction = 'MU_Z'; mp.center = (0, 0, 0); mp.layer = 26
col2 = P.empty('col_strut', frame_axes(HINGE + U * (STEP * 3 + INNER_LEN / 2), -U), sections[-1])
mp = col2.muproperties; mp.collider = 'MU_COL_CAPSULE'; mp.isTrigger = False; mp.radius = .05; mp.height = INNER_LEN; mp.direction = 'MU_Z'; mp.center = (0, 0, 0); mp.layer = 26
col3 = P.empty('piston_collider', T(KNEE.x, KNEE.y, KNEE.z), pi)
mp = col3.muproperties; mp.collider = 'MU_COL_CAPSULE'; mp.isTrigger = False; mp.radius = .06; mp.height = SUSP + .05; mp.direction = 'MU_Z'; mp.center = (0, 0, -SUSP / 2); mp.layer = 26
# ground plate collider on the bracket so a kerbal can't walk through it
P.hull_collider('col_bracket', [Vector(p) for p in ((-.26, 0, -.34), (.26, 0, -.34), (-.26, 0, .44), (.26, 0, .44), (-.26, -.05, -.34), (.26, -.05, -.34), (-.26, -.05, .44), (.26, -.05, .44))], parent=leg)

P.node('top', (0, 0, 0), (0, 1, 0), 1)
P.bake_clips(0)
P.export(out)
P.save_blend(out)
print('GROUND offset (origin to sole)', round(-SOLE_Z, 3), 'wheel collider local', tuple(round(v, 3) for v in (KNEE.x, KNEE.z, KNEE.y)))
