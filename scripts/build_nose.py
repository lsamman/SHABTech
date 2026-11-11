"""shab_Nose: ablative plug closing the HIAD's centre during entry (fig. 3 "Nosecone")."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
import ll as L

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(17)
P = Part('shab_Nose')
M_h = P.material('shab_hiad', spec=(.4, .4, .4), shininess=.15)
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)

R_RIM = L.HUB_R - .02
R_FLAT = .72
DEPTH = .85
# spherical-ish cap meeting the hub rim, flattened at the adapter ring
n = 12
outer_prof = []
for i in range(n + 1):
    t = i / n
    # t=0 at the flat, t=1 at the rim
    r = R_FLAT + (R_RIM - R_FLAT) * t
    z = -DEPTH + DEPTH * (t ** 1.7) * .96
    outer_prof.append((r, z))
outer_prof.append((R_RIM + .01, -DEPTH * .02))
outer_prof.append((R_RIM + .01, 0.0))
total = sum(math.hypot(outer_prof[i][0] - outer_prof[i - 1][0], outer_prof[i][1] - outer_prof[i - 1][1]) for i in range(1, len(outer_prof)))
RH = R_FLAT + total


def uv_cap(az, r, z, arc):
    return L.polar_uv(L.NOSE, az, (R_FLAT * .5 + arc) / (R_FLAT * .5 + total) , 1.0)


cap = lathe(outer_prof, 72, -180, 180, uv_fn=uv_cap)
# flat underside inside the adapter ring
flat = lathe([(0, -DEPTH), (R_FLAT, -DEPTH)], 36, -180, 180, uv_fn=lambda az, r, z, arc: L.polar_uv(L.NOSE, az, r / R_FLAT * .22, 1.0))
P.mesh('cap', cap, M_h, smooth_angle=60)
P.mesh('cap_flat', flat, M_h)

det = Geo()
# inner liner seen from above once it has fallen away: dark foil over ribs
inner = [(R_RIM + .01, 0.0), (R_RIM - .01, -.015)]
for i in range(n, -1, -1):
    t = i / n
    r = R_FLAT + (R_RIM - .02 - R_FLAT) * t
    z = -DEPTH + .05 + (DEPTH - .05) * (t ** 1.7) * .96
    inner.append((r, z))
inner.append((0, -DEPTH + .05))
det.add(lathe(inner, 48, -180, 180, zone=Z.foil_dark))
# rib stiffeners on the back of the plug
for k in range(12):
    az = 30 * k + 15
    a = math.radians(az)
    pts = []
    for i in range(1, n):
        t = i / n
        r = R_FLAT + (R_RIM - .05 - R_FLAT) * t
        z = -DEPTH + .05 + (DEPTH - .05) * (t ** 1.7) * .96 + .03
        pts.append((r * math.sin(a), -r * math.cos(a), z))
    det.add(tube(pts, .022, 4, zone=Z.grey))
# adapter ring under the plug
det.add(lathe([(R_FLAT - .08, -DEPTH - .05), (R_FLAT + .02, -DEPTH - .05), (R_FLAT + .03, -DEPTH - .04), (R_FLAT + .03, -DEPTH + .03)], 48, -180, 180, zone=Z.bare))
det.add(bolt_ring(R_FLAT - .03, 24, zone=Z.steel), Rx(180) @ T(0, 0, DEPTH + .05))
# separation latches around the rim, with pyro boxes and pull-away connectors
for k in range(12):
    az = 30 * k
    a = math.radians(az)
    fr = T(R_RIM * math.sin(a) * .985, -R_RIM * math.cos(a) * .985, -.02) @ Rz(az)
    det.add(box(.12, .08, .05, zone=Z.white, bevel=.006, center=(0, 0, 0)), fr)
    det.add(box(.04, .03, .03, zone=Z.red, bevel=.003, center=(0, .05, .008)), fr)
# umbilical pull-away
det.add(box(.20, .10, .06, zone=Z.connector, bevel=.005, center=(0, 1.10, -.11)))
P.mesh('details', det, M_det)


def ring(r, z, nn=20):
    return [Vector((r * math.cos(TAU * i / nn), r * math.sin(TAU * i / nn), z)) for i in range(nn)]


cc = P.empty('colliders', parent=P.model)
P.hull_collider('col_cap', ring(R_RIM, -.01) + ring(R_RIM * .8, -DEPTH * .32) + ring(R_FLAT, -DEPTH - .05), parent=cc)

P.node('top', (0, 0, 0), (0, 0, 1), 3)
P.node('bottom', (0, 0, -DEPTH - .05), (0, 0, -1), 2)
P.bake_clips(0)
P.export(out)
P.save_blend(out)
