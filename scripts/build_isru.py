"""shab_ISRU: oxygen plant (paper III-B). Rack on a tie-down pallet: dust-filtered telescoping
intake mast, CO2 compressor, solid-oxide electrolysis hot box with fin radiator, LOX and H2O
tanks, hydrogen feedstock bottle, CO vent stack and copper plumbing."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from sl import *
from greebles import *
from gr_surface import *
from surface_layout import *

out = sys.argv[sys.argv.index('--') + 1]
enable_addon(); clean_scene()
np.random.seed(31)

P = Part('shab_ISRU')
M_isr = P.material('shab_isru')
M_sf = P.material('shab_surface', spec=(.9, .9, .9), shininess=.3)
M_det = P.material('shab_details', spec=(.9, .9, .9), shininess=.3)

XX, YY = ISRU_X, ISRU_Y
Z0, Z1 = -.45, .40       # pallet underside, top of the frame
DECK = -.39
d = Geo(); s = Geo(); skin = Geo()

# ---------------------------------------------------------------- pallet and skins
skin.add(boxmap(-XX, XX, -YY, YY, Z0, DECK, .008, dict(top=IZ['deck'], bottom=IZ['lip'], xp=IZ['lip'], xn=IZ['lip'], yp=IZ['lip'], yn=IZ['lip'])))
# rear and left walls: thin sheet on the frame, whole-zone mapped, inner faces dark
wall_h = Z1 - DECK
for org, n, zone_, w_ in (((0, YY - .012, (DECK + Z1) / 2), (0, 1, 0), IZ['rear'], 2 * XX - .04), ((-XX + .012, 0, (DECK + Z1) / 2), (-1, 0, 0), IZ['left'], 2 * YY - .04)):
    skin.add(quad_patch(w_, wall_h - .03, zone_), facing(org, n))
    d.add(quad_patch(w_, wall_h - .03, Z.dark), facing(org, tuple(-v for v in n)) @ T(0, 0, .002))
# tie-down lugs on the pallet corners
for sx_ in (-1, 1):
    for sy_ in (-1, 1):
        d.add(cyl(.028, .014, 10, zone=Z.yellow, bevel=.003, center_z=False), T(sx_ * (XX - .05), sy_ * (YY - .05), DECK))
        d.add(cyl(.011, .012, 6, zone=Z.steel, center_z=False), T(sx_ * (XX - .05), sy_ * (YY - .05), DECK + .014))

# ---------------------------------------------------------------- frame
POST = .035
for sx_ in (-1, 1):
    for sy_ in (-1, 1):
        d.add(box(POST, POST, wall_h, zone=Z.white, bevel=.004, center=(sx_ * (XX - .018), sy_ * (YY - .018), (DECK + Z1) / 2)))
for sy_ in (-1, 1):
    d.add(box(2 * XX, POST, POST, zone=Z.white, bevel=.004, center=(0, sy_ * (YY - .018), Z1 - POST / 2)))
for sx_ in (-1, 1):
    d.add(box(POST, 2 * YY, POST, zone=Z.white, bevel=.004, center=(sx_ * (XX - .018), 0, Z1 - POST / 2)))
# nameplate on the front top beam
s.add(quad_patch(.46, .11, SZ['isru']), facing((-.20, -YY - .0012, Z1 - .058), (0, -1, 0)))
d.add(box(.50, .012, .13, zone=Z.white, bevel=.002, center=(-.20, -YY + .006, Z1 - .058)))
# lifting eyes on the top corners
for sx_ in (-1, 1):
    for sy_ in (-1, 1):
        d.add(cyl(.014, .02, 8, zone=Z.yellow, center_z=False), T(sx_ * (XX - .018), sy_ * (YY - .018), Z1))

# ---------------------------------------------------------------- SOXE hot box, left half
HB = (-.415, -.03, -.29, .285, DECK + .01, .03)     # x0 x1 y0 y1 z0 z1
hx0, hx1, hy0, hy1, hz0, hz1 = HB
d.add(box(hx1 - hx0, hy1 - hy0, hz1 - hz0, zone=Z.nomex, bevel=.012, center=((hx0 + hx1) / 2, (hy0 + hy1) / 2, (hz0 + hz1) / 2)))
# sight window onto the cell stack, on the front face
s.add(quad_patch(.25, .24, SZ['soec']), facing(((hx0 + hx1) / 2, hy0 - .002, (hz0 + hz1) / 2 + .01), (0, -1, 0)))
d.add(rounded_rect_ring(.28, .27, .02, .026, .022, seg=3, zone=Z.grey, base=-.004), facing(((hx0 + hx1) / 2, hy0 - .002, (hz0 + hz1) / 2 + .01), (0, -1, 0)))
# stack tie rods and pressure plate above the hot box
for sx_ in (-1, 1):
    for y_ in (hy0 + .06, hy1 - .06):
        d.add(cyl(.009, .03, 6, zone=Z.steel, center_z=False), T((hx0 + hx1) / 2 + sx_ * .13, y_, hz1))
d.add(box(.34, hy1 - hy0 - .06, .018, zone=Z.grey, bevel=.004, center=((hx0 + hx1) / 2, (hy0 + hy1) / 2, hz1 + .02)))
# fin radiator: 14 vertical plates on the hot box, with a header along each side
FZ0, FZ1 = hz1 + .03, Z1 - .05
FN = 14
for i in range(FN):
    x_ = hx0 + .03 + (hx1 - hx0 - .06) * i / (FN - 1)
    s.add(box(.007, hy1 - hy0 - .07, FZ1 - FZ0, zone=SZ['chassis'], center=(x_, (hy0 + hy1) / 2, (FZ0 + FZ1) / 2)))
    d.add(box(.009, .024, FZ1 - FZ0, zone=Z.black, center=(x_, hy0 + .03, (FZ0 + FZ1) / 2)))
for sy_ in (hy0 + .04, hy1 - .04):
    d.add(tube([(hx0 + .012, sy_, FZ0 + .02), (hx1 - .012, sy_, FZ0 + .02)], .011, 8, zone=Z.copper))

# ---------------------------------------------------------------- LOX and H2O tanks, right front
def tank(zone_, r, h, x_, y_, z0):
    cap = r * .55
    p = [(0, z0), (r * .55, z0 + cap * .18), (r * .86, z0 + cap * .58), (r, z0 + cap), (r, z0 + h - cap), (r * .86, z0 + h - cap * .58), (r * .55, z0 + h - cap * .18), (0, z0 + h)]
    s.add(lathe(p, 28, zone=zone_), T(x_, y_, 0))
    d.add(cyl(r * .22, .025, 10, zone=Z.grey, bevel=.003, center_z=False), T(x_, y_, z0 + h - .003))
    # saddle straps and feet
    for z_ in (z0 + h * .28, z0 + h * .72):
        d.add(cyl(r + .004, .016, 28, zone=Z.grey, center_z=True), T(x_, y_, z_))
    for k in range(4):
        a = TAU * (k + .5) / 4
        d.add(prism((x_ + (r - .02) * math.cos(a), y_ + (r - .02) * math.sin(a), z0 + cap * .6), (x_ + (r + .02) * math.cos(a), y_ + (r + .02) * math.sin(a), DECK), .014, .02, zone=Z.grey))


LOX = (.31, -.17, DECK + .035, .125, .50)
H2O = (.07, -.19, DECK + .035, .092, .40)
tank(SZ['lox'], LOX[3], LOX[4], LOX[0], LOX[1], LOX[2])
tank(SZ['h2o'], H2O[3], H2O[4], H2O[0], H2O[1], H2O[2])
# frost-line MLI collar around the LOX tank neck
d.add(cyl(.05, .05, 14, zone=Z.mli_silver, center_z=False), T(LOX[0], LOX[1], LOX[2] + LOX[4]))

# ---------------------------------------------------------------- compressor, rear right
CP_Y, CP_Z = .155, -.24
CP_X0, CP_X1 = .03, .44
s.add(x_axis(lathe([(0, CP_X0), (.07, CP_X0), (.085, CP_X0 + .015), (.085, CP_X1 - .13), (.07, CP_X1 - .115), (0, CP_X1 - .115)], 22, zone=SZ['stirling'])), T(0, CP_Y, CP_Z))
d.add(x_axis(fin_stack(.07, .098, 9, .018, .005, Z.grey, seg=20)), T(.22, CP_Y, CP_Z))
d.add(x_axis(cyl(.068, .11, 20, zone=Z.white, bevel=.006)), T(CP_X1 - .06, CP_Y, CP_Z))     # motor
d.add(x_axis(cyl(.082, .012, 20, zone=Z.dark)), T(CP_X1 - .002, CP_Y, CP_Z))                # fan shroud
for sy_ in (-1, 1):
    d.add(box(.3, .03, CP_Z - DECK - .07, zone=Z.grey, bevel=.004, center=(.22, CP_Y + sy_ * .055, (CP_Z - .07 + DECK) / 2)))
# hydrogen feedstock bottle on a shelf above the compressor (COPV)
H2B = (.24, .165, .06)
d.add(prism((.05, .09, -.08), (.42, .09, -.08), .03, .022, zone=Z.white))
d.add(prism((.05, .25, -.08), (.42, .25, -.08), .03, .022, zone=Z.white))
d.add(x_axis(lathe([(0, -.18), (.045, -.17), (.075, -.14), (.08, -.10), (.08, .10), (.075, .14), (.045, .17), (0, .18)], 22, zone=Z.copv)), T(*H2B))
for dx in (-.09, .09):
    d.add(x_axis(cyl(.083, .018, 22, zone=Z.grey)), T(H2B[0] + dx, H2B[1], H2B[2]))
    for dy in (-.06, .06):
        d.add(box(.02, .018, .12, zone=Z.grey, center=(H2B[0] + dx, H2B[1] + dy, H2B[2] - .08)))
d.add(x_axis(cyl(.018, .04, 8, zone=Z.bare)), T(H2B[0] + .20, H2B[1], H2B[2]))
d.add(valve(.035), T(H2B[0] + .205, H2B[1], H2B[2] - .03) @ Rx(180))

# ---------------------------------------------------------------- plumbing, CO vent stack, panels
# compressor discharge to hot box
d.add(tube(smooth_path([(CP_X0 + .01, CP_Y, CP_Z), (-.012, CP_Y, CP_Z + .03), (-.03, CP_Y - .02, CP_Z + .06)]), .013, 8, zone=Z.copper))
# hot box O2 line to the LOX tank via a valve
o2 = [(hx1 + .002, -.10, -.15), (.02, -.08, -.08), (.15, -.03, .02), (LOX[0] - .02, LOX[1] + .03, LOX[2] + LOX[4] + .05), (LOX[0], LOX[1], LOX[2] + LOX[4] + .05)]
d.add(tube(smooth_path(o2), .009, 7, zone=Z.copper))
d.add(valve(.04), T(.15, -.03, .02) @ Rx(90))
# H2 from the bottle to the Sabatier-style water reactor, then to the H2O tank
wr = (.07, .02, -.10)
s.add(cyl(.045, .13, 14, zone=SZ['stirling'], bevel=.006, center_z=True), T(*wr))
d.add(tube(smooth_path([(H2B[0] + .205, H2B[1], H2B[2] - .06), (.40, .07, -.04), (.20, .03, -.02), (wr[0] + .02, wr[1], wr[2] + .065)]), .0065, 6, zone=Z.gold))
d.add(tube(smooth_path([(wr[0], wr[1] - .03, wr[2] - .06), (H2O[0], H2O[1] + .04, -.12), (H2O[0], H2O[1], H2O[2] + H2O[4])]), .0065, 6, zone=Z.copper))
d.add(tube(smooth_path([(hx1 + .002, .03, -.16), (.02, .02, -.13), (wr[0] - .045, wr[1], wr[2] + .01)]), .0065, 6, zone=Z.copper))
# CO vent stack from the hot box up the back left corner, flared
VX, VY = -.39, .285
d.add(tube(smooth_path([(hx0 + .08, hy1 - .03, hz1), (VX + .03, VY - .02, hz1 + .06), (VX, VY, hz1 + .16), (VX, VY, Z1 + .24)], n=5), .013, 8, zone=Z.bare))
d.add(lathe([(.014, 0), (.03, .03), (.032, .05)], 12, zone=Z.dark), T(VX, VY, Z1 + .24))
d.add(cyl(.032, .004, 12, zone=Z.black), T(VX, VY, Z1 + .29))
for z_ in (.02, .24):
    d.add(box(.09, .03, .012, zone=Z.grey, center=(VX + .02, VY + .03, z_)))
# power input junction and connector plates on the right side, open bay
d.add(junction_box(.14, .12, .035), facing((XX - .03, .24, -.32), (1, 0, 0)))
d.add(qd_panel(.17, .11), facing((XX - .02, -.04, DECK + .08), (1, 0, 0)))
d.add(tube(smooth_path([(XX - .02, .24, -.29), (.41, .20, -.19), (CP_X1 - .05, CP_Y, CP_Z + .07)]), .007, 6, zone=Z.orange))
d.add(tube(smooth_path([(XX - .03, .17, -.34), (.28, .05, -.37), (-.02, -.03, DECK + .04)]), .009, 6, zone=Z.orange))
# handrail along the top of the front beam, right side, for EVA servicing
d.add(handrail(.30, standoff=.04, bar=.012), facing((.26, -YY, Z1 - .02), (0, -1, 0), up=(1, 0, 0)))

# ---------------------------------------------------------------- mast (rises from the back right corner)
MX, MY = .385, .275
MB_TOP = Z1 + .06
d.add(cyl(.038, MB_TOP - DECK, 14, zone=Z.white, bevel=.003, center_z=False), T(MX, MY, DECK))
d.add(cyl(.05, .012, 14, zone=Z.grey, center_z=False), T(MX, MY, Z1 - .02))
d.add(box(.08, .02, .03, zone=Z.white, center=(MX, MY + .02, Z1 - .03)))
STAGE = .34
st1 = Geo(); st1.add(cyl(.029, STAGE + .05, 12, zone=Z.bare, center_z=False), T(MX, MY, MB_TOP - STAGE - .05))
st1.add(cyl(.034, .012, 12, zone=Z.grey, center_z=False), T(MX, MY, MB_TOP - .012 + .005))
st2 = Geo(); st2.add(cyl(.021, STAGE + .05, 12, zone=Z.bare, center_z=False), T(MX, MY, MB_TOP - STAGE - .05))
# filter head: pleated drum, top hood, intake screen, sits on the top stage
hd = Geo(); hds = Geo()
HZ = MB_TOP + .012
hds.add(lathe([(.086, HZ + .03), (.086, HZ + .15)], 24, zone=SZ['filter']), T(MX, MY, 0))
hd.add(cyl(.036, .02, 12, zone=Z.grey, center_z=False), T(MX, MY, HZ))
hd.add(lathe([(.03, HZ + .02), (.094, HZ + .03), (.094, HZ + .036), (.03, HZ + .04)], 24, zone=Z.grey), T(MX, MY, 0))
hd.add(lathe([(.094, HZ + .148), (.098, HZ + .158), (.05, HZ + .20), (.014, HZ + .214), (0, HZ + .216)], 24, zone=Z.white), T(MX, MY, 0))
for k in range(6):
    a = TAU * k / 6
    hd.add(box(.008, .008, .126, zone=Z.grey, center=(MX + .09 * math.cos(a), MY + .09 * math.sin(a), HZ + .09)))
d.add(tube(smooth_path([(MX - .02, MY - .02, Z1 + .02), (.34, .24, .05), (.40, .17, -.06), (CP_X1 - .02, CP_Y + .03, CP_Z + .09)]), .012, 8, zone=Z.rubber))

# ---------------------------------------------------------------- objects
P.mesh('rack_skin', skin, M_isr, smooth_angle=30)
P.mesh('details', d, M_det, smooth_angle=38)
P.mesh('body', s, M_sf, smooth_angle=38)
# compressor cooling fan, spins while the plant runs
fan_fr = T(CP_X1 + .002, CP_Y, CP_Z)
fan = Geo()
fan.add(x_axis(cyl(.016, .014, 10, zone=Z.dark)), fan_fr)
for k in range(7):
    a = TAU * k / 7
    y1, z1_ = .07 * math.cos(a), .07 * math.sin(a)
    b_ = a + .55
    fan.add(tube([(CP_X1 + .002, CP_Y, CP_Z), (CP_X1 + .004, CP_Y + y1 * .55, CP_Z + z1_ * .55), (CP_X1 + .006, CP_Y + .074 * math.cos(b_), CP_Z + .074 * math.sin(b_))], .007, 3, zone=Z.grey))
o_fan = P.mesh('fan', fan, M_det, frame=fan_fr)
rest = o_fan.matrix_basis.to_quaternion()
for i in range(7):
    P.key('plantRunning', o_fan, i * 5, rotation_quaternion=rest @ Quaternion((1, 0, 0), TAU * i / 6))

o1 = P.mesh('mastStage1', st1, M_det, frame=T(MX, MY, 0))
o2_ = P.mesh('mastStage2', st2, M_det, frame=T(MX, MY, 0), parent=o1)
o3 = P.mesh('filterHead', hd, M_det, frame=T(MX, MY, 0), parent=o2_)
P.mesh('filterPleats', hds, M_sf, frame=T(MX, MY, 0), parent=o3)
for o, z_ in ((o1, STAGE), (o2_, STAGE)):
    loc = o.location.copy()
    P.key('mastDeploy', o, 0, location=loc)
    P.key('mastDeploy', o, 60, location=loc + Vector((0, 0, z_)))


def rect_pts(x0, x1, y0, y1, z0, z1):
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


colliders = P.empty('colliders', parent=P.model)
P.hull_collider('col_rack', rect_pts(-XX, XX, -YY, YY, Z0, Z1), parent=colliders)
P.hull_collider('col_mast', [(MX + .09 * math.cos(TAU * i / 8), MY + .09 * math.sin(TAU * i / 8), z_) for i in range(8) for z_ in (Z1, HZ + .216)], parent=o3)
P.box_trigger('ladder_front', climb_frame((.2, -YY - .05, 0), (0, -1, 0)), (.5, .14, .7), 'Ladder')

P.node('bottom', (0, 0, Z0), (0, 0, -1), 1)
P.node('top', (0, 0, Z1), (0, 0, 1), 1)
P.bake_clips(0)
P.export(out)
P.save_blend(out)
