"""Upgraded Cygnus service module: gold MLI 12-gon, recessed aft bay, RCS quads, wing mounts."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
from gr_power import *
from gr_engine import engine, SM as ENGINE
import sm_layout as L

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(11)
rs = np.random.RandomState(12)

P = Part('shab_SM')
M_sm = P.material('shab_sm', spec=(1, .92, .72), shininess=.42, name='sm_gold')
M_dk = P.material('shab_sm', spec=(.8, .8, .8), shininess=.3, name='sm_dark')
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)


def strip_fn(az, r, z, arc):
    return L.strip_uv(az, z)


def vert(az, r):
    a = math.radians(az)
    return Vector((r * math.sin(a), -r * math.cos(a), 0))


A0, A1 = L.A0, L.A0 + 360.0
R = L.R
HB = L.Z_TOP - L.BAND


# ------------------------------------------------------------- ring frames (12-sided)
frames = Geo()
fr_rim = .012
frames.add(lathe([(R - .05, L.Z_BOT), (R - fr_rim, L.Z_BOT), (R, L.Z_BOT + fr_rim * .7), (R, -HB - .004), (R - .018, -HB + .004)], L.NF, A0, A1, uv_fn=strip_fn))
frames.add(lathe([(R - .018, HB - .004), (R, HB + .004), (R, L.Z_TOP - fr_rim * .7), (R - fr_rim, L.Z_TOP)], L.NF, A0, A1, uv_fn=strip_fn))
frames.add(lathe([(R - .03, -L.MID - .002), (R - .004, -L.MID + .003), (R - .004, L.MID - .003), (R - .03, L.MID + .002)], L.NF, A0, A1, uv_fn=strip_fn))

# ------------------------------------------------------------- blanket pillows
blanket = Geo()
for k in range(L.NF):
    az0 = A0 + k * L.FACET; az1 = az0 + L.FACET
    p0, p1 = vert(az0, R - .018), vert(az1, R - .018)
    out_n = (vert((az0 + az1) / 2, 1)).normalized()
    for z0, z1 in ((-HB, -L.MID), (L.MID, HB)):
        nu, nv = 8, 5
        idx = {}
        for j in range(nv + 1):
            t = j / nv
            for i in range(nu + 1):
                s = i / nu
                bump = math.sin(math.pi * s) ** .7 * math.sin(math.pi * t) ** .7
                n = float(rs.normal(0, .0022)) if 0 < i < nu and 0 < j < nv else 0.0
                p = p0.lerp(p1, s) + out_n * (bump * .017 + n)
                z = z0 + (z1 - z0) * t
                idx[(i, j)] = len(blanket.v)
                blanket.v.append((p.x, p.y, z))
        for j in range(nv):
            for i in range(nu):
                s0, s1 = i / nu, (i + 1) / nu
                za, zb = z0 + (z1 - z0) * j / nv, z0 + (z1 - z0) * (j + 1) / nv
                azl, azr = az0 + (az1 - az0) * s0, az0 + (az1 - az0) * s1
                blanket.face([idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]],
                             [L.strip_uv(azl if k or i else A0, za), L.strip_uv(azr, za), L.strip_uv(azr, zb), L.strip_uv(azl if k or i else A0, zb)])

# ------------------------------------------------------------- top deck + interface ring
top = Geo()
top.add(lathe([(R - fr_rim, L.Z_TOP), (.835, L.Z_TOP), (.83, L.Z_TOP + .012), (.815, L.Z_TOP + .018), (.795, L.Z_TOP + .018), (.79, L.Z_TOP + .004), (.70, L.Z_TOP + .002), (.30, L.Z_TOP + .002), (0, L.Z_TOP + .002)], L.NF * 4, A0, A1, uv_fn=lambda az, r, z, arc: L.top_uv(az, r)))

# ------------------------------------------------------------- aft bay
aft = Geo()
rings = [0, .10, .235, .30, .52, .74, L.R_WALL]
aft_prof = [(r_, L.Z_DECK) for r_ in rings]
aft.add(lathe(aft_prof, L.NF * 2, A0, A1, uv_fn=lambda az, r, z, arc: L.aft_uv(az, min(r, .92))))

det = Geo()
# inner wall of the skirt, dark blanket
wall = lathe([(L.R_WALL, L.Z_DECK), (L.R_WALL, L.Z_BOT + .004), (L.R_WALL + .016, L.Z_BOT)], L.NF, A0, A1, zone=Z.mli_black)
det.add(wall)

# thrust structure (the engine's own cone, see the main engine below) and spokes
ENG_Z = L.Z_DECK - .105          # gimbal pivot
eng_mv, eng_st, eng_j = engine(ENGINE)
EF = T(0, 0, ENG_Z)              # engine frame: turbopump toward +X
det.add(eng_st, EF)
for az_ in (0, 90, 180, 270):
    a = math.radians(az_)
    d = Vector((math.sin(a), -math.cos(a), 0))
    t = Vector((d.y, -d.x, 0))
    fr = Matrix((t, d, Vector((0, 0, 1)))).transposed().to_4x4()
    fr.translation = d * .56 + Vector((0, 0, L.Z_DECK - .018))
    det.add(box(.035, .56, .036, zone=Z.grey, bevel=.004), fr)
    det.add(box(.012, .56, .05, zone=Z.dark, bevel=.002), fr @ T(0, 0, .0))

# propellant tanks: domes through the bulkhead, weld rings, polar boss, cable to engine
tank_azs = (45, 135, 225, 315)
TANK_R = .225
for i, az_ in enumerate(tank_azs):
    c = vert(az_, .515) + Vector((0, 0, L.Z_DECK + .012))
    m = T(*c)
    det.add(dome(TANK_R, 28, 8, zone=Z.tank_white if i % 2 else Z.tank_grey), m)
    # weld land and dome stiffener
    det.add(lathe([(TANK_R + .012, L.Z_DECK + .001 - c.z), (TANK_R + .012, L.Z_DECK - .012 - c.z), (TANK_R - .004, L.Z_DECK - .018 - c.z)], 28, zone=Z.bare), m)
    det.add(bolt_ring(TANK_R + .004, 24, br=.004, h=.003, zone=Z.steel), m @ T(0, 0, L.Z_DECK - .016 - c.z) @ Rx(180))
    pole = c + Vector((0, 0, -TANK_R))
    det.add(lathe([(.034, 0.016), (.034, -.012), (.018, -.02), (0, -.02)], 12, zone=Z.steel), T(*pole))
    # feed line from the tank pole in to the engine valves
    inlet = vert(az_ + 20, .13) + Vector((0, 0, L.Z_DECK - .014))
    mid1 = pole + Vector((0, 0, -.018))
    mid2 = vert(az_ + 8, .30) + Vector((0, 0, pole.z - .02))
    det.add(pipe_run([mid1, mid2, vert(az_ + 18, .17) + Vector((0, 0, L.Z_DECK - .05)), inlet], r=.0095, zone=Z.copper if i % 2 else Z.steel))
    # isolation valve on the run
    vpos = mid2 + (vert(az_ + 18, .17) + Vector((0, 0, L.Z_DECK - .05)) - mid2) * .5
    det.add(box(.04, .03, .03, zone=Z.access, bevel=.004, center=tuple(vpos)))

# helium COPVs between the tanks, with regulator stacks and pressurant lines
for i, az_ in enumerate((0, 90, 180, 270)):
    c = vert(az_, .70) + Vector((0, 0, L.Z_DECK + .004))
    m = T(*c)
    det.add(dome(.094, 18, 6, zone=Z.copv), m)
    det.add(cyl(.018, .03, 8, zone=Z.steel, center_z=False), T(c.x, c.y, c.z - .094 - .028))
    reg = vert(az_, .56) + Vector((0, 0, L.Z_DECK - .05))
    det.add(box(.05, .05, .05, zone=Z.white, bevel=.005, center=tuple(reg)))
    pole = c + Vector((0, 0, -.12))
    det.add(pipe_run([pole, reg + Vector((0, 0, -.04)), reg], r=.0045, zone=Z.steel))
    for az2 in (az_ - 45, az_ + 45):
        t0 = vert(az2, .515) + Vector((0, 0, L.Z_DECK - .03))
        det.add(pipe_run([reg + Vector((0, 0, .022)), reg.lerp(t0, .5) + Vector((0, 0, .03)), t0 + Vector((0, 0, -.04)) + vert(az_, -.14)], r=.0035, zone=Z.gold if i % 2 else Z.copper))

# avionics boxes and harness on the deck between structures
for az_, rad_ in ((22, .78), (112, .78), (202, .78), (292, .78), (68, .36), (158, .36), (248, .36), (338, .36)):
    a = vert(az_, rad_)
    m = T(a.x, a.y, L.Z_DECK) @ Rz(-az_) @ Rx(180)
    det.add(junction_box(.11, .08, .03), m)

# ------------------------------------------------------------- side details
RF = R * math.cos(math.radians(15)) + .012     # blanket crown on the facet centre
# corner posts over the facet seams, with stitched-looking cleats
for k in range(L.NF):
    az_ = A0 + k * L.FACET
    p = vert(az_, R + .002)
    a = math.radians(az_)
    d = Vector((math.sin(a), -math.cos(a), 0)); t = Vector((-d.y, d.x, 0))
    m = Matrix((t, Vector((0, 0, 1)), d)).transposed().to_4x4()
    m.translation = p
    det.add(box(.032, 2 * HB - .01, .012, zone=Z.grey, bevel=.003), m)
    for z_ in (-.25, -.12, .12, .25):
        det.add(cyl(.006, .004, 6, zone=Z.steel, center_z=False), m @ T(0, z_, .006))
# wing mounts: bolted fitting, launch latch, and harness pigtail
wing_nodes = {}
for name, az_ in (('wingA', 90), ('wingB', -90)):
    f = on_cyl(az_, 0, RF - .012)
    det.add(box(.27, .27, .05, zone=Z.white, bevel=.006, center=(0, 0, .035)), f)
    det.add(cyl(.085, .022, 20, zone=Z.bare, bevel=.003, center_z=False), f @ T(0, 0, .06))
    det.add(bolt_ring(.072, 10, zone=Z.steel), f @ T(0, 0, .082))
    for sx_, sy_ in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        det.add(cyl(.009, .006, 6, zone=Z.steel, center_z=False), f @ T(sx_ * .115, sy_ * .115, .06))
    det.add(pipe_run([f @ Vector((.10, -.16, .018)), f @ Vector((.10, -.10, .05)), f @ Vector((.06, -.05, .07))], r=.006, zone=Z.black))
    wing_nodes[name] = tuple(f.translation + (f.to_3x3() @ Vector((0, 0, .082))))
# access panels, fill ports and a few tiedown plates
for az_, z_ in ((30, -.19), (-30, -.19), (150, .19), (-150, .19), (0, .19)):
    f = on_cyl(az_, z_, RF - .01)
    det.add(box(.15, .11, .010, zone=Z.access, bevel=.002, center=(0, 0, .005)), f)
    det.add(tube([(-.05, .055, .010), (-.05, .075, .004)], .004, 5, zone=Z.black), f)
    det.add(tube([(.05, .055, .010), (.05, .075, .004)], .004, 5, zone=Z.black), f)
for az_, z_ in ((60, .19), (-60, .19)):
    f = on_cyl(az_, z_, RF - .012)
    det.add(qd_panel(.16, .10), f)
for az_, z_ in ((120, -.19), (-120, -.19), (180, -.19)):
    f = on_cyl(az_, z_, RF - .012)
    det.add(junction_box(.09, .07, .024), f)
    det.add(vent_stub(.010), f @ T(.07, 0, 0))
# handholds on the mid belt
for az_ in (30, 150, -150, -30):
    fr = on_cyl(az_, 0, RF - .006) @ Rz(90)
    det.add(handrail(.26, standoff=.03, bar=.011), fr)

# ------------------------------------------------------------- RCS quads
ZPOD = -.20
thr = P.empty('rcs', parent=P.model)
RPOD = R + .085
for az_ in (45, 135, 225, 315):
    f = on_cyl(az_, ZPOD, RPOD)
    # mount: two struts back to the frame and a backing plate on the corner post
    base = on_cyl(az_, ZPOD, R + .004)
    det.add(box(.11, .17, .012, zone=Z.grey, bevel=.003, center=(0, 0, .006)), base)
    for sy_ in (-1, 1):
        for sx_ in (-1, 1):
            det.add(rod(f @ Vector((sx_ * .022, sy_ * .025, -.02)), base @ Vector((sx_ * .04, sy_ * .07, .01)), r=.0055, sides=6, zone=Z.white))
    # housing with heater blanket
    det.add(box(.085, .10, .068, zone=Z.white, bevel=.006), f)
    det.add(box(.086, .036, .069, zone=Z.mli_gold, bevel=.002), f)
    det.add(box(.018, .018, .01, zone=Z.connector, center=(0, 0, .037)), f)
    # four thrusters: up, down, and both tangents
    for name, loc, d in (('u', (0, .05, 0), (0, 1, 0)), ('d', (0, -.05, 0), (0, -1, 0)), ('l', (-.0425, 0, 0), (-1, 0, 0)), ('r', (.0425, 0, 0), (1, 0, 0))):
        world_o = f @ Vector(loc)
        world_d = f.to_3x3() @ Vector(d)
        nz = frame_axes(world_o, z=world_d, x=(0, 0, 1) if abs(world_d.z) < .9 else (1, 0, 0))
        det.add(nozzle(.023, .052, seg=12), nz)
        det.add(cyl(.012, .008, 8, zone=Z.steel), nz @ T(0, 0, -.003))
        P.empty('RCSthruster', frame_y(world_o + world_d * .02, world_d), thr)

# ------------------------------------------------------------- main engine
# methalox engine family (gr_engine.py), the lander's descent engine at 0.4 with a short nozzle
gim = P.empty('engine_gimbal', T(0, 0, ENG_Z), P.model)
M_eng = P.material('shab_engine', spec=(.9, .9, .9), shininess=.35)
eng = Geo(); eng.add(eng_mv, EF)
P.mesh('engine', eng, M_eng, parent=gim, frame=T(0, 0, ENG_Z), smooth_angle=50)
# exit plane .148 below the pivot; the thrust transform sits just inside it, where it always has
P.empty('thrustTransform', frame_axes((0, 0, ENG_Z - .138), z=(0, 0, -1), x=(1, 0, 0)), gim)
# feeds through the thrust cone to the engine's flex joints
for name in ('lox', 'fuel'):
    j = eng_j[name]
    det.add(tube([EF @ Vector((j.x * 2.6, j.y * 1.6, .100)), EF @ Vector((j.x, j.y, j.z + .02)), EF @ Vector((j.x, j.y, j.z + .006))], .0075, 6,
                 zone=Z.copper if name == 'fuel' else Z.steel, caps=False))

# ------------------------------------------------------------- objects
P.mesh('blanket', blanket, M_sm, smooth_angle=60)
P.mesh('frames', frames, M_dk, smooth_angle=20)
P.mesh('top_deck', top, M_dk, smooth_angle=30)
P.mesh('aft_deck', aft, M_dk, smooth_angle=20)
P.mesh('details', det, M_det, smooth_angle=38)


def ring_pts(r, z, n=L.NF):
    return [vert(A0 + i * 360.0 / n, r) + Vector((0, 0, z)) for i in range(n)]


cols = P.empty('colliders', parent=P.model)
P.hull_collider('col_body', ring_pts(R, L.Z_TOP) + ring_pts(R, L.Z_BOT), parent=cols)
for az_ in (45, 135, 225, 315):
    f = on_cyl(az_, ZPOD, RPOD)
    pts = [f @ Vector((sx_ * .07, sy_ * .08, sz_ * .05)) for sx_ in (-1, 1) for sy_ in (-1, 1) for sz_ in (-1, 1)]
    P.hull_collider(f'col_pod', pts, parent=cols)

P.node('top', (0, 0, L.Z_TOP), (0, 0, 1), 2)
P.node('bottom', (0, 0, L.Z_BOT), (0, 0, -1), 2)
P.node('wingA', wing_nodes['wingA'], (1, 0, 0), 1)
P.node('wingB', wing_nodes['wingB'], (-1, 0, 0), 1)
print('wing nodes', wing_nodes)
P.export(out)
P.save_blend(out)
