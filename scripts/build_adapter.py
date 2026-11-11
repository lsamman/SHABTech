"""shab_Adapter: truss interstage from the nose plug's ring (r 0.75) to a 2.5 m Falcon upper stage."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
from gr_lander import copv, junction_box
import ll as L

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(19)
P = Part('shab_Adapter')
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)

R_TOP, R_BOT, H = .75, 1.25, .62
det = Geo()
# top ring, bottom ring with a stringered skirt (white metal)
det.add(lathe([(R_TOP - .08, -.03), (R_TOP + .025, -.03), (R_TOP + .025, -.008), (R_TOP + .015, 0), (R_TOP - .08, 0)], 48, zone=Z.white))
det.add(lathe([(R_TOP - .08, 0), (R_TOP - .08, -.03)], 48, zone=Z.grey))
det.add(bolt_ring(R_TOP - .03, 24, zone=Z.steel), T(0, 0, 0))
skirt_top = -H + .14
det.add(lathe([(R_BOT - .10, -H), (R_BOT, -H), (R_BOT + .01, -H + .012), (R_BOT + .005, skirt_top - .02), (R_BOT - .03, skirt_top), (R_BOT - .10, skirt_top)], 64, zone=Z.white))
det.add(lathe([(R_BOT - .10, skirt_top), (R_BOT - .10, -H)], 64, zone=Z.grey))
for k in range(32):
    az = 11.25 * k
    det.add(box(.016, .10, .012, zone=Z.grey, bevel=.002, center=(0, 0, .005)), on_cyl(az, -H + .07, R_BOT + .003))
# X-braced truss of tubes with end fittings
NB = 12
for k in range(NB):
    a0 = 360.0 * k / NB
    a1 = 360.0 * (k + 1) / NB
    r0, r1 = R_TOP - .01, R_BOT - .06
    z0, z1 = -.03, skirt_top

    def P_(az, r, z):
        a = math.radians(az)
        return Vector((r * math.sin(a), -r * math.cos(a), z))
    for (azA, azB) in ((a0, a1), (a1, a0)):
        pa, pb = P_(azA, r0, z0), P_(azB, r1, z1)
        d = (pb - pa)
        det.add(tube([pa + d * .05, pb - d * .05], .018, 8, zone=Z.white))
        det.add(tube([pa, pa + d * .07], .027, 8, zone=Z.grey))
        det.add(tube([pb - d * .07, pb], .027, 8, zone=Z.grey))
    # longeron
    det.add(tube([P_(a0, r0, z0), P_(a0, r1, z1)], .022, 8, zone=Z.grey))
# umbilical run and avionics on the skirt
for az in (20, 200):
    det.add(junction_box(.16, .09, .03), on_cyl(az, -H + .07, R_BOT + .004))
det.add(cable_bundle([tuple(on_cyl(40, -H + .10, R_BOT + .03).translation), tuple(on_cyl(35, skirt_top + .1, R_BOT - .02).translation), tuple(on_cyl(25, -.05, R_TOP + .06).translation)], r=.008, n=3))

# four retro motors on the skirt, nozzles angled up and out, away from the plug
motors = Geo()
for az in (45, 135, 225, 315):
    fr = on_cyl(az, -H + .10, R_BOT - .02)
    a = math.radians(az)
    out_ = Vector((math.sin(a), -math.cos(a), 0))
    axis = (Vector((0, 0, 1)) * .9 + out_ * .42).normalized()
    pos = fr.translation + out_ * .10
    mf = frame_axes(pos, axis)
    motors.add(cyl(.05, .24, 12, zone=Z.white, bevel=.008, center_z=False), mf @ T(0, 0, -.20))
    motors.add(lathe([(.018, .04), (.05, .04), (.052, .10), (.045, .10), (.012, .05), (0, .05)][::1], 12, zone=Z.dark), mf)
    motors.add(box(.05, .05, .13, zone=Z.grey, bevel=.004, center=(0, 0, -.09)), mf @ T(0, -.06, 0) if False else fr @ T(0, 0, .05))
    P.empty('thrustTransform', frame_axes(mf @ Vector((0, 0, .10)), axis), P.model)
P.mesh('truss', det, M_det, smooth_angle=45)
P.mesh('motors', motors, M_det)


def ring(r, z, nn=20):
    return [Vector((r * math.cos(TAU * i / nn), r * math.sin(TAU * i / nn), z)) for i in range(nn)]


cc = P.empty('colliders', parent=P.model)
P.hull_collider('col_adapter', ring(R_TOP + .02, 0) + ring(R_BOT, -H), parent=cc)
P.node('top', (0, 0, 0), (0, 0, 1), 2)
P.node('bottom', (0, 0, -H), (0, 0, -1), 3)
P.bake_clips(0)
P.export(out)
P.save_blend(out)
