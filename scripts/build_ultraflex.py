"""UltraFlex fan solar array (Cygnus Enhanced style). Folded fan pack on a two-section boom.
Deployed pose is authored; stowed pose comes from keyframes.
Part axes: +Z runs out along the boom. Sun-facing cell side is +Y (Unity +Z on the pivot)."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
from gr_power import *
import sm_layout as L

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(21)

P = Part('shab_UltraFlex')
M_fan = P.material('shab_fan', spec=(.9, .9, 1.0), shininess=.5)
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)
N = L.FAN_N
RG = L.FAN_R
RH = L.FAN_RH
GW = 360.0 / N
LA, LB = 1.20, 1.20
ROOT_Z = .12
HX = .05                    # root hinge and A axis sit off the tracking axis so B can run beside A when folded
GORE_Y = .07                # gore plane in front of the hub origin

FR = 240                    # clip length in frames (8 s)
OPEN_0, OPEN_1 = 96, 236    # fan opens here
HUB_T = LA + LB + ROOT_Z


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def Qy(deg):
    return Quaternion((0, 1, 0), math.radians(deg))


def Qx(deg):
    return Quaternion((1, 0, 0), math.radians(deg))


# ------------------------------------------------------------- static yoke, bearing drive
base = Geo()
base.add(cyl(.105, .018, 24, zone=Z.white, bevel=.004, center_z=False))
base.add(bolt_ring(.09, 10, zone=Z.steel), T(0, 0, .018))
base.add(cyl(.07, .05, 24, zone=Z.grey, bevel=.004, center_z=False), T(0, 0, .018))
base.add(lathe([(.075, .05), (.075, .068), (.066, .072)], 24, zone=Z.bare), T(0, 0, .018))
base.add(box(.07, .05, .05, zone=Z.access, bevel=.004, center=(.09, 0, .045)))
base.add(pipe_run([(.09, -.02, .02), (.13, -.05, .012), (.18, -.05, .006)], r=.006, zone=Z.black))
o_base = P.mesh('array_base', base, M_det)

pivot = P.empty('sunPivot', parent=P.model)

# rotating fork above the bearing, hinge pin along Y at HX
fork = Geo()
fork.add(cyl(.06, .018, 24, zone=Z.white, bevel=.003, center_z=False), T(0, 0, .072))
for s in (-1, 1):
    fork.add(box(.06, .012, .07, zone=Z.white, bevel=.003, center=(HX, s * .036, ROOT_Z - .01)))
fork.add(tube([(HX, -.046, ROOT_Z), (HX, .046, ROOT_Z)], .009, 10, zone=Z.steel))
P.mesh('array_fork', fork, M_det, parent=pivot)

# ------------------------------------------------------------- boom A (root hinge)
HA = Vector((HX, 0, ROOT_Z))
HE = Vector((HX, 0, ROOT_Z + LA))
frA = T(*HA)
a = Geo()
a.add(cyl(.024, LA - .10, 16, zone=Z.white, center_z=False), T(HX, 0, ROOT_Z + .05))
a.add(lathe([(.018, ROOT_Z + .01), (.03, ROOT_Z + .03), (.03, ROOT_Z + .06), (.024, ROOT_Z + .08)], 16, zone=Z.bare), T(HX, 0, 0))
a.add(box(.05, .05, .05, zone=Z.white, bevel=.005, center=(HX, 0, ROOT_Z + .03)))
a.add(lathe([(.03, HE.z - .08), (.03, HE.z - .03), (.018, HE.z - .012)], 16, zone=Z.bare), T(HX, 0, 0))
# elbow clevis
for s in (-1, 1):
    a.add(box(.05, .010, .05, zone=Z.white, bevel=.002, center=(HX, s * .03, HE.z - .012)))
a.add(cyl(.008, .07, 8, zone=Z.steel), T(HX, 0, HE.z) @ Rx(90))
# harness along the boom, clamped
path = [(HX + .03, 0, ROOT_Z + .04 + i * (LA - .1) / 8) for i in range(9)]
a.add(tube(path, .005, 5, zone=Z.black, caps=False))
for i in range(1, 8):
    a.add(box(.012, .03, .014, zone=Z.grey, center=(HX + .028, 0, ROOT_Z + .04 + i * (LA - .1) / 8)))
# pack cradle pad on the boom (holds the folded fan while stowed)
a.add(box(.055, .11, .012, zone=Z.rubber, center=(HX - .04, 0, ROOT_Z + LA * .55)))
oA = P.mesh('boomA', a, M_det, parent=pivot, frame=frA)

# ------------------------------------------------------------- boom B (elbow): runs on the tracking axis
frB = T(*HE)
bz0 = HE.z
bx = HX - HX               # B axis on the tracking axis, x = 0
b = Geo()
b.add(cyl(.020, LB - .09, 16, zone=Z.white, center_z=False), T(0, 0, bz0 + .05))
b.add(box(.055, .040, .06, zone=Z.white, bevel=.005, center=(.012, 0, bz0 + .025)))
b.add(lathe([(.016, bz0 + .05), (.027, bz0 + .06), (.027, bz0 + .09), (.020, bz0 + .10)], 16, zone=Z.bare))
b.add(lathe([(.020, HUB_T - .08), (.03, HUB_T - .06), (.03, HUB_T - .02), (.022, HUB_T)], 16, zone=Z.bare))
path = [(.026, 0, bz0 + .06 + i * (LB - .14) / 7) for i in range(8)]
b.add(tube(path, .0045, 5, zone=Z.black, caps=False))
for i in range(1, 7):
    b.add(box(.012, .028, .013, zone=Z.grey, center=(.025, 0, bz0 + .06 + i * (LB - .14) / 7)))
oB = P.mesh('boomB', b, M_det, parent=oA, frame=frB)

# ------------------------------------------------------------- hub
frH = T(0, 0, HUB_T)
oHub = P.empty('hub', frH, oB)
h = Geo()
to_y = Rx(-90)              # local +Z of a builder -> +Y (hub axis)
h.add(cyl(.098, GORE_Y + .012, 32, zone=Z.white, bevel=.004, center_z=False), frH @ to_y @ T(0, 0, -.01))
h.add(lathe([(.11, 0.0), (.11, .014), (.098, .018)], 32, zone=Z.grey), frH @ to_y @ T(0, 0, -.012))
# bearing and yoke saddle on the boom's end
h.add(box(.08, .05, .06, zone=Z.white, bevel=.006, center=(0, -.012, HUB_T - .03)))
h.add(bolt_ring(.092, 16, zone=Z.steel), frH @ to_y @ T(0, 0, GORE_Y + .002))
P.mesh('hub_body', h, M_det, parent=oHub, frame=frH)
hf = lathe([(.128, 0), (.11, .004), (.09, .006), (0, .006)], 32, uv_fn=lambda az, r, z, arc: L.fan_hub_uv(az, min(r, .125)))
hf2 = Geo(); hf2.add(hf, frH @ to_y @ T(0, 0, GORE_Y + .012))
P.mesh('hub_face', hf2, M_fan, parent=oHub, frame=frH, smooth_angle=40)


# ------------------------------------------------------------- gores
def gore_geo():
    """One 18 degree gore in the hub frame (origin at the hub centre, plane XZ, cells +Y),
    pointing along -X with its centre line."""
    g = Geo()
    half = math.radians(GW / 2)
    rads = [RH, .45, .9, 1.4, 1.8, RG]

    def pt(r_, a_):
        return Vector((-r_ * math.cos(a_), 0, r_ * math.sin(a_)))
    for i in range(len(rads) - 1):
        ra, rb = rads[i], rads[i + 1]
        q = [pt(ra, -half), pt(ra, half), pt(rb, half), pt(rb, -half)]
        lats = [-ra * math.sin(half), ra * math.sin(half), rb * math.sin(half), -rb * math.sin(half)]
        rd = [ra * math.cos(half), ra * math.cos(half), rb * math.cos(half), rb * math.cos(half)]
        lf = [L.fan_front_uv(lats[k], rd[k]) for k in range(4)]
        lb = [L.fan_back_uv(lats[k], rd[k]) for k in range(4)]
        oriented_quad(g, [p + Vector((0, .002, 0)) for p in q], lf, (0, 1, 0))
        oriented_quad(g, [p + Vector((0, -.002, 0)) for p in q], lb, (0, -1, 0))
        # rim and edge lips so the sheet has thickness at the silhouette
    return g


def gore_ribs():
    g = Geo()
    half = math.radians(GW / 2)

    def pt(r_, a_):
        return Vector((-r_ * math.cos(a_), 0, r_ * math.sin(a_)))
    # spar on the leading edge, tapered; rim cord; tip block
    g.add(tube([pt(RH * .9, half), pt(RG, half)], .007, 5, zone=Z.white, r_fn=lambda t: .009 - .005 * t))
    g.add(tube([pt(RG, -half), pt(RG, half)], .0038, 4, zone=Z.white))
    tip = pt(RG, half)
    g.add(box(.03, .014, .014, zone=Z.grey, bevel=.002, center=tuple(tip)))
    # inner hinge lug on the hub drum
    g.add(box(.05, .014, .022, zone=Z.grey, bevel=.002, center=tuple(pt(RH + .018, half))))
    return g


hub_rest = frH @ T(0, GORE_Y, 0)
gore0 = gore_geo()
ribs0 = gore_ribs()
gores = []
for k in range(N):
    final = k * GW
    fr = frH @ T(0, GORE_Y, 0) @ Ry(final)
    wrapper = P.empty(f'gore_{k:02d}', fr, oHub)
    gg = Geo(); gg.add(gore0, fr)
    P.mesh(f'gore_{k:02d}_sheet', gg, M_fan, parent=wrapper, frame=fr, smooth_angle=20)
    rr = Geo(); rr.add(ribs0, fr)
    P.mesh(f'gore_{k:02d}_ribs', rr, M_det, parent=wrapper, frame=fr, smooth_angle=50)
    gores.append(wrapper)

catcher = P.empty('sunCatcher', frH @ T(0, GORE_Y + .03, 0), oHub)

# ------------------------------------------------------------- keys
DELTA = .35                                 # stowed fan spread per gore, degrees
STACK = .0034                               # stowed stack spacing along the hub axis, metres
Gfinal = GW - DELTA

for k, g in enumerate(gores):
    ry_final = g.rotation_quaternion.copy() if False else Qy(k * GW)
    y_final = GORE_Y
    # pull string: the outermost gore moves first, each following once the one ahead of it has taken up its share
    lead_tot = (N - 1) * Gfinal
    frames = list(range(OPEN_0, OPEN_1 + 1, 7)) + [OPEN_1]
    P.key('deploy', g, 0, rotation_quaternion=Qy(k * DELTA), location=Vector((0, GORE_Y + k * STACK, 0)))
    for fi in sorted(set(frames)):
        t = (fi - OPEN_0) / (OPEN_1 - OPEN_0)
        lead = lead_tot * ease(t)
        ang = k * DELTA + max(0.0, lead - (N - 1 - k) * Gfinal)
        P.key('deploy', g, fi, rotation_quaternion=Qy(ang), location=Vector((0, GORE_Y + k * STACK * (1 - ease(t)), 0)))
    P.key('deploy', g, FR, rotation_quaternion=Qy(k * GW), location=Vector((0, GORE_Y, 0)))

# boom A: folded 90 deg, unfolds over the first third
def alpha(f):
    return -90 * (1 - ease(f / 70.0))


def beta(f):
    return 180 * (1 - ease(f / 82.0))


def pack(f):
    # world orientation of the fan pack: flat against the hull until the booms are up, then edge-on
    return Qx(90 * (1 - ease((f - 62) / 34.0)))


for f in sorted(set(list(range(0, 97, 6)) + [FR])):
    P.key('deploy', oA, f, rotation_quaternion=Qy(alpha(f)))
    P.key('deploy', oB, f, rotation_quaternion=Qy(beta(f)))
    comp = Qy(alpha(f) + beta(f)).inverted() @ pack(f)
    P.key('deploy', oHub, f, rotation_quaternion=comp)

# ------------------------------------------------------------- colliders (booms and hub; sheets stay collider-free, as stock arrays' panels usually do on the fragile area)
P.hull_collider('col_base', [Vector((.10 * math.cos(TAU * i / 12), .10 * math.sin(TAU * i / 12), z)) for i in range(12) for z in (0, .09)])
P.hull_collider('col_boomA', [HA + Vector((sx * .03, sy * .03, dz)) for sx in (-1, 1) for sy in (-1, 1) for dz in (0, LA)], parent=oA, frame=frA)
P.hull_collider('col_boomB', [HE + Vector((sx * .03 - HX, sy * .03, dz)) for sx in (-1, 1) for sy in (-1, 1) for dz in (.02, LB)], parent=oB, frame=frB)
P.hull_collider('col_hub', [Vector((.12 * math.cos(TAU * i / 10), v, HUB_T + .12 * math.sin(TAU * i / 10))) for i in range(10) for v in (-.02, GORE_Y + .02)], parent=oHub, frame=frH)

P.node('bottom', (0, 0, 0), (0, 0, -1), 1)
P.bake_clips(0)
P.export(out)
P.save_blend(out)
