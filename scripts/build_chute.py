"""Twin canopies for the entry cap, as one transform because ModuleParachute drives a single canopy.
Same layout as stock: the canopy's local Y is its axis. Stowed, both collapse to nothing inside the crown."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from sl import *

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
P = Part('shab_TPSCanopy')
P.two_sided = True      # both faces of each dome are modelled below
M = P.material('shab_chute', spec=(.2, .2, .2), shininess=.1)
C = Zone(0, 0, 512, 512, atlas=512)
R, H, LN, OFF, PIVOT_Z = 2.4, 1.7, 6.0, 3.0, .10
ANCHOR = 1.0, -.05 - PIVOT_Z      # the crown canisters, in the canopy's frame
prof = [(R * math.cos(math.radians(i * 9)), LN + H * math.sin(math.radians(i * 9))) for i in range(11)]
prof[-1] = (0, LN + H)


def uvf(az, r, z, arc):
    return C.uv((az % 360) / 360, math.asin(min(1, (z - LN) / H)) / (math.pi / 2))


g = Geo()
for s in (-1, 1):
    g.add(lathe(prof, 32, -180, 180, uv_fn=uvf, flip=True), T(s * OFF, 0, PIVOT_Z))    # outside
    g.add(lathe(prof, 32, -180, 180, uv_fn=uvf), T(s * OFF, 0, PIVOT_Z))                # inside
    for k in range(12):
        a = TAU * k / 12
        g.add(tube([(s * ANCHOR[0], 0, PIVOT_Z + ANCHOR[1]), (s * OFF + R * math.cos(a), R * math.sin(a), PIVOT_Z + LN)], .018, 3, zone=C))
c = P.mesh('canopy', g, M, frame=T(0, 0, PIVOT_Z) @ Rx(90))
STOW = (.001, .001, .001); SEMI = (.08, .85, .08); FULL = (1, 1, 1)
c.scale = STOW
# the last clip keyed sets the exported rest pose
P.key('fullyDeployChute', c, 0, scale=SEMI); P.key('fullyDeployChute', c, 12, scale=FULL)
P.key('semiDeployChute', c, 0, scale=STOW); P.key('semiDeployChute', c, 18, scale=SEMI)
P.bake_clips()
P.export(out)
P.save_blend(out)
