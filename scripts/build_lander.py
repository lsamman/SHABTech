"""shab_Lander: Mars lander deck (Friz concept): PCM mount, walkway, tanks, 8 CH4/LOX engines."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
from gr_lander import *
from gr_engine import engine, LANDER as ENGINE
import ll as L

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(11)

P = Part('shab_Lander')
M_deck = P.material('shab_lander')
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)


def top_uv(az, r, z, arc):
    return L.polar_uv(L.TOP, az, r, L.TOP_RMAX)


def under_uv(az, r, z, arc):
    return L.polar_uv(L.UNDER, az, r, L.UNDER_RMAX)


# ---- wall: six sectors, one trim sector, frames in the profile
wall = Geo()
fr = .022
prof = [(2.44, L.DECK_BOT), (2.50 + fr - .004, L.DECK_BOT + .004), (2.50 + fr, L.DECK_BOT + .008), (2.50 + fr, L.DECK_BOT + .045), (2.50, L.DECK_BOT + .052),
        (2.50, -.02), (2.50 + fr * .8, -.012), (2.50 + fr * .8, .052), (2.50, .06),
        (2.50, L.DECK_TOP - .052), (2.50 + fr, L.DECK_TOP - .045), (2.50 + fr, L.DECK_TOP - .008), (2.50 + fr - .006, L.DECK_TOP)]
for k in range(6):
    a0, a1 = k * 60, (k + 1) * 60

    def wall_uv(az, r, z, arc, a0=a0):
        return L.rect_uv(L.SIDE, (az - a0) / 60.0, (z - L.DECK_BOT) / (L.DECK_TOP - L.DECK_BOT))
    wall.add(lathe(prof, 24, a0, a1, uv_fn=wall_uv))
    # longerons on the sector's quarter points

    def lg_uv(az, z, a0=a0):
        return L.rect_uv(L.SIDE, (az - a0) / 60.0, (z - L.DECK_BOT) / (L.DECK_TOP - L.DECK_BOT))
    for s in (.25, .75):
        azc = a0 + s * 60
        wall.add(curved_panel(2.50, azc - .9, azc + .9, L.DECK_BOT + .05, L.DECK_TOP - .05, raise_=.014, chamfer=.004, seg=1, uv_fn=lg_uv))
# ---- deck top and underside
top = lathe([(2.50 + fr - .006, L.DECK_TOP), (2.46, L.DECK_TOP), (2.2, L.DECK_TOP), (1.7, L.DECK_TOP), (1.2, L.DECK_TOP), (.9, L.DECK_TOP), (0, L.DECK_TOP)], 96, -180, 180, uv_fn=top_uv)
under = lathe([(0, L.DECK_BOT), (.8, L.DECK_BOT), (1.65, L.DECK_BOT), (2.44, L.DECK_BOT)], 72, -180, 180, uv_fn=under_uv)


# ---- PCM mount ring
def plate_uv(az, r, z, arc):
    return L.rect_uv(L.PLATE, ((az + 180) / 360) % 1, (arc * 3) % 1)


mount = lathe([(.905, L.DECK_TOP), (.905, L.DECK_TOP + .012), (.885, L.DECK_TOP + .02), (.862, L.MOUNT_Z - .004), (.856, L.MOUNT_Z), (.70, L.MOUNT_Z), (0, L.MOUNT_Z)], 64, -180, 180, uv_fn=plate_uv)

det = Geo()
for k in range(24):
    az = 7.5 + 15 * k
    if abs((az + 180) % 360 - 180) < 12:   # clear the ladder landing
        continue
    a = math.radians(az)
    fr_ = frame_axes((.885 * math.sin(a), -.885 * math.cos(a), L.DECK_TOP), (0, 0, 1), x=(math.cos(a), math.sin(a), 0))
    det.add(gusset(.29, .055, .012, Z.white), fr_ @ Rz(180))
det.add(bolt_ring(.885, 48, zone=Z.steel), T(0, 0, L.DECK_TOP + .012))

# ---- ladder landing below the PCM's fixed ladder: grating at PCM-floor height with short steps
LDG_Z = L.MOUNT_Z - .004
landing = T(0, -(1.06), LDG_Z)
det.add(box(.52, .50, .012, zone=Z.grating, center=(0, 0, -.006)), landing)
for sx_ in (-1, 1):
    for sy_ in (-1, 1):
        det.add(box(.022, .022, LDG_Z - L.DECK_TOP, zone=Z.grey, center=(sx_ * .24, sy_ * .23, -(LDG_Z - L.DECK_TOP) / 2 - .002)), landing)
    # hand-hold posts either side of the ladder foot
    det.add(tube([(sx_ * .26, .02, 0), (sx_ * .26, .02, .36), (sx_ * .26, -.20, .36), (sx_ * .26, -.24, .05)], .011, 6, zone=Z.yellow), landing)
# step down to the walkway
det.add(box(.40, .12, .025, zone=Z.grating, center=(0, -.31, -.04)), landing)

# ---- walkway rails at the outer edge of the tread plate, open at the ladder
rail_r = 1.70
N_POST = 24
post = stanchion(.40)
for k in range(N_POST):
    az = 15 * k + 7.5
    if abs((az + 180) % 360 - 180) < 16:
        continue
    a = math.radians(az)
    det.add(post, T(rail_r * math.sin(a), -rail_r * math.cos(a), L.DECK_TOP))
for h_ in (.40, .22):
    det.add(tube(arc_path((0, 0), rail_r, 22.5, 337.5, n=60, z=L.DECK_TOP + h_), .012, 6, zone=Z.yellow, caps=True))

# ---- propellant tank crowns, feed lines, COPVs, avionics
dome = tank_dome(.335, .17)
bolts = bolt_ring(.35, 20, zone=Z.steel)
for k, az in enumerate((45, 135, 225, 315)):
    a = math.radians(az)
    m = T(2.09 * math.sin(a), -2.09 * math.cos(a), L.DECK_TOP)
    det.add(dome, m)
    det.add(bolts, m @ T(0, 0, .012))
    # valve cluster on the crown
    det.add(cyl(.04, .04, 10, zone=Z.bare, center_z=False), m @ T(0, 0, .185))
    det.add(tube([(0, 0, .22), (.0, .0, .26), (.06, .05, .28), (.20, .16, .05), (.26, .21, .0)], .014, 8, zone=Z.bare), m)
    # main feed to the mount ring, via brackets
    p0 = m @ Vector((-.30 * math.sin(a), .30 * math.cos(a), .03))
    p1 = Vector((1.74 * math.sin(a), -1.74 * math.cos(a), L.DECK_TOP + .03))
    feed = [p0, p1]
    det.add(tube(feed, .022, 8, zone=Z.copper))
    for t_ in (.2, .8):
        q = p0.lerp(p1, t_)
        det.add(box(.08, .03, .03, zone=Z.grey, center=(q.x, q.y, L.DECK_TOP + .015)))
# rim ring main: LOX crossfeed manifold around the outer field
ring_path = arc_path((0, 0), 2.42, 16, 344, n=72, z=L.DECK_TOP + .03)
det.add(tube(ring_path, .016, 8, zone=Z.bare))
for k in range(24):
    az = 15 * k
    if abs((az + 180) % 360 - 180) < 14:
        continue
    a = math.radians(az)
    det.add(box(.05, .04, .03, zone=Z.grey, center=(2.42 * math.sin(a), -2.42 * math.cos(a), L.DECK_TOP + .012)))
# COPVs in pairs on three sides
cp = copv(.17)
for azc in (90, 180, 270):
    for off in (-14, 14):
        az = azc + off
        a = math.radians(az)
        m = T(2.1 * math.sin(a), -2.1 * math.cos(a), L.DECK_TOP) @ Rz(az)
        det.add(cp, m)
# avionics boxes with the deck sheet's trim
bz = {
    'avi': Zone(L.BOXES[0] + 16, L.BOXES[1] + 16, 224, 224, atlas=2048, ppm=500),
    'fin': Zone(L.BOXES[0] + 272, L.BOXES[1] + 16, 224, 224, atlas=2048, ppm=500),
    'pdu': Zone(L.BOXES[0] + 784, L.BOXES[1] + 16, 224, 224, atlas=2048, ppm=500),
}
deck_boxes = Geo()
for az, zn, w_, d_, h_ in ((22, 'avi', .34, .26, .16), (-22, 'fin', .30, .26, .14), (158, 'pdu', .30, .26, .18), (202, 'avi', .34, .26, .16), (68, 'fin', .28, .24, .12), (292, 'pdu', .28, .24, .14)):
    a = math.radians(az)
    m = T(1.92 * math.sin(a), -1.92 * math.cos(a), L.DECK_TOP) @ Rz(az)
    deck_boxes.add(avionics_box(w_, d_, h_, bz[zn]), m)
    # cable into the box, run to the rim
    pa = m @ Vector((0, .12, .06)); pb = m @ Vector((0, .40, .02)); pc = m @ Vector((.0, -.50, .02))
    det.add(cable_bundle([pa, pb], r=.006, n=2), None)
    det.add(cable_bundle([m @ Vector((0, -.12, .06)), pc], r=.006, n=2), None)

# ---- rim: RCS blocks, grapple fixture, antennas, star trackers, sensors, ladder
for az in L.RCS_AZ:
    det.add(rcs_quad(), on_cyl(az, .25, 2.5))
det.add(frgf(.9), on_cyl(180.001, .30, 2.52))
det.add(patch_antenna(.14), on_cyl(150, .34, 2.515))
det.add(patch_antenna(.14), on_cyl(-150, .34, 2.515))
det.add(blade_antenna(.15), on_cyl(90, .40, 2.51))
det.add(blade_antenna(.15), on_cyl(-90, .40, 2.51))
det.add(qd_panel(.20, .13), on_cyl(-15, .34, 2.515))
det.add(qd_panel(.20, .13), on_cyl(15, .34, 2.515))
for az in (45, 135, 225, 315):
    det.add(phased_array(), on_cyl(az, -.35, 2.515))
det.add(handrail(.8, standoff=.035, bar=.012), on_cyl(0.001, .20, 2.5) @ T(-.26, 0, 0))
det.add(handrail(.8, standoff=.035, bar=.012), on_cyl(0.001, .20, 2.5) @ T(.26, 0, 0))
# upper section of the deck-edge ladder: fixed rails
rail0 = on_cyl(0.001, .02, 2.5)
for s in (-1, 1):
    det.add(box(.022, 1.16, .016, zone=Z.grey, bevel=.002, center=(s * .16, 0, .03)), rail0)

# ---- underside: methalox descent engines (gr_engine.py). Each engine's frame turns its turbopump outboard;
# the gimbal empties keep the part's axes.
eng_mv, eng_st, eng_j = engine(ENGINE)
engines = []
for k in range(L.N_ENG):
    az = 22.5 + 45 * k
    a = math.radians(az)
    base = T(L.ENGINE_R * math.sin(a), -L.ENGINE_R * math.cos(a), L.DECK_BOT)
    gpt = base @ T(0, 0, -.13)
    ef = gpt @ Rz(az - 90)          # local +X radially out
    det.add(eng_st, ef)
    engines.append((k, az, gpt, ef))
# centre hub cover and pipes to each engine
det.add(cyl(.70, .04, 32, zone=Z.grey, center_z=False), T(0, 0, L.DECK_BOT - .04))
det.add(bolt_ring(.64, 32, zone=Z.steel), Rx(180) @ T(0, 0, -L.DECK_BOT + .04))
# propellant manifold on the hub: LOX and CH4 distribution drums and the isolation valves
det.add(cyl(.34, .10, 24, zone=Z.white, bevel=.012, center_z=False), T(0, 0, L.DECK_BOT - .14))
det.add(cyl(.20, .08, 20, zone=Z.bare, bevel=.008, center_z=False), T(0, 0, L.DECK_BOT - .22))
for k in range(8):
    a = math.radians(22.5 + 45 * k)
    det.add(box(.09, .07, .05, zone=Z.grey, bevel=.006, center=(0, 0, 0)), T(.42 * math.sin(a), -.42 * math.cos(a), L.DECK_BOT - .07) @ Rz(22.5 + 45 * k))
for k, az, gpt, ef in engines:
    a = math.radians(az)
    t_ = Vector((math.cos(a), math.sin(a), 0))
    for name, side in (('lox', 1), ('fuel', -1)):
        pp = Vector((.60 * math.sin(a), -.60 * math.cos(a), L.DECK_BOT - .03)) + t_ * (.05 * side)
        j = eng_j[name]
        path = [pp, ef @ Vector((-.42, .10 * side, .10)), ef @ Vector((-.20, .11 * side, .075)), ef @ Vector((j.x, j.y, .03)), ef @ Vector((j.x, j.y, j.z + .014))]
        det.add(tube(path, .016, 6, zone=Z.copper if name == 'fuel' else Z.bare, caps=False))

# ---- objects
o_wall = P.mesh('deck_wall', wall, M_deck, smooth_angle=40)
o_top = P.mesh('deck_top', top, M_deck, smooth_angle=40)
o_und = P.mesh('deck_under', under, M_deck, smooth_angle=40)
o_mnt = P.mesh('mount', mount, M_deck, smooth_angle=40)
P.mesh('deck_boxes', deck_boxes, M_deck)
P.mesh('details', det, M_det)

# gimballed engines: each under its own 'gimbal' empty so ModuleGimbal finds all of them
M_eng = P.material('shab_engine', spec=(.9, .9, .9), shininess=.35)
for k, az, gpt, ef in engines:
    g_ = P.empty('gimbal', gpt, P.model)
    gg = Geo(); gg.add(eng_mv, ef)
    P.mesh(f'bell{k}', gg, M_eng, parent=g_, frame=gpt, smooth_angle=50)
    # thrust transform at the nozzle exit plane, local +Z along the exhaust (-Z of the part)
    tf = frame_axes(gpt @ Vector((0, 0, -.82)), (0, 0, -1), x=(1, 0, 0))
    P.empty('thrustTransform', tf, g_)

# RCS nozzles and thrust transforms
noz = Geo()
proto = rcs_nozzle()
for az in L.RCS_AZ:
    f = on_cyl(az, .25, 2.5)
    for pos, d in RCS_NOZZLES:
        tf = thruster_frame(f, pos, d)
        noz.add(proto, tf)
        o = P.empty('RCSthruster', tf, P.model)
        P.empty('RCSjet', tf, o)
P.mesh('rcs_nozzles', noz, M_det)

# deck-edge telescoping ladder: slides out past the stowed HIAD and down toward the ground
lad_top = ladder(1.10, width=.22, standoff=.02)
lad_bot = ladder(1.10, width=.17, standoff=.0)
stow_a = on_cyl(0.001, .02, 2.5) @ T(0, 0, .03)
ga = Geo(); ga.add(lad_top, stow_a)
o_a = P.mesh('ladderTop', ga, M_det, frame=stow_a)
stow_b = stow_a @ T(0, 0, .014)
gb = Geo(); gb.add(lad_bot, stow_b)
o_b = P.mesh('ladderLow', gb, M_det, parent=o_a, frame=stow_b)
# outriggers that carry the ladder clear of the stowed HIAD band
for s in (-1, 1):
    arm = on_cyl(0.001, .40, 2.5) @ T(s * .16, 0, .03)
    gg = Geo(); gg.add(box(.016, .016, .46, zone=Z.yellow, bevel=.002, center=(0, 0, -.22)), arm)   # runs back into the wall when stowed
    P.mesh('ladderArm' + ('L' if s < 0 else 'R'), gg, M_det, parent=o_a, frame=arm)
rest_a = o_a.location.copy(); rest_b = o_b.location.copy()
# rest pose is frame 0 (stowed). Deployed: out along -Y by 0.46 m, top section down 0.4 m.
P.key('ladderDeploy', o_a, 0, location=rest_a)
P.key('ladderDeploy', o_a, 30, location=rest_a + Vector((0, -.46, 0)))
P.key('ladderDeploy', o_a, 60, location=rest_a + Vector((0, -.46, -.40)))
P.key('ladderDeploy', o_b, 0, location=rest_b)
P.key('ladderDeploy', o_b, 30, location=rest_b)
P.key('ladderDeploy', o_b, 90, location=rest_b + Vector((0, -1.05, 0)))    # parent's frame: its +Y runs up the wall
OUT = (0, -1, 0)
P.box_trigger('ladder_deck', climb_frame((stow_a @ T(0, 0, .07)).translation, OUT), (.30, .18, 1.15), 'Ladder', parent=o_a)
P.box_trigger('ladder_low', climb_frame((stow_b @ T(0, 0, .07)).translation, OUT), (.26, .18, 1.15), 'Ladder', parent=o_b)
# the wall rails are climbable, so the landing connects to the deck above it
P.box_trigger('ladder_wall', climb_frame((0, -2.55, .34), OUT), (.34, .14, .66), 'Ladder')
# ---- landing: a grating that folds down like a drawbridge between the outrigger arms, once the ladder has moved
# out of its way. Stowed flat on the wall with its walking face inward. Rotating +90 about X takes up to out.
LAND_W, LAND_L, LAND_R, LAND_Z = .29, .44, 2.528, .012
piv = P.empty('landingPivot', T(0, -LAND_R, LAND_Z), P.model)
lg = Geo()
face = frame_axes((0, -LAND_R, LAND_Z + .008 + LAND_L / 2), (0, 1, 0), x=(-1, 0, 0))
lg.add(quad_patch(LAND_W, LAND_L, Z.grating), face)
lg.add(box(LAND_W, .012, LAND_L, zone=Z.dark, bevel=.002, center=(0, -LAND_R - .0065, LAND_Z + .008 + LAND_L / 2)))
for s_ in (-1, 1):      # raised yellow edges
    lg.add(box(.006, .024, LAND_L, zone=Z.yellow, bevel=.001, center=(s_ * (LAND_W / 2 - .001), -LAND_R + .006, LAND_Z + .008 + LAND_L / 2)))
lg.add(box(LAND_W, .022, .007, zone=Z.yellow, bevel=.001, center=(0, -LAND_R + .005, LAND_Z + .008 + LAND_L)))
lg.add(cyl(.007, LAND_W - .02, 8, zone=Z.steel), T(0, -LAND_R, LAND_Z) @ Ry(90))
P.mesh('landingDeck', lg, M_det, parent=piv)
P.hull_collider('col_landing', [Vector((x_, -LAND_R + y_, LAND_Z + z_)) for x_ in (-LAND_W / 2, LAND_W / 2) for y_ in (-.012, .0) for z_ in (.008, .008 + LAND_L)], parent=piv)
for f_, deg in ((0, 0), (30, 0), (40, 12), (50, 40), (60, 70), (70, 90), (90, 90)):
    P.key('ladderDeploy', piv, f_, rotation_quaternion=Quaternion((1, 0, 0), math.radians(deg)))


# ---- colliders
def ring(r, z, n=24):
    return [Vector((r * math.cos(TAU * i / n), r * math.sin(TAU * i / n), z)) for i in range(n)]


cc = P.empty('colliders', parent=P.model)
P.hull_collider('col_deck', ring(2.52, L.DECK_BOT) + ring(2.52, L.DECK_TOP), parent=cc)
P.hull_collider('col_mount', ring(.90, L.DECK_TOP) + ring(.86, L.MOUNT_Z), parent=cc)
P.hull_collider('col_landing', [landing @ Vector(p) for p in ((-.26, -.25, -.02), (.26, -.25, -.02), (.26, .25, -.02), (-.26, .25, -.02), (-.26, -.25, 0), (.26, -.25, 0), (.26, .25, 0), (-.26, .25, 0))], parent=cc)

P.node('top', (0, 0, L.MOUNT_Z), (0, 0, 1), 2)
P.node('bottom', (0, 0, L.DECK_BOT), (0, 0, -1), 3)
for i, az in enumerate(L.LEG_AZ):
    a = math.radians(az)
    P.node(f'leg{i + 1}', (2.5 * math.sin(a), -2.5 * math.cos(a), L.LEG_Z), (math.sin(a), -math.cos(a), 0), 1)
P.bake_clips(0)
P.export(out)
P.save_blend(out)
for k, v in P.nodes.items():
    print('NODE', k, f'{v[0].x:.4f}, {v[0].z:.4f}, {v[0].y:.4f}, {v[1].x:.4f}, {v[1].z:.4f}, {v[1].y:.4f}, {v[2]}')
