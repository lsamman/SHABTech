"""SHAB entry cap: jettisonable TPS over the PCM's top half (paper fig. 2, 4, 7). Attaches to
the PCM top node at z = 0 and hangs down around the hull, clearing rails and window flanges. The
crown is low: an NDS port seated in the PCM's collar sits just under the opening, with the nose cone shut over it."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
import layout as L

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(11)
P = Part('shab_TPS')
M = P.material('shab_tps', shininess=.25)
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)

R_OUT, R_IN = 1.085, 1.045
Z_LOW, Z_SHOULDER = -1.92, -.30
N = 2048
CIRC = TAU * R_OUT
PXM = N / CIRC
A0, A1 = 0.0, 360.0
D = 1000; RHOMAX = 1.75


def uv_strip(az, r, z, arc):
    return (az % 360 if az < 360 else 360) / 360, (z - Z_LOW) * PXM / N


def plen(prof):
    return sum(math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]) for i in range(1, len(prof)))


def crown(prof, tot=None, arc0=0.0):
    tot = tot or plen(prof)

    def fn(az, r, z, arc):
        rho = tot - arc0 - arc
        a = math.radians(az)
        c = D / 2
        return ((c + math.sin(a) * rho / RHOMAX * c) / N, 1 - (c + math.cos(a) * rho / RHOMAX * c) / N)
    return lathe(prof, 96, A0, A1, uv_fn=fn)


# outer skin: bottom edge lip, cylinder, shoulder, ogive to a low cone tip (fig 2 and 4)
skin = lathe([(R_OUT - .012, Z_LOW), (R_OUT, Z_LOW + .012)] + [(R_OUT, z) for z in np.linspace(Z_LOW + .1, Z_SHOULDER, 8)], 96, A0, A1, uv_fn=uv_strip)
dome_prof = [(R_OUT, Z_SHOULDER), (1.078, -.22), (1.052, -.13), (1.00, -.05), (.92, .02), (.78, .085), (.62, .14), (.42, .20), (.20, .25), (.05, .275), (0, .28)]
# the opening: everything inside R_OPEN is the hinged nose cone
I_OPEN = 6     # NDS reaches r = .494, so this leaves a clear gap all round it
R_OPEN, Z_OPEN = dome_prof[I_OPEN]
HINGE = (0, R_OPEN + .035, Z_OPEN + .012)
DOME_LEN = plen(dome_prof)
dome = crown(dome_prof[:I_OPEN + 1], DOME_LEN)
nose_skin = crown(dome_prof[I_OPEN:], DOME_LEN, plen(dome_prof[:I_OPEN + 1]))
# inner liner: silver foil facing the hab, a separate sheet region
lin_zone = Zone(1024, 0, 1024, 512, atlas=N)
liner = lathe([(R_IN, Z_SHOULDER + .08), (R_IN, Z_LOW + .03), (R_OUT - .012, Z_LOW)], 72, A0, A1, zone=lin_zone)
liner_dome = lathe([(R_IN, Z_SHOULDER + .08), (.98, -.09), (.86, .0), (.73, .05), (R_OPEN + .004, Z_OPEN - .07)][::1], 48, A0, A1, zone=lin_zone, flip=True)
# inside the collar: seat ring on the CBM and a truss to the shell
det = Geo()
det.add(lathe([(L.R_CBM + .03, -.02), (L.R_CBM + .03, .05), (L.R_CBM - .05, .05), (L.R_CBM - .05, .0)], 48, A0, A1, zone=Z.grey))
# the opening's edge: a skirt down into the shell and a trim ring on the crown
det.add(lathe([(R_OPEN + .004, Z_OPEN - .07), (R_OPEN + .004, Z_OPEN + .006), (R_OPEN + .05, Z_OPEN - .024)], 72, A0, A1, zone=Z.white))
# hinge brackets on the crown behind the opening
for sx_ in (-1, 1):
    det.add(box(.022, .07, .05, zone=Z.grey, bevel=.004), T(sx_ * .11, HINGE[1] + .012, HINGE[2] - .012))
det.add(cyl(.011, .24, 10, zone=Z.steel), T(*HINGE) @ Ry(90))
for k in range(8):
    a = 22.5 + 45 * k
    p0 = on_cyl(a, .04, L.R_CBM + .02).translation
    p1 = on_cyl(a + 12, -.20, .98).translation
    p2 = on_cyl(a - 12, -.20, .98).translation
    det.add(tube([tuple(p0), tuple(p1)], .018, 6, zone=Z.dark))
    det.add(tube([tuple(p0), tuple(p2)], .018, 6, zone=Z.dark))
# separation latches around the skirt
for k in range(6):
    az = 15 + 60 * k
    f = on_cyl(az, Z_LOW + .045, R_OUT - .003)
    det.add(box(.11, .07, .018, zone=Z.grey, bevel=.004, center=(0, 0, .012)), f)
    det.add(cyl(.016, .018, 10, zone=Z.steel, bevel=.003, center_z=False), f @ T(0, .0, .021))
    for sx_ in (-1, 1):
        det.add(cyl(.006, .004, 6, zone=Z.steel, center_z=False), f @ T(sx_ * .042, .022, .021))
        det.add(cyl(.006, .004, 6, zone=Z.steel, center_z=False), f @ T(sx_ * .042, -.022, .021))
    # pyro cabling between latches, in a surface raceway
    a2 = az + 60
    path = [tuple(on_cyl(float(az + (60 * t / 12)), Z_LOW + .018, R_OUT + .004).translation) for t in range(13)]
    det.add(tube(path, .005, 5, zone=Z.dark, caps=False))
# separation motors on the shoulder, canted out: fairings with exposed nozzles
for k in range(4):
    az = 45 + 90 * k
    f = on_cyl(az, Z_SHOULDER - .20, R_OUT - .003)
    det.add(box(.12, .34, .055, zone=Z.white, bevel=.012, center=(0, 0, .028)), f)
    det.add(tube([(0, -.18, .03), (0, -.21, .045)], .03, 12, zone=Z.nozzle, caps=False, r_fn=lambda t: .018 + .018 * t), f)
    det.add(cyl(.012, .012, 6, zone=Z.steel, center_z=False), f @ T(.042, .14, .05))
    det.add(cyl(.012, .012, 6, zone=Z.steel, center_z=False), f @ T(-.042, .14, .05))
# hoist lugs at the shoulder crown and a grapple pin for the assembly-in-orbit phase
for k in range(3):
    az = 15 + 120 * k
    f = on_cyl(az, -.13, 1.04) @ Rx(-32)
    det.add(box(.08, .12, .012, zone=Z.grey, bevel=.003, center=(0, 0, .006)), f)
    det.add(tube([(0, .03, .012), (0, .03, .045), (0, -.03, .045), (0, -.03, .012)], .01, 6, zone=Z.steel), f)
det.add(frgf(.9), on_cyl(195, Z_LOW + .55, R_OUT - .002))
# two chute canisters on the crown (the paper's parachute option for pulling the shell clear). The lids live in the
# Cap transform, which ModuleParachute hides on deployment; the canopies are shab_TPSCanopy.
CHUTE_NORMAL = Vector((.756, .655)).normalized()
lids = Geo()
for az in (90, 270):
    u = Vector((math.sin(math.radians(az)), math.cos(math.radians(az)), 0))
    n = u * CHUTE_NORMAL.x + Vector((0, 0, CHUTE_NORMAL.y))
    f = frame_axes(u * 1.0 + Vector((0, 0, -.05)), n, x=(0, 1, 0))
    det.add(cyl(.125, .045, 28, zone=Z.grey, bevel=.006, center_z=False), f @ T(0, 0, -.015))
    det.add(bolt_ring(.108, 12, zone=Z.steel), f @ T(0, 0, .03))
    lids.add(lathe([(.092, .030), (.092, .045), (.06, .062), (0, .068)], 28, 0, 360, zone=Z.white), f)
# static port and plume-free vents
for az in (120, 240):
    det.add(vent_stub(.012), on_cyl(az, Z_SHOULDER - .32, R_OUT - .002))
# heat-flux sensors, flush bright dots
for az, zz in ((80, -.5), (200, -.9), (320, -.25)):
    det.add(cyl(.018, .004, 12, zone=Z.bare, center_z=False), on_cyl(az, zz, R_OUT - .001))

o_skin = P.mesh('tps_skin', skin, M, smooth_angle=60)
P.mesh('tps_crown', dome, M, smooth_angle=60)
# nose cone on its hinge. It tips up and back past vertical, clear of anything approaching the port.
pivot = P.empty('nose_pivot', T(*HINGE), P.model)
P.mesh('nose_skin', nose_skin, M, parent=pivot, smooth_angle=60)
nd = Geo()
nd.add(lathe([(R_OPEN - .002, Z_OPEN), (R_OPEN - .018, Z_OPEN - .006), (.50, .13), (.34, .165), (.20, .195), (0, .23)], 48, A0, A1, zone=Z.bare))
for sx_ in (-1, 1):
    nd.add(tube([(sx_ * .09, HINGE[1], HINGE[2]), (sx_ * .09, HINGE[1] - .05, HINGE[2] + .012), (sx_ * .09, R_OPEN - .10, Z_OPEN + .012)], .009, 6, zone=Z.grey))
P.mesh('nose_inner', nd, M_det, parent=pivot)
OPEN_DEG, FR_OPEN = -150.0, 120
for i in range(9):
    t = i / 8
    e = t * t * (3 - 2 * t)
    P.key('noseOpen', pivot, int(round(t * FR_OPEN)), rotation_quaternion=Quaternion((1, 0, 0), math.radians(OPEN_DEG * e)))
L_ = Geo(); L_.add(liner); L_.add(liner_dome)
P.mesh('tps_liner', L_, M, smooth_angle=60)
P.mesh('tps_details', det, M_det)
P.mesh('chute_lids', lids, M_det, parent=P.empty('Cap', parent=P.model))

# colliders: hollow shell = a ring of wall boxes and a crown; the PCM sits inside
col = P.empty('colliders', parent=P.model)
n = 12
for k in range(n):
    a0, a1 = 360 * k / n, 360 * (k + 1) / n
    pts = []
    for az in (a0, a1):
        for rr in (R_IN, R_OUT):
            for zz in (Z_LOW, Z_SHOULDER):
                pts.append(on_cyl(az, zz, rr).translation.copy())
    P.hull_collider(f'col_wall{k}', pts, parent=col)
# the crown and nose are rings of wedges: a port stands in the middle, and must not touch the cap when it jettisons
def ring_wedges(tag, prof, parent, n=12):
    for k in range(n):
        pts = [Vector((r * math.sin(a), r * math.cos(a), z)) for (r, z) in prof for a in (TAU * k / n, TAU * (k + 1) / n)]
        P.hull_collider(f'{tag}{k}', pts, parent=parent)


ring_wedges('col_crown', dome_prof[:I_OPEN + 1], col)
ring_wedges('col_noseRim', [(R_OPEN, Z_OPEN), dome_prof[I_OPEN + 1]], pivot)
P.hull_collider('col_nose', [Vector((r * math.sin(TAU * i / 12), r * math.cos(TAU * i / 12), z)) for (r, z) in (dome_prof[I_OPEN + 1], dome_prof[I_OPEN + 2], dome_prof[I_OPEN + 3]) for i in range(12)], parent=pivot)

P.node('bottom', (0, 0, 0), (0, 0, -1), 1)
P.bake_clips(0)
P.export(out)
P.save_blend(out)
