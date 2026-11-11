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

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(23)
P = Part('shab_Leg')
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)
M_deck = P.material('shab_lander')

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
brk.add(tube([(-.085, HINGE.y, HINGE.z), (.085, HINGE.y, HINGE.z)], .018, 10, zone=Z.steel))
# stiffening web above the clevis and lower brace lugs
brk.add(box(.20, .10, .025, zone=Z.white, bevel=.003, center=(0, -.06, HINGE.z + .07)))
LUGS = [Vector((sx_ * .24, -.05, -.30)) for sx_ in (-1, 1)]
for p in LUGS:
    brk.add(box(.05, .09, .07, zone=Z.white, bevel=.005, center=tuple(p + Vector((0, .018, 0)))))
P.mesh('bracket', brk, M_det, parent=leg)

# ---- wheel collider: at the piston's unloaded position, aligned with the part (axis = vessel up)
wc = P.empty('wheelCollider', T(KNEE.x, KNEE.y, KNEE.z), leg)
wc.muproperties.layer = 27     # stock LT-2: WheelColliders layer, ignores layer 26 below

# ---- telescoping strut: four nested tubes
s1 = Geo()
s1.add(along(HINGE, OUTER_LEN, .062, Z.white, 16))
s1.add(tube([HINGE + Vector((-.06, 0, 0)), HINGE + Vector((.06, 0, 0))], .04, 12, zone=Z.grey))
# collar for the V-braces, band clamps, a conduit along the tube
COLLAR_D = .55
s1.add(tube([HINGE + U * (COLLAR_D - .035), HINGE + U * (COLLAR_D + .035)], .074, 16, zone=Z.grey))
for d in (.2, .85):
    s1.add(tube([HINGE + U * (d - .012), HINGE + U * (d + .012)], .068, 16, zone=Z.steel))
off = Vector((.0, -math.cos(TILT), math.sin(TILT))) * .074
s1.add(tube([HINGE + U * .1 + off, HINGE + U * .9 + off], .010, 6, zone=Z.black))
base_fr = T(HINGE.x, HINGE.y, HINGE.z)
pb = P.mesh('pistonbase', s1, M_det, parent=leg, frame=base_fr)

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
        # elbow at the knee: vertical sleeve for the shock absorber
        g.add(tube([KNEE + Vector((0, 0, .10)), KNEE + Vector((0, 0, -.13))], .054, 14, zone=Z.white))
        g.add(tube([KNEE + Vector((0, 0, -.125)), KNEE + Vector((0, 0, -.145))], .060, 14, zone=Z.grey))
        g.add(box(.05, .10, .05, zone=Z.white, bevel=.006, center=tuple(KNEE + Vector((0, .05, .04)))))
    o = P.mesh(f'strut{k + 2}', g, M_det, parent=parent, frame=T(p0.x, p0.y, p0.z))
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
ft.add(lathe([(r, z + FOOT_C.z) for r, z in pad_prof], 24, zone=Z.lander_panel), T(FOOT_C.x, FOOT_C.y, 0))
# crushable honeycomb ring and eight radial stiffeners
ft.add(lathe([(PAD_R + .004, FOOT_C.z - RADIUS + .05), (PAD_R + .004, FOOT_C.z - RADIUS + .085)], 24, zone=Z.hex), T(FOOT_C.x, FOOT_C.y, 0))
for k in range(8):
    a = k * 45.0
    ft.add(box(.012, .13, .05, zone=Z.white, bevel=.002, center=(0, .10, -RADIUS + .12)), T(FOOT_C.x, FOOT_C.y, FOOT_C.z) @ Rz(a))
ft.add(tube([FOOT_C + Vector((0, 0, .0)), FOOT_C + Vector((0, 0, .05))], .05, 12, zone=Z.grey))
foot_fr = T(FOOT_C.x, FOOT_C.y, FOOT_C.z)
fo = P.mesh('foot', ft, M_det, parent=pi, frame=foot_fr)
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


BR = .36
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
    ga.add(tube([Vector((0, 0, 0)), Vector((0, 0, BR))], .024, 10, zone=Z.white))
    ga.add(tube([Vector((0, 0, -.015)), Vector((0, 0, .025))], .032, 10, zone=Z.grey))
    oa = P.mesh(f'braceSleeve{"LR"[side > 0]}', Geo().add(ga, frA), M_det, parent=leg, frame=frA)
    c0 = keysB[-1][1]; dB = keysB[-1][2]
    frB = frame_axes(c0, dB)
    gb = Geo()
    gb.add(tube([Vector((0, 0, 0)), Vector((0, 0, BR + .12))], .014, 8, zone=Z.bare))
    gb.add(tube([Vector((0, 0, -.015)), Vector((0, 0, .025))], .024, 8, zone=Z.grey))
    ob = P.mesh(f'braceRod{"LR"[side > 0]}', Geo().add(gb, frB), M_det, parent=leg, frame=frB)
    ref = Vector((1, 0, 0))
    for (f, l_, d_), (fb, c_, db) in zip(keysA, keysB):
        fa_ = frame_axes(l_, d_, x=ref).to_quaternion()
        fb_ = frame_axes(c_, db, x=ref).to_quaternion()
        P.key('legDeploy', oa, f, rotation_quaternion=fa_, location=l_)
        P.key('legDeploy', ob, f, rotation_quaternion=fb_, location=c_)

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
