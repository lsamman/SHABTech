"""shab_ReactorRover: paper section III-G. A 100 kWe fission power cart: chassis, reactor with
reflector drums, Stirling converters, rear shadow shield facing the hab, umbrella heat-pipe
radiator, HV cable drum and fairlead, control box, comm whip, tie-downs, four wheel nodes.
Forward is +Y (Unity +Z). The rover drives away from the hab, paying cable out the back."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
from gr_surface import *
from surface_layout import *

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(23)

P = Part('shab_ReactorRover')
M_rov = P.material('shab_rover')
M_sf = P.material('shab_surface', spec=(.9, .9, .9), shininess=.3)
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)
M_lamp = P.material('shab_details', shader='KSP/Emissive/Bumped Specular', nrm='shab_details', emissive='shab_lamp_emit', name='lamp')

CX, CY, CZ = CH_X, CH_Y, CH_Z
TOP = CZ
RY0 = -.05              # reactor axis Y
NODE_Z = .08            # wheel mount plate underside
WX, WY = .76, .60       # wheel station
Z_WHEEL_NODE = .46      # wheel part's node height above its hub
GROUND_Z = NODE_Z - Z_WHEEL_NODE - .28

d = Geo()     # details atlas
s = Geo()     # surface sheet

# ---------------------------------------------------------------- chassis
chassis = boxmap(-CX, CX, -CY, CY, -CZ, CZ, .014, dict(top=RZ['deck'], bottom=RZ['belly'], xp=RZ['sideR'], xn=RZ['sideL'], yp=RZ['front'], yn=RZ['rear']))

# outriggers: paired box beams with a diagonal brace, plate on top of each wheel station
for sx_ in (-1, 1):
    for sy_ in (-1, 1):
        wx, wy = sx_ * WX, sy_ * WY
        for dy in (-.075, .075):
            d.add(prism((sx_ * (CX - .01), wy + dy, .05), (wx + sx_ * .06, wy + dy, NODE_Z + .022), .05, .044, zone=Z.white))
        d.add(prism((sx_ * (CX - .01), wy, -.09), (wx - sx_ * .02, wy, NODE_Z + .004), .035, .022, up=(0, 1, 0), zone=Z.grey))
        d.add(box(.24, .26, .014, zone=Z.white, bevel=.003, center=(wx, wy, NODE_Z + .007)))
        d.add(box(.20, .05, .022, zone=Z.white, bevel=.004, center=(wx, wy, NODE_Z + .038)))
        for bx in (-1, 1):
            for by in (-1, 1):
                d.add(cyl(.008, .006, 6, zone=Z.steel, center_z=False), T(wx + bx * .09, wy + by * .10, NODE_Z + .014))
        # wheel motor lead from the belly to the steering housing
        d.add(tube(smooth_path([(sx_ * (CX - .005), wy - sy_ * .12, -.03), (sx_ * (CX + .08), wy - sy_ * .12, .0), (wx - sx_ * .02, wy - sy_ * .1, NODE_Z - .01)]), .0055, 5, zone=Z.orange))

# tie-downs: four pyro release brackets on the chassis sides, with a lug for the deck
for sx_ in (-1, 1):
    for y_ in (-.32, .32):
        fr = facing((sx_ * CX, y_, -.06), (sx_, 0, 0))
        d.add(box(.075, .055, .012, zone=Z.grey, bevel=.002, center=(0, 0, .006)), fr)
        d.add(cyl(.016, .03, 10, zone=Z.yellow, bevel=.003, center_z=False), fr @ T(0, 0, .012))
        d.add(cyl(.009, .012, 8, zone=Z.red, center_z=False), fr @ T(0, 0, .042))
        d.add(tube([(0, -.018, .03), (.0, -.048, .012)], .004, 5, zone=Z.yellow), fr)

# deck handrails, front half and along the sides of the reactor
for sx_ in (-1, 1):
    fr = facing((sx_ * (CX - .03), .14, TOP), (0, 0, 1), up=(0, 1, 0))
    d.add(handrail(.34, standoff=.075, bar=.012), fr)

# ---------------------------------------------------------------- reactor base and converters
d.add(cyl(.37, .03, 36, zone=Z.grey, bevel=.006, center_z=False), T(0, RY0, TOP))
d.add(bolt_ring(.345, 24), T(0, RY0, TOP + .03))
s.add(lathe([(.20, TOP + .03), (.24, TOP + .03), (.24, TOP + .05), (.205, TOP + .075), (.20, .24)], 36, zone=SZ['flange'], uv_fn=lambda az, r, z, arc: SZ['stirling'].uv(az / 360, .05)), T(0, RY0, 0))

# vessel: dull Inconel with welded head (paper: "reactor"; form follows Kilopower-class designs)
vp = [(.20, .24), (.20, .86), (.19, .91), (.16, .955), (.11, .99), (.05, 1.01), (0, 1.015)]
s.add(lathe(vp, 40, zone=SZ['vessel']), T(0, RY0, 0))

# six reflector drums with actuators, control rods exposed at the top
for k in range(6):
    a = 30 + 60 * k
    fr = on_cyl(a, 0, .245); ctr = fr.translation + Vector((0, RY0, 0))
    d.add(cyl(.04, .58, 16, zone=Z.steel, bevel=.004, center_z=False), T(ctr.x, ctr.y, .27))
    d.add(cyl(.031, .09, 12, zone=Z.dark, bevel=.004, center_z=False), T(ctr.x, ctr.y, .85))
    d.add(cyl(.012, .03, 8, zone=Z.bare, center_z=False), T(ctr.x, ctr.y, .94))
    # drum clamp bands
    for z_ in (.34, .76):
        d.add(cyl(.0435, .014, 16, zone=Z.grey, center_z=False), T(ctr.x, ctr.y, z_))
    # actuator power line down to the base
    p0 = on_cyl(a + 12, 0, .275).translation + Vector((0, RY0, 0))
    d.add(tube([(ctr.x, ctr.y, .90), (p0.x, p0.y, .88), (p0.x, p0.y, .28)], .0035, 4, zone=Z.black))

# four free-piston Stirling converters, radial at the base, with copper fin coolers
for az in (62, 118, 242, 298):
    fr = on_cyl(az, .205, .20)
    fr.translation += Vector((0, RY0, 0))
    s.add(lathe([(0, 0), (.047, 0), (.052, .01), (.052, .22), (.044, .245), (.022, .258), (0, .26)], 18, zone=SZ['stirling']), fr)
    d.add(fin_stack(.046, .066, 6, .015, .004, Z.copper, seg=18), fr @ T(0, 0, .16))
    # hot-end pipe to the vessel
    p = fr @ Vector((0, .03, .02))
    d.add(tube([tuple(p), tuple(fr @ Vector((0, .15, -.01)))], .010, 8, zone=Z.copper))

# ---------------------------------------------------------------- manifold ring, feeds, instrument cap
RING_R, RING_Z = .305, 1.13
ring = [(RING_R * math.sin(TAU * i / 36), RY0 - RING_R * math.cos(TAU * i / 36), RING_Z) for i in range(36)]
d.add(tube(ring, .018, 8, zone=Z.grey, closed=True))
for k in range(6):
    a = 60 * k
    tip = on_cyl(a, RING_Z, RING_R).translation + Vector((0, RY0, 0))
    root = on_cyl(a, .985, .085).translation + Vector((0, RY0, 0))
    mid = on_cyl(a, 1.09, .17).translation + Vector((0, RY0, 0))
    d.add(tube(smooth_path([tuple(root), tuple(mid), tuple(tip)]), .0115, 6, zone=Z.copper))
    # hinge clevis on the ring
    fr = on_cyl(a, RING_Z + .004, RING_R + .018)
    fr.translation += Vector((0, RY0, 0))
    for dx in (-.09, .09):
        d.add(box(.018, .035, .05, zone=Z.grey, bevel=.003, center=(dx, 0, .004)), fr)
d.add(cyl(.095, .08, 20, zone=Z.white, bevel=.006, center_z=False), T(0, RY0, 1.015))
d.add(cyl(.045, .03, 12, zone=Z.dark, bevel=.004, center_z=False), T(0, RY0, 1.095))
d.add(bolt_ring(.082, 12), T(0, RY0, 1.095))

# ---------------------------------------------------------------- shadow shield, facing the hab (rear)
SH_Y0, SH_Y1 = -.49, -.43
SH_W, SH_Z1 = .96, 1.08
s.add(box(SH_W, SH_Y1 - SH_Y0, SH_Z1 - TOP, zone=SZ['chassis'], bevel=.01, center=(0, (SH_Y0 + SH_Y1) / 2, (TOP + SH_Z1) / 2)))
s.add(quad_patch(SH_W - .03, SH_Z1 - TOP - .03, SZ['shield']), facing((0, SH_Y0 - .001, (TOP + SH_Z1) / 2), (0, -1, 0)))
# raised shield plates on the reactor side, wedge-thickening the middle
s.add(box(SH_W * .62, .04, (SH_Z1 - TOP) * .84, zone=SZ['chassis'], bevel=.008, center=(0, SH_Y1 + .02, TOP + (SH_Z1 - TOP) * .47)))
for sx_ in (-1, 1):
    # triangular gusset braces against the deck, forward side
    d.add(prism((sx_ * (SH_W / 2 - .03), SH_Y1, SH_Z1 - .25), (sx_ * (SH_W / 2 - .03), SH_Y1 + .26, TOP + .01), .02, .036, up=(1, 0, 0), zone=Z.grey))
    d.add(box(.09, .04, .012, zone=Z.grey, center=(sx_ * (SH_W / 2 - .03), SH_Y1 + .26, TOP + .006)))
    # lifting eye
    d.add(cyl(.018, .025, 10, zone=Z.yellow, center_z=False), T(sx_ * (SH_W / 2 - .09), (SH_Y0 + SH_Y1) / 2, SH_Z1))
s.add(quad_patch(.14, .14, SZ['trefoil']), facing((.30, SH_Y1 + .0015 + .04, TOP + .26), (0, 1, 0)))

# ---------------------------------------------------------------- HV cable drum (rotating) and fairlead
DR_Y, DR_Z = -.645, TOP + .19
DR_W = .50
drum = Geo()
# wound cable: lathe about X; U around, V across so the helix texture runs across the width
drum.add(x_axis(lathe([(.07, -DR_W / 2 + .018), (.125, -DR_W / 2 + .018), (.135, -DR_W / 2 + .05), (.135, DR_W / 2 - .05), (.125, DR_W / 2 - .018), (.07, DR_W / 2 - .018)], 36, zone=SZ['cable'])))
for sx_ in (-1, 1):
    # flange with lightening holes in the normal map
    fz = sx_ * (DR_W / 2 - .009)
    fp = [(.0, fz - .009 * sx_), (.155, fz - .009 * sx_), (.158, fz - .004 * sx_), (.158, fz + .004 * sx_), (.155, fz + .009 * sx_), (0, fz + .009 * sx_)]
    if sx_ < 0:
        fp = fp[::-1]
    drum.add(x_axis(lathe(fp, 36, uv_fn=lambda az, r, z, arc: SZ['flange'].uv(.5 + .5 * r / .16 * math.sin(math.radians(az)), .5 + .5 * r / .16 * math.cos(math.radians(az))))))
drum.add(x_axis(cyl(.022, DR_W + .10, 12, zone=SZ['vessel'])))
drum_w = Geo(); drum_w.add(drum, T(0, DR_Y, DR_Z))
for sx_ in (-1, 1):
    bx = sx_ * (DR_W / 2 + .035)
    # bearing pedestals
    d.add(prism((bx, DR_Y - .05, TOP), (bx, DR_Y, DR_Z), .03, .05, up=(1, 0, 0), zone=Z.grey))
    d.add(prism((bx, DR_Y + .05, TOP), (bx, DR_Y, DR_Z), .03, .05, up=(1, 0, 0), zone=Z.grey))
    d.add(x_axis(cyl(.045, .034, 16, zone=Z.white, bevel=.004)), T(bx, DR_Y, DR_Z))
# take-up motor on one end, feed line on the other
d.add(x_axis(cyl(.052, .14, 16, zone=Z.white, bevel=.006)), T(DR_W / 2 + .13, DR_Y, DR_Z))
d.add(x_axis(fin_stack(.04, .058, 7, .011, .004, Z.grey, seg=16)), T(DR_W / 2 + .155, DR_Y, DR_Z))
d.add(tube(smooth_path([(-DR_W / 2 - .06, DR_Y, DR_Z), (-DR_W / 2 - .09, DR_Y + .04, DR_Z - .05), (-.34, DR_Y + .2, TOP + .02), (-.34, SH_Y1 + .05, TOP + .02), (-.24, RY0 - .24, TOP + .03)]), .012, 8, zone=Z.orange))
# fairlead: frame with two horizontal and two vertical rollers at the rear edge
FL_Y, FL_Z = -CY - .015, TOP + .075
for sx_ in (-1, 1):
    d.add(box(.018, .04, .15, zone=Z.grey, bevel=.003, center=(sx_ * .075, FL_Y, FL_Z - .02)))
    d.add(cyl(.013, .10, 10, zone=Z.steel, center_z=True), T(sx_ * .05, FL_Y, FL_Z))
for dz in (-.042, .042):
    d.add(x_axis(cyl(.013, .10, 10, zone=Z.steel)), T(0, FL_Y, FL_Z + dz))
d.add(box(.18, .05, .014, zone=Z.grey, bevel=.003, center=(0, FL_Y, TOP + .004)))
# paid-out cable from drum to the fairlead, fixed run (the KAS hose takes over at the fairlead)
d.add(tube([(0, DR_Y - .10, DR_Z + .03), (0, FL_Y + .02, FL_Z)], .010, 8, zone=Z.orange))

# ---------------------------------------------------------------- control and power conditioning, front deck
CB_Y0, CB_Y1 = .36, .74
CB_W, CB_H = .72, .23
s.add(box(CB_W, CB_Y1 - CB_Y0, CB_H, zone=SZ['chassis'], bevel=.008, center=(0, (CB_Y0 + CB_Y1) / 2, TOP + CB_H / 2)))
s.add(quad_patch(.26, .19, SZ['ctrl']), facing((.18, CB_Y1 + .001, TOP + CB_H / 2), (0, 1, 0)))
s.add(quad_patch(.28, .19, SZ['dark_box']), facing((-.20, CB_Y1 + .001, TOP + CB_H / 2), (0, 1, 0)))
# radiator fins on top of the box and a louvre panel on the side
s.add(quad_patch(CB_W - .06, .28, SZ['fins'], z=0), T(0, (CB_Y0 + CB_Y1) / 2, TOP + CB_H + .001))
d.add(quad_patch(.20, .14, Z.louver), facing((CB_W / 2 + .001, .55, TOP + CB_H / 2), (1, 0, 0)))
d.add(quad_patch(.20, .14, Z.vent), facing((-CB_W / 2 - .001, .55, TOP + CB_H / 2), (-1, 0, 0)))
# battery packs outboard of the control box
for sx_ in (-1, 1):
    s.add(box(.15, .36, .11, zone=SZ['dark_box'], bevel=.006, center=(sx_ * .455, .55, TOP + .055)))
    d.add(tube(smooth_path([(sx_ * .455, .37, TOP + .05), (sx_ * .42, .33, TOP + .03), (sx_ * .22, .32, TOP + .03), (sx_ * .12, .355, TOP + .04)]), .006, 5, zone=Z.orange))
# HV feeds, reactor base to the control box
for dx in (-.09, .09):
    d.add(tube(smooth_path([(dx, RY0 + .36, TOP + .03), (dx, .22, TOP + .035), (dx, CB_Y0, TOP + .05)]), .010, 8, zone=Z.orange))
# cable tray clamps over the feeds
for y_ in (.28, .34):
    d.add(box(.26, .018, .014, zone=Z.grey, center=(0, y_, TOP + .05)))

# comm whip with loading coil, S-band patch, camera mast with lamps
WH = (CB_W / 2 - .05, CB_Y1 - .05, TOP + CB_H)
d.add(cyl(.02, .025, 10, zone=Z.white, center_z=False), T(*WH))
d.add(cyl(.012, .07, 10, zone=Z.dark, center_z=False), T(WH[0], WH[1], WH[2] + .025))
d.add(tube([(WH[0], WH[1], WH[2] + .09), (WH[0] + .002, WH[1], WH[2] + .5), (WH[0] + .012, WH[1], WH[2] + 1.0)], 1.0, 5, zone=Z.white, r_fn=lambda t: .0055 - .0035 * t))
d.add(patch_antenna(.13), T(-.22, .50, TOP + CB_H))
MAST = (-.0, CB_Y1 - .07, TOP + CB_H)
d.add(cyl(.016, .30, 8, zone=Z.white, center_z=False), T(*MAST))
d.add(wide_camera(), T(MAST[0], MAST[1], MAST[2] + .25) @ Rz(180))
lamp_geo = Geo()
for sx_ in (-1, 1):
    fr = facing((sx_ * .12, CB_Y1 + .001, TOP + CB_H + .10), (0, 1, 0))
    d.add(box(.018, .018, .10, zone=Z.white, center=(sx_ * .12, CB_Y1 - .012, TOP + CB_H + .05)))
    d.add(exterior_lamp(.10, .055), fr)
    lamp_geo.add(lamp_lens(.10, .055), fr)
# stencil and target plates on the deck front
d.add(quad_patch(.09, .09, Z.target), T(.44, -.22, TOP + .001))
d.add(quad_patch(.09, .09, Z.target), T(-.44, -.22, TOP + .001))

# ---------------------------------------------------------------- objects
o_ch = P.mesh('chassis', chassis, M_rov, smooth_angle=30)
P.mesh('details', d, M_det, smooth_angle=38)
P.mesh('body', s, M_sf, smooth_angle=38)
P.mesh('lamp_lens', lamp_geo, M_lamp)
o_drum = P.mesh('cable_drum', drum_w, M_sf, frame=T(0, DR_Y, DR_Z), smooth_angle=40)

# headlamps
beam = Vector((0, 1, -.25)).normalized()
add_spot(P, 'headLight', Vector((0, CB_Y1 + .02, TOP + CB_H + .10)), beam, power=1200)

# ---------------------------------------------------------------- umbrella radiator: six heat-pipe petals
PET_L, PET_W, PET_T = .84, .30, .012
HR = RING_R + .03
pivot = P.empty('rad_pivot', T(0, RY0, RING_Z), P.model)
ANG = -102.0
for k in range(6):
    az = 60 * k
    fr = on_cyl(az, RING_Z + .004, HR)
    fr.translation += Vector((0, RY0, 0))
    g = Geo()
    g.add(box(PET_W, PET_L, PET_T, zone=SZ['chassis'], bevel=.003, center=(0, -PET_L / 2 - .02, 0)))
    # outer and inner skins, whole-zone mapped; hinge end is the zone's darker root band
    g.add(quad_patch(PET_W - .012, PET_L - .012, SZ['heatpipe']), T(0, -PET_L / 2 - .02, PET_T / 2 + .0006) @ Rz(180))
    g.add(quad_patch(PET_W - .012, PET_L - .012, SZ['heatpipe']), T(0, -PET_L / 2 - .02, -PET_T / 2 - .0006) @ Rx(180))
    # central header pipe and hinge barrel
    g.add(tube([(0, -.02, PET_T), (0, -PET_L + .03, PET_T)], .0075, 6, zone=SZ['stirling']))
    g.add(x_axis(cyl(.014, PET_W * .62, 10, zone=SZ['stirling'])))
    g.add(prism((0, 0, 0), (0, -.05, .005), .05, .02, up=(0, 0, 1), zone=SZ['chassis']))
    w_ = Geo(); w_.add(g, fr)
    o = P.mesh(f'radPanel{k}', w_, M_sf, parent=pivot, frame=fr, smooth_angle=35)
    rest = o.matrix_basis.to_quaternion()
    q = rest @ Quaternion((1, 0, 0), math.radians(ANG))
    # staged: each opposite pair starts a little later, and the panels ease past 90 degrees
    delay = (k % 3) * 8
    P.key('radiatorDeploy', o, 0, rotation_quaternion=rest)
    if delay:
        P.key('radiatorDeploy', o, delay, rotation_quaternion=rest)
    P.key('radiatorDeploy', o, 60 + delay, rotation_quaternion=rest @ Quaternion((1, 0, 0), math.radians(ANG * .55)))
    P.key('radiatorDeploy', o, 110, rotation_quaternion=q)

# ---------------------------------------------------------------- attach points and triggers
ANC = P.empty('anchor', T(0, 0, -CZ), P.model)
KAS_FR = P.empty('cableSource', facing((0, FL_Y - .03, FL_Z), (0, -1, 0)), P.model)
for k, (sx_, sy_) in enumerate(((-1, 1), (1, 1), (-1, -1), (1, -1))):     # 1 LF, 2 RF, 3 LR, 4 RR
    P.node(f'wheel{k + 1}', (sx_ * WX, sy_ * WY, NODE_Z), (0, 0, -1), 0)


def rect_pts(x0, x1, y0, y1, z0, z1):
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


def ring_pts(r, z, n=10, cy=0):
    return [Vector((r * math.cos(TAU * i / n), cy + r * math.sin(TAU * i / n), z)) for i in range(n)]


colliders = P.empty('colliders', parent=P.model)
P.hull_collider('col_chassis', rect_pts(-CX, CX, -CY, CY, -CZ, CZ), parent=colliders)
P.hull_collider('col_reactor', ring_pts(.34, TOP, 12, RY0) + ring_pts(.34, RING_Z + .03, 12, RY0), parent=colliders)
P.hull_collider('col_shield', rect_pts(-SH_W / 2, SH_W / 2, SH_Y0, SH_Y1 + .04, TOP, SH_Z1), parent=colliders)
P.hull_collider('col_drum', rect_pts(-DR_W / 2 - .2, DR_W / 2 + .2, -CY - .04, SH_Y0, TOP, DR_Z + .16), parent=colliders)
P.hull_collider('col_box', rect_pts(-CB_W / 2, CB_W / 2, CB_Y0, CB_Y1, TOP, TOP + CB_H), parent=colliders)
for sx_ in (-1, 1):
    for sy_ in (-1, 1):
        P.hull_collider(f'col_out{sx_ + 1}{sy_ + 1}', rect_pts(*sorted((sx_ * CX, sx_ * (WX + .12))), sy_ * WY - .13, sy_ * WY + .13, NODE_Z, NODE_Z + .05), parent=colliders)
P.box_trigger('ladder_L', climb_on_cyl(-90, TOP + .1, CX + .03), (.14, .14, .3), 'Ladder')
P.box_trigger('ladder_R', climb_on_cyl(90, TOP + .1, CX + .03), (.14, .14, .3), 'Ladder')

P.bake_clips(0)
P.node('top', (0, 0, 1.095), (0, 0, 1), 1)      # crown of the reactor
P.node('bottom', (0, 0, -CZ), (0, 0, -1), 1)
P.export(out)
P.save_blend(out)
print('GROUND_Z', GROUND_Z, 'FAIRLEAD unity', (0, FL_Z, FL_Y - .03), 'drum perimeter', TAU * .135)
