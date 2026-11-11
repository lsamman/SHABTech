"""shab_HIAD: 16 m hypersonic inflatable decelerator (paper fig. 3, 7). Four ring groups carry the
windward skin, tori and straps; each scales between a nested stowed pack and the open cone. The hub
stays open so the lander's engines fire through it."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
from gr_lander import copv
import ll as L

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(13)

P = Part('shab_HIAD')
M_h = P.material('shab_hiad', spec=(.5, .5, .5), shininess=.2)
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)
N_ANIM = 180
COSS, SINS = math.cos(L.SLOPE), math.sin(L.SLOPE)
S_TOTAL = L.GROUP_S[-1]


def skin_section(s0, s1, gores=12):
    """Windward fabric between two stations on the cone: profile runs outward so it faces down."""
    g = Geo()
    ns = 4
    prof = [L.cone_rz(s0 + (s1 - s0) * i / ns) for i in range(ns + 1)]
    for k in range(gores):
        a0 = k * 360.0 / gores
        a1 = a0 + 360.0 / gores

        def uv(az, r, z, arc, a0=a0, a1=a1):
            s_ = s0 + arc
            return L.rect_uv(L.SKIN, (az - a0) / (a1 - a0), 1 - s_ / S_TOTAL)
        g.add(lathe(prof, 8, a0, a1, uv_fn=uv))
    return g


def back_section(s0, s1):
    """Grey back cover under the tori, facing up (profile runs inward)."""
    ns = 3
    prof = [L.cone_rz(s1 - (s1 - s0) * i / ns, .012) for i in range(ns + 1)]
    g = Geo()
    for k in range(8):
        a0 = k * 45.0

        def uv(az, r, z, arc, a0=a0):
            return L.rect_uv(L.BACK, (az - a0) / 45.0, min(.999, arc / (s1 - s0 + 1e-6)))
        g.add(lathe(prof, 8, a0, a0 + 45, uv_fn=uv))
    return g


def torus(R, z0, m, tiles=16, rows=10, cols=6):
    prof = []
    for i in range(rows + 1):
        a = -math.pi / 2 + TAU * i / rows
        prof.append((R + m * math.cos(a), z0 + m * math.sin(a)))
    g = Geo()
    circ = TAU * m
    for k in range(tiles):
        a0 = k * 360.0 / tiles
        a1 = a0 + 360.0 / tiles

        def uv(az, r, z, arc, a0=a0, a1=a1):
            return L.rect_uv(L.BRAID, (az - a0) / (a1 - a0), min(.999, arc / circ))
        g.add(lathe(prof, cols, a0, a1, uv_fn=uv))
    return g


def surface_height(s, tori):
    """Height above the skin of whatever a strap lies on at station s."""
    h = .016
    for nm, si, m, off, grp in tori:
        d = abs(s - si)
        if d < m:
            h = max(h, off + m + math.sqrt(m * m - d * d) - m + m * 0 + .012 + m * 0)
    return h


def strap_section(s0, s1, tori, n_straps=24, width=.075, samples=12):
    """Kevlar radial straps riding over the tori of this group: flat ribbons facing up."""
    g = Geo()
    zn = Z.kevlar
    for j in range(n_straps):
        az = j * 360.0 / n_straps + 3.0
        a = math.radians(az)
        rad = Vector((math.sin(a), -math.cos(a), 0))
        tan = Vector((math.cos(a), math.sin(a), 0))
        base = len(g.v)
        for i in range(samples + 1):
            s = s0 + (s1 - s0) * i / samples
            r, z = L.cone_rz(s, surface_height(s, tori))
            c = rad * r + Vector((0, 0, z))
            g.v.append(tuple(c - tan * width / 2)); g.v.append(tuple(c + tan * width / 2))
        for i in range(samples):
            v0, v1 = base + 2 * i, base + 2 * i + 1
            v2, v3 = base + 2 * i + 2, base + 2 * i + 3
            t0, t1 = (i % 8) / 8, (i % 8 + 1) / 8
            # inward as i grows downward: winding gives an upward normal
            g.face([v0, v2, v3, v1], [zn.uv(0, t0), zn.uv(0, t1), zn.uv(1, t1), zn.uv(1, t0)])
    return g


groups = []
for k in range(4):
    s0, s1 = L.GROUP_S[k], L.GROUP_S[k + 1]
    tori = [t for t in L.TORUS if t[4] == k]
    g = Geo()
    g.add(skin_section(s0, s1))
    g.add(back_section(s0, s1))
    for nm, si, m, off, grp in tori:
        r, z = L.cone_rz(si, off + m)
        g.add(torus(r, z, m))
    o = P.mesh(f'ring{k}', g, M_h, smooth_angle=55)
    st = strap_section(s0, s1, tori)
    # hoop cords binding each torus, the fig. 3 "supporting composite braiding"
    for nm, si, m, off, grp in tori:
        r, z = L.cone_rz(si, off + m * 1.98)
        st.add(tube(arc_path((0, 0), r, 0, 360, n=72, z=z), .009, 4, zone=Z.kevlar, closed=True, caps=False))
    o2 = P.mesh(f'straps{k}', st, M_det, smooth_angle=50)
    a, b, target = L.STOW[k]
    z0 = L.cone_rz(s0)[1]
    c = target - b * z0
    # stagger: the outer groups lead, the inner ones follow
    f0 = int(N_ANIM * (.30 - k * .10))
    f1 = int(N_ANIM * (.75 + k * .08333))
    for ob in (o, o2):
        P.key('hiadInflate', ob, 0, scale=Vector((a, a, b)), location=Vector((0, 0, c)))
        if f0 > 0:
            P.key('hiadInflate', ob, f0, scale=Vector((a, a, b)), location=Vector((0, 0, c)))
        P.key('hiadInflate', ob, f1, scale=Vector((1, 1, 1)), location=Vector((0, 0, 0)))
        if f1 < N_ANIM:
            P.key('hiadInflate', ob, N_ANIM, scale=Vector((1, 1, 1)), location=Vector((0, 0, 0)))
    groups.append((o, o2))
    print(f'group {k}: stowed r {a * L.cone_rz(s0)[0]:.3f}..{a * L.cone_rz(s1)[0]:.3f}, deployed r {L.cone_rz(s0)[0]:.3f}..{L.cone_rz(s1)[0]:.3f}, tori {[t[0] for t in tori]}')

# ---- stowage band: wraps the pack when stowed (fig. 4's dark ring), becomes the grey rim (fig. 7)
Rr = L.STOW_OUT_R
rim = Geo()
for k in range(4):
    a0 = k * 90.0

    def uv_band(az, r, z, arc, a0=a0):
        return L.rect_uv(L.RIMZ, (az - a0) / 90.0, (z + L.RIM_H) / L.RIM_H)
    rim.add(lathe([(Rr - .02, -L.RIM_H), (Rr, -L.RIM_H + .02), (Rr, -.02), (Rr - .02, 0)], 24, a0, a0 + 90, uv_fn=uv_band))
for k in range(8):
    a0 = k * 45.0

    def uv_led(az, r, z, arc, a0=a0):
        return L.rect_uv(L.BACK, (az - a0) / 45.0, min(.999, arc / .5))
    rim.add(lathe([(Rr - .02, 0), (L.DECK_R + .03, 0)], 10, a0, a0 + 45, uv_fn=uv_led))
    rim.add(lathe([(Rr - .18, -L.RIM_H + .01), (Rr - .02, -L.RIM_H)], 10, a0, a0 + 45, uv_fn=uv_led))
# inner wall and ceiling of the pack, in the dark back-cover tone. Without them a view up past the lowest ring meets
# only faces pointing away, which KSP doesn't draw, so the sky shows through the gap under the rim. The ceiling
# stops under the top ledge so its upper side never shows, stowed or deployed.
dark_uv = L.rect_uv(L.BACK, .5, .985)
rim.add(lathe([(L.DECK_R + .03, -.02), (Rr - .03, -.02), (Rr - .03, -L.RIM_H + .012)], 72, 0, 360, uv_fn=lambda az, r, z, arc: dark_uv))
o_rim = P.mesh('rim', rim, M_h, smooth_angle=45)
P.key('hiadInflate', o_rim, 0, scale=Vector((1, 1, 1)), location=Vector((0, 0, 0)))
P.key('hiadInflate', o_rim, int(N_ANIM * .9), scale=Vector((L.RIM_A, L.RIM_A, L.RIM_B)), location=Vector((0, 0, L.RIM_DEPLOY_Z)))
P.key('hiadInflate', o_rim, N_ANIM, scale=Vector((L.RIM_A, L.RIM_A, L.RIM_B)), location=Vector((0, 0, L.RIM_DEPLOY_Z)))

# ---- hub: fixed ring around the engine opening
Zb = L.BOTTOM_NODE_Z


def hub_uv(az, r, z, arc):
    return L.rect_uv(L.HUBZ, ((az + 180) % 45) / 45.0, min(.999, (arc * .8) % 1))


hub = Geo()
hub.add(lathe([(L.HUB_R, Zb), (L.CONE_R0 + .04, Zb), (L.CONE_R0 + .04, Zb + .03), (L.CONE_R0 + .005, Zb + .05), (L.CONE_R0 + .005, -.03), (L.CONE_R0 + .09, -.02), (L.CONE_R0 + .09, 0), (L.HUB_R - .05, 0), (L.HUB_R - .05, -.02), (L.HUB_R, -.03), (L.HUB_R, Zb)], 72, -180, 180, uv_fn=hub_uv))
P.mesh('hub', hub, M_h, smooth_angle=40)

det = Geo()
det.add(bolt_ring(L.CONE_R0 + .05, 48, zone=Z.steel), T(0, 0, 0))
det.add(bolt_ring(L.CONE_R0 + .015, 36, zone=Z.steel), T(0, 0, Zb + .03))
# inflation system on the inside of the hub wall, visible through the engine opening
bottle = copv(.085)
for k in range(8):
    az = 45 * k
    fr = on_cyl(az, -.30, L.HUB_R) @ Ry(180)
    det.add(bottle, fr @ Rz(0))
    # valve box and regulator above each bottle
    det.add(box(.13, .09, .05, zone=Z.grey, bevel=.005, center=(0, .25, .025)), fr)
    det.add(cyl(.018, .05, 8, zone=Z.bare, center_z=False), fr @ T(.04, .25, .05))
    det.add(tube([(0, .17, .05), (0, .205, .05)], .010, 6, zone=Z.copper), fr)
    # hose through the wall to T1
    det.add(tube([(-.09, .25, .03), (-.15, .25, .02), (-.17, .20, .005)], .008, 6, zone=Z.copper), fr)
# manifold ring and pressure lines
det.add(tube(arc_path((0, 0), L.HUB_R - .025, 0, 360, n=72, z=Zb + .34), .012, 6, zone=Z.copper, closed=True, caps=False))
det.add(tube(arc_path((0, 0), L.HUB_R - .025, 0, 360, n=72, z=-.08), .009, 6, zone=Z.bare, closed=True, caps=False))
for k in range(16):
    az = 22.5 * k + 11.25
    fr = on_cyl(az, Zb + .34, L.HUB_R)
    det.add(box(.03, .03, .03, zone=Z.grey, center=(0, 0, -.015)), fr)
# outer hub: valve panels and feed hoses to T1 (seen once inflated)
for k in range(8):
    az = 45 * k + 22.5
    fr = on_cyl(az, -.26, L.CONE_R0 + .005)
    det.add(junction_box(.12, .10, .03), fr)
    pts = [fr @ Vector((0, -.05, .03)), fr @ Vector((0, -.10, .10)), fr @ Vector((0, -.18, .13))]
    det.add(tube(pts, .012, 6, zone=Z.rubber))
P.mesh('hub_details', det, M_det)


# ---- colliders. Inner ring stays put; outer ring scales with the fabric, like stock's ColliderScaler.
# Nothing inside HUB_R, so the engine plumes stay clear.
def sector_pts(a0, a1, r0, z0, r1, z1, top):
    pts = []
    for az in (a0, (a0 + a1) / 2, a1):
        a = math.radians(az)
        for r, z in ((r0, z0), (r1, z1)):
            pts.append(Vector((r * math.sin(a), -r * math.cos(a), z)))
            pts.append(Vector((r * math.sin(a), -r * math.cos(a), z + top)))
    return pts


cc = P.empty('colliders', parent=P.model)
R_SPLIT = 2.72
z_split = L.CONE_Z0 + (R_SPLIT - L.CONE_R0) * math.tan(L.SLOPE)
for k in range(12):
    a0, a1 = k * 30.0, (k + 1) * 30.0
    P.hull_collider(f'col_inner{k}', sector_pts(a0, a1, L.HUB_R, Zb, R_SPLIT, z_split, .10), parent=cc)
outer = P.empty('colliderScaler', parent=cc)
zo = L.cone_rz(S_TOTAL)[1]
for k in range(16):
    a0, a1 = k * 22.5, (k + 1) * 22.5
    P.hull_collider(f'col_outer{k}', sector_pts(a0, a1, R_SPLIT, z_split, L.HIAD_OUT_R, zo, .34), parent=outer)
# stowed: outer ring scales into the band envelope (r 1.73..2.925), z packed against the deck
aS = L.STOW_OUT_R / L.HIAD_OUT_R
bS = (L.RIM_H - .10) / (zo - z_split + .34)
cS = -L.RIM_H - bS * z_split
P.key('hiadInflate', outer, 0, scale=Vector((aS, aS, bS)), location=Vector((0, 0, cS)))
P.key('hiadInflate', outer, int(N_ANIM * .9), scale=Vector((1, 1, 1)), location=Vector((0, 0, 0)))
P.key('hiadInflate', outer, N_ANIM, scale=Vector((1, 1, 1)), location=Vector((0, 0, 0)))
print('outer collider stowed r', round(R_SPLIT * aS, 3), '..', round(L.HIAD_OUT_R * aS, 3))
assert R_SPLIT * aS > 1.48, 'stowed outer collider would reach the plumes'

P.node('top', (0, 0, 0), (0, 0, 1), 3)
P.node('bottom', (0, 0, Zb), (0, 0, -1), 3)
P.bake_clips(0)
P.export(out)
P.save_blend(out)
