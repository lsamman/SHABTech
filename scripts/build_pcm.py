"""SHAB pressurized cargo module: Cygnus "Super" PCM with bare MMOD and FIB-blanket shells."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
import layout as L

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(7)

P = Part('shab_PCM')
P.variants = ({'hull_bare', 'dome_bare'}, {'hull_fib', 'dome_fib'})     # the B9 shell switch
M_mmod = P.material('shab_mmod')
M_fib = P.material('shab_fib')
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)
M_win = P.material('shab_window', shader='KSP/Emissive/Bumped Specular', nrm='shab_window', emissive='shab_window_emit', shininess=.6)
M_lamp = P.material('shab_details', shader='KSP/Emissive/Bumped Specular', nrm='shab_details', emissive='shab_lamp_emit', name='lamp')


# --- UV helpers on the hull sheet
def uv_strip(az, r, z, arc):
    return L.hull_uv(az, z)


def uv_polar(az, r, z, arc):
    return L.dome_uv(az, r)


def uv_panel(az, z):
    return L.hull_uv(az, z)


def ring_uv(rect):
    x0, y0, w, h = rect

    def fn(az, r, z, arc):
        return ((x0 + L.az_wrap(az) / 360 * w) / L.ATLAS, 1 - (y0 + h - (arc * 800) % h) / L.ATLAS)
    return fn


def disc_uv(rect, rmax):
    x0, y0, w, h = rect

    def fn(az, r, z, arc):
        a = math.radians(az)
        return ((x0 + w / 2 + math.sin(a) * r / rmax * w / 2) / L.ATLAS, 1 - (y0 + h / 2 + math.cos(a) * r / rmax * h / 2) / L.ATLAS)
    return fn


A0, A1 = L.SEAM_AZ, L.SEAM_AZ + 360.0
SEG = 96


def lathe_strip(profile, seg=SEG):
    return lathe(profile, seg, A0, A1, uv_fn=uv_strip)


# ------------------------------------------------------------- shared structure
skirt = lathe_strip([(.80, L.Z_BOT), (.83, L.Z_BOT + .03), (.86, L.Z_BOT + .07), (L.R_FLOOR, L.SEG_Z[0] - L.FRAME_H)])
base_cap = lathe([(0, L.Z_BOT), (.80, L.Z_BOT)], 48, A0, A1, uv_fn=disc_uv(L.DECK_ZONE, .82))

# ------------------------------------------------------------- bare MMOD hull
bare = Geo()
fz = L.FRAME_H
# floor between frames
prof = []
for k in range(4):
    z0, z1 = L.SEG_Z[k] + fz, L.SEG_Z[k + 1] - fz
    prof += [(L.R_FLOOR, z0), (L.R_FLOOR, z1)]
    bare.add(lathe_strip([(L.R_FLOOR, z0), (L.R_FLOOR, z1)]))
for z in L.SEG_Z:
    bare.add(lathe_strip([(L.R_FLOOR, z - fz), (L.R_ENV - .006, z - fz + .002), (L.R_ENV, z - fz + .006), (L.R_ENV, z + fz - .006), (L.R_ENV - .006, z + fz - .002), (L.R_FLOOR, z + fz)]))
# ribs
for rib in L.RIB_AZ:
    for k in range(4):
        z0, z1 = L.SEG_Z[k] + fz, L.SEG_Z[k + 1] - fz
        bare.add(curved_panel(L.R_FLOOR, rib - L.RIB_HALF, rib + L.RIB_HALF, z0, z1, raise_=L.R_ENV - L.R_FLOOR, chamfer=.006, seg=2, uv_fn=uv_panel))
# bumpers: recess the hatch bay (hatch flange hides them)
gap_a = L.RIB_HALF + .35
for b, baz in enumerate(L.BAY_AZ):
    for k in range(4):
        z0, z1 = L.SEG_Z[k] + fz + .002, L.SEG_Z[k + 1] - fz - .002
        zm = (z0 + z1) / 2
        for pz0, pz1 in ((z0, zm - L.PANEL_GAP_Z), (zm + L.PANEL_GAP_Z, z1)):
            a0_, a1_ = baz - L.BAY_W / 2 + gap_a, baz + L.BAY_W / 2 - gap_a
            bare.add(curved_panel(L.R_FLOOR, a0_, a1_, pz0, pz1, raise_=L.R_ENV - .004 - L.R_FLOOR, chamfer=.007, seg=6, uv_fn=uv_panel))
def dome_lathe(prof):
    tot = sum(math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]) for i in range(1, len(prof)))

    def fn(az, r, z, arc):
        return L.dome_uv(az, L.dome_rho(arc, tot))
    return lathe(prof, SEG, A0, A1, uv_fn=fn)


bare_dome = dome_lathe([(L.R_ENV, L.SEG_Z[-1] + fz), (L.R_ENV, L.Z_SHOULDER - .02), (.93, L.Z_SHOULDER + .03), (.88, L.Z_SHOULDER + .13), (.80, L.Z_SHOULDER + .26), (.70, L.Z_SHOULDER + .40), (L.R_COLLAR + .01, L.Z_COLLAR - .08), (L.R_COLLAR, L.Z_COLLAR - .06)])

# ------------------------------------------------------------- FIB blanket shell
fib = Geo()
fib.add(lathe_strip([(L.R_FLOOR + .01, L.SEG_Z[0] - fz - .01), (L.R_FIB - .012, L.SEG_Z[0] - fz), (L.R_FIB, L.SEG_Z[0] + fz)] + [(L.R_FIB, z) for z in np.linspace(L.SEG_Z[0] + .2, L.SEG_Z[-1], 6)] + [(L.R_FIB, L.Z_SHOULDER - .001)]))
fib_dome = dome_lathe([(L.R_FIB, L.Z_SHOULDER - .002), (.945, L.Z_SHOULDER + .03), (.895, L.Z_SHOULDER + .13), (.815, L.Z_SHOULDER + .26), (.715, L.Z_SHOULDER + .40), (L.R_COLLAR + .012, L.Z_COLLAR - .08), (L.R_COLLAR, L.Z_COLLAR - .06)])

# ------------------------------------------------------------- CBM collar and hatch
collar = Geo()
collar.add(lathe([(L.R_COLLAR, L.Z_COLLAR - .065), (L.R_COLLAR, L.Z_COLLAR + .005), (L.R_COLLAR - .006, L.Z_COLLAR + .012), (L.R_CBM, L.Z_COLLAR + .018), (L.R_CBM, L.Z_TOP - .02), (L.R_CBM - .008, L.Z_TOP), (L.R_HATCH + .02, L.Z_TOP), (L.R_HATCH + .01, L.Z_TOP - .012), (L.R_HATCH + .01, L.Z_HATCH + .012), (L.R_HATCH, L.Z_HATCH)], 72, A0, A1, uv_fn=ring_uv(L.RING_ZONE)))
collar.add(lathe([(L.R_HATCH, L.Z_HATCH), (0, L.Z_HATCH)], 48, A0, A1, uv_fn=disc_uv(L.DECK_ZONE, L.R_HATCH)))

# ------------------------------------------------------------- details
det = Geo()
# hatch handle on the well floor, for when no port is fitted
det.add(tube([(-.09, -.16, L.Z_HATCH - .002), (-.09, -.16, L.Z_HATCH + .028), (.09, -.16, L.Z_HATCH + .028), (.09, -.16, L.Z_HATCH - .002)], .007, 6, zone=Z.yellow))
RAIL_R = L.R_FIB - .004  # stand-off feet start under the blanket and pass through
# vertical rails along every rib, segment by segment; skip those beside the hatch where the
# ladder/hood already give hand holds
for rib in L.RIB_AZ:
    for k in range(4):
        z0, z1 = L.SEG_Z[k] + .07, L.SEG_Z[k + 1] - .07
        det.add(handrail(z1 - z0, standoff=.034, bar=.012), on_cyl(rib, (z0 + z1) / 2, RAIL_R))
# circumferential rail around the crown, below the TPS cap's reach, and above the hatch
for baz in L.BAY_AZ:
    if baz == L.HATCH_AZ:
        continue
    fr = on_cyl(baz, L.SEG_Z[1] + .02, RAIL_R) @ Rz(90)
    det.add(handrail(.36, standoff=.034, bar=.012), fr)

# grapple fixture (paper: Canadarm2 assembly): lower floor, opposite the hatch, sticks out
det.add(frgf(), on_cyl(180 - 1e-3, -.55, L.R_FIB - .002))
# cable runs: along the ribs at 90 and -90, into junction boxes
for az_, off in ((90, 2.2), (-90, -2.2), (150, 2.2)):
    a = az_ + off + 2.2 * (1 if off > 0 else -1)
    path = []
    for z in np.linspace(L.SEG_Z[0] + .06, L.SEG_Z[-1] - .03, 14):
        p = on_cyl(a, float(z), L.R_FIB + .009).translation
        path.append(tuple(p))
    det.add(cable_bundle(path, r=.0048, n=3))
    for z in np.linspace(L.SEG_Z[0] + .12, L.SEG_Z[-1] - .1, 7):
        det.add(box(.018, .008, .024, zone=Z.grey, bevel=.0015, center=(0, 0, .012)), on_cyl(a, float(z), L.R_FIB - .002))
    det.add(junction_box(.10, .10, .028), on_cyl(a, L.SEG_Z[-1] - .03, L.R_FIB - .002))
    det.add(junction_box(.08, .06, .024), on_cyl(a, L.SEG_Z[0] + .03, L.R_FIB - .002))
# S-band patches and UHF blades
det.add(patch_antenna(.15), on_cyl(-60, -1.32, L.R_FIB - .002))
det.add(patch_antenna(.15), on_cyl(120, -1.32, L.R_FIB - .002))
det.add(blade_antenna(.15), on_cyl(-120, -1.52, L.R_FIB - .001))
det.add(blade_antenna(.15), on_cyl(60, -1.52, L.R_FIB - .001))
# ECLSS vents
for az_, z_ in ((-120, -.14), (120, -.14), (-68, -.62), (-52, -.62)):
    det.add(vent_stub(.014), on_cyl(az_, z_, L.R_FIB - .002))
# umbilical plates to the lander (propellant-free: power, data, water)
det.add(qd_panel(.2, .13), on_cyl(-120, -1.26, L.R_FIB - .002))
det.add(qd_panel(.2, .13), on_cyl(60, -1.26, L.R_FIB - .002))
# body-mounted radiators (fig. text: "radiators will be installed"), lower floor
for az_ in (120, -120):
    fr0, fr1 = L.SEG_Z[1] + .05, L.SEG_Z[2] - .05
    det.add(radiator_panel(L.R_FIB, az_ - 22, az_ + 22, fr0, fr1))
    # feed lines
    for s in (-1, 1):
        a = az_ + s * 23.5
        path = [tuple(on_cyl(a, float(z), L.R_FIB + .008).translation) for z in np.linspace(fr0 - .06, fr1, 5)]
        det.add(tube(path, .006, 6, zone=Z.copper))

# ------------------------------------------------------------- airlock door, flange, hood, ladder
rt = L.R_TANGENT
door_fr = on_cyl(L.HATCH_AZ, L.HATCH_Z, rt)
det.add(rounded_rect_ring(L.HATCH_W + .08, L.HATCH_H + .08, .08, .05, .10, seg=5, zone=Z.white, base=-.08), door_fr)
det.add(bolt_ring(0, 0), door_fr)
# door sheet
x0, y0, w, h = L.DOOR_ZONE
door_zone = Zone(x0, y0, w, h, atlas=L.ATLAS)
door = quad_patch(L.HATCH_W, L.HATCH_H, door_zone, z=.0)
door_geo = Geo(); door_geo.add(door, door_fr)
# external handle + grab bars on the door
det.add(tube([(-.11, .22, .002), (-.11, .22, .04), (.11, .22, .04), (.11, .22, .002)], .007, 6, zone=Z.yellow), door_fr)
det.add(tube([(-.05, -.02, .002), (-.05, -.02, .03), (.05, -.02, .03), (.05, -.02, .002)], .009, 6, zone=Z.red), door_fr)
for s in (-1, 1):
    det.add(handrail(.42, standoff=.045, zone=Z.yellow), door_fr @ T(s * (L.HATCH_W / 2 + .055), 0, .02))
# dust-lock hood above the door: a cantilevered visor with blower bar and side curtains
hood = door_fr @ T(0, L.HATCH_H / 2 + .05, .02)
det.add(box(L.HATCH_W + .10, .03, .13, zone=Z.white, bevel=.006, center=(0, .03, .05)), hood)
det.add(box(L.HATCH_W + .10, .018, .012, zone=Z.vent, center=(0, .012, .118)), hood)
for s in (-1, 1):
    det.add(box(.016, .10, .12, zone=Z.white, bevel=.003, center=(s * (L.HATCH_W / 2 + .05), -.03, .05)), hood)
    det.add(box(.006, .62, .05, zone=Z.rubber, center=(s * (L.HATCH_W / 2 + .05), -.40, .03)), hood)   # dust curtains
det.add(wide_camera(), door_fr @ T(L.HATCH_W / 2 + .13, L.HATCH_H / 2 + .05, -.01))
# floodlights either side of the hood
for s in (-1, 1):
    lp = door_fr @ T(s * (L.HATCH_W / 2 + .13), L.HATCH_H / 2 - .1, .0)
    det.add(exterior_lamp(), lp)
# porch and ladder down to the lander deck
porch = door_fr @ T(0, -L.HATCH_H / 2 - .03, .005)
det.add(grate_platform(.46, .24), porch)
lad_len = (L.HATCH_Z - L.HATCH_H / 2 - .05) - L.Z_BOT
det.add(ladder(lad_len, width=.2, standoff=.08), on_cyl(L.HATCH_AZ, L.Z_BOT + lad_len / 2, L.R_FIB - .004))

# ------------------------------------------------------------- windows
win_objs = []
for wi, zw in enumerate(L.WIN_Z):
    fr = on_cyl(L.WIN_AZ, zw, rt - .012)
    det.add(rounded_rect_ring(L.WIN_W + .07, L.WIN_H + .07, .05, .05, .08, seg=4, zone=Z.white, base=-.05), fr)
    det.add(rounded_rect_ring(L.WIN_W + .012, L.WIN_H + .012, .03, .012, .035, seg=4, zone=Z.dark, base=-.012), fr)
    # glass, emissive at night
    wz = Zone(0, 0, 512, 512, atlas=512)
    glass = Geo(); glass.add(quad_patch(L.WIN_W, L.WIN_H, wz, z=.002), fr)
    win_objs.append(glass)

# ------------------------------------------------------------- objects
hullb = Geo(); hullb.add(bare)
o_bare = P.mesh('hull_bare', hullb, M_mmod, smooth_angle=40)
o_bdome = P.mesh('dome_bare', bare_dome, M_mmod, smooth_angle=60)
o_fib = P.mesh('hull_fib', fib, M_fib, smooth_angle=50)
o_fdome = P.mesh('dome_fib', fib_dome, M_fib, smooth_angle=60)
P.mesh('skirt', skirt, M_mmod, smooth_angle=60)
P.mesh('base_cap', base_cap, M_mmod)
P.mesh('collar', collar, M_mmod, smooth_angle=45)
P.mesh('door', door_geo, M_mmod)
P.mesh('details', det, M_det, smooth_angle=38)

# window glass + shutters
for i, g in enumerate(win_objs):
    P.mesh(f'window_glass{i}', g, M_win)

# lamp lenses (emissive material, toggled by ModuleLight colour)
ln = Geo()
for s in (-1, 1):
    ln.add(lamp_lens(), door_fr @ T(s * (L.HATCH_W / 2 + .13), L.HATCH_H / 2 - .1, .0))
P.mesh('lamp_lens', ln, M_lamp)
for s in (-1, 1):
    f = door_fr @ T(s * (L.HATCH_W / 2 + .13), L.HATCH_H / 2 - .1, .04)
    beam = door_fr.to_3x3() @ Vector((0, -.75, .65))
    add_spot(P, 'hatchLight', f.translation, beam, power=1200)

# window shutters: hinged cover along each window's top edge. The hinge stands proud of the skin so the
# open cover lies back along the hull, under the entry cap's liner.
SHUT_LIFT = .022
SHUT_OPEN = 175
for i, zw in enumerate(L.WIN_Z):
    fr = on_cyl(L.WIN_AZ, zw, rt + SHUT_LIFT) @ T(0, L.WIN_H / 2 + .012, 0)
    sh = Geo()
    sh.add(box(L.WIN_W + .03, L.WIN_H + .03, .006, zone=Z.white, bevel=.002, center=(0, -(L.WIN_H + .03) / 2, 0)), Matrix())
    sh.add(box(.02, .012, .02, zone=Z.grey, center=(-.05, 0, -.012)))
    sh.add(box(.02, .012, .02, zone=Z.grey, center=(.05, 0, -.012)))
    sh.add(tube([(-.03, -(L.WIN_H) * .85, .004), (-.03, -(L.WIN_H) * .85, .023), (.03, -(L.WIN_H) * .85, .023), (.03, -(L.WIN_H) * .85, .004)], .004, 5, zone=Z.yellow))
    gg = Geo(); gg.add(sh, fr)
    oo = P.mesh(f'shutter{i}', gg, M_det, frame=fr)
    closed = oo.matrix_basis.to_quaternion()
    # open: swings up and out about local X. Rest state (frame 0) = open.
    for f_ in range(0, 31, 5):
        q_ = Quaternion((1, 0, 0), math.radians(-SHUT_OPEN * (1 - f_ / 30)))
        P.key('windowCover', oo, f_, rotation_quaternion=closed @ q_)

# ------------------------------------------------------------- colliders + triggers
def ring_pts(r, z, n=20):
    return [Vector((r * math.cos(TAU * i / n), r * math.sin(TAU * i / n), z)) for i in range(n)]


colliders = P.empty('colliders', parent=P.model)
P.hull_collider('col_body', ring_pts(L.R_FIB, L.SEG_Z[0]) + ring_pts(L.R_FIB, L.Z_SHOULDER) + ring_pts(.80, L.Z_BOT), parent=colliders)
P.hull_collider('col_crown', ring_pts(L.R_FIB, L.Z_SHOULDER) + ring_pts(.72, L.Z_SHOULDER + .40) + ring_pts(.69, L.Z_HATCH), parent=colliders)
# the collar is a ring of wedges round the docking well, leaving the well open
for k in range(12):
    a0_, a1_ = TAU * k / 12, TAU * (k + 1) / 12
    P.hull_collider(f'col_collar{k}', [Vector((r * math.cos(a), r * math.sin(a), z)) for (r, z) in ((L.R_HATCH, L.Z_HATCH), (.69, L.Z_HATCH), (L.R_COLLAR, L.Z_COLLAR), (L.R_CBM, L.Z_TOP), (L.R_HATCH, L.Z_TOP)) for a in (a0_, a1_)], parent=colliders)
# door/hood (stops kerbals walking through it)
P.hull_collider('col_hood', [tuple(hood @ Vector(p)) for p in ((-.33, .05, 0), (.33, .05, 0), (-.33, .05, .13), (.33, .05, .13), (-.33, -.02, 0), (.33, -.02, 0), (-.33, -.02, .13), (.33, -.02, .13))], parent=colliders)
P.hull_collider('col_porch', [tuple(porch @ Vector(p)) for p in ((-.23, 0, 0), (.23, 0, 0), (-.23, 0, .24), (.23, 0, .24), (-.23, -.04, 0), (.23, -.04, 0), (-.23, -.04, .24), (.23, -.04, .24))], parent=colliders)
# EVA: airlock trigger just outside the door, ladder triggers on rails and the fixed ladder
P.box_trigger('airlock', climb_on_cyl(L.HATCH_AZ, L.HATCH_Z, rt + .12), (.5, .35, .8), 'Airlock')
for rib in L.RIB_AZ:
    fr = climb_on_cyl(rib, (L.SEG_Z[0] + L.SEG_Z[-1]) / 2, L.R_FIB + .05)
    P.box_trigger(f'ladder_{int(rib + 180)}', fr, (.12, .14, L.SEG_Z[-1] - L.SEG_Z[0]), 'Ladder')
P.box_trigger('ladder_main', climb_on_cyl(L.HATCH_AZ, L.Z_BOT + lad_len / 2 + .05, L.R_FIB + .07), (.26, .18, lad_len + .25), 'Ladder')

P.node('top', (0, 0, L.Z_TOP), (0, 0, 1), 1)
P.node('dock', (0, 0, L.Z_DOCK), (0, 0, 1), 1)
P.node('bottom', (0, 0, L.Z_BOT), (0, 0, -1), 2)
P.bake_clips(0)
# the collar docks in its own right when no port is fitted
P.empty('dockingNode', frame_axes((0, 0, L.Z_TOP), (0, 0, 1), x=(1, 0, 0)), P.model)
P.export(out)
P.save_blend(out)
