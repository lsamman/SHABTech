"""Shared layout numbers: geometry scripts and texture painters read the same values, so
painted fasteners, shadows and stencils line up with the modelled panels. No bpy here."""
SCALE = 0.585

# ---- PCM (Cygnus "Super" 4-segment, outer envelope 3.07 m -> 1.875 m, length 6.3 m -> 3.7 m)
Z_BOT, Z_TOP = -1.85, 1.85
Z_DOCK = 1.648          # docking port's seat, down in the well: an NDS here stands .06 above the collar, under the entry cap's nose
R_ENV = 0.9375          # MMOD panel envelope
R_FLOOR = 0.897         # gap floor under the MMOD bumpers
R_FIB = 0.955           # outside of the FIB blanket
SEG_Z = [-1.70, -1.00, -0.30, 0.40, 1.10]   # segment boundaries
FLOOR_Z = -0.30         # deck between the lower (EVA) and upper (living) floors
Z_SHOULDER = 1.18
R_COLLAR = 0.645
Z_COLLAR = 1.74
R_CBM = 0.625       # matches HabTech's C-200 CBM ring
R_HATCH = 0.54
Z_HATCH = 1.60          # floor of the docking well
NBAYS = 6
BAY_W = 360.0 / NBAYS
RIB_AZ = [(-180 + 30 + BAY_W * i) for i in range(NBAYS)]     # ribs at -150,-90,-30,30,90,150
BAY_AZ = [(-180 + 60 + BAY_W * i) for i in range(NBAYS)]     # bay centres at -120,-60,0,60,120,180
RIB_HALF = 2.4          # degrees
PANEL_GAP_Z = 0.012
FRAME_H = 0.028         # half height of a segment frame ring

# feature placement (azimuth in degrees; 0 faces the VAB camera, +90 is +X)
HATCH_AZ = 0.0
HATCH_Z = -1.00
HATCH_W, HATCH_H = 0.56, 0.86
WIN_AZ = 60.0
WIN_Z = (-0.72, 0.72)   # lower and upper floor
WIN_W, WIN_H = 0.20, 0.27
R_TANGENT = 0.975       # hatch and window flanges sit on this tangent plane

# ---- hull atlas (2048 px): strip of the unrolled cylinder at the bottom, dome top-left
ATLAS = 2048
PX_PER_M = ATLAS / (2 * 3.14159265 * R_ENV)
STRIP_Z0, STRIP_Z1 = Z_BOT, Z_SHOULDER
STRIP_PX = int((STRIP_Z1 - STRIP_Z0) * PX_PER_M)     # about 1054 px
DOME_SIZE = 940         # polar zone: square at the top-left corner of the sheet
DOME_RMAX = 1.2         # rho (see dome_rho) that maps to the zone's edge
# door and misc panels on the right-hand side of the sheet, above the strip
DOOR_ZONE = (980, 20, 520, 800)      # x, y, w, h px
RING_ZONE = (1520, 20, 500, 120)     # collar side wall
DECK_ZONE = (1520, 160, 500, 500)    # hatch disc

# The texture seam sits in the shadow gap beside the rib at -150, never across a panel.
SEAM_AZ = -147.4

def az_wrap(az):
    """Degrees past the seam, 0..360 inclusive, so a lathe's last column maps to u = 1."""
    d = az - SEAM_AZ
    while d < 0:
        d += 360.0
    while d > 360.0:
        d -= 360.0
    return d

def hull_px(az, z):
    """Pixel (x, y from the image top) of a point on the unrolled hull strip."""
    return az_wrap(az) / 360.0 * ATLAS, ATLAS - (z - STRIP_Z0) * PX_PER_M

def hull_uv(az, z):
    """UV (bottom-left origin) of a point on the hull strip."""
    return az_wrap(az) / 360.0, (z - STRIP_Z0) * PX_PER_M / ATLAS

def dome_rho(arc, total):
    """Polar texture radius from arc length along the crown profile, measured from the collar.
    Using arc length rather than radius keeps fasteners round where the shoulder turns vertical."""
    return R_COLLAR + (total - arc)

def dome_px(az, r):
    import math
    a = math.radians(az)
    c = DOME_SIZE / 2
    return c + math.sin(a) * r / DOME_RMAX * c, c + math.cos(a) * r / DOME_RMAX * c

def dome_uv(az, r):
    x, y = dome_px(az, r)
    return x / ATLAS, 1 - y / ATLAS

# ---- details atlas (shared by every part): zones as (x, y, w, h)
DET = dict(
    white=(0, 0, 256, 256), grey=(256, 0, 256, 256), dark=(512, 0, 256, 256), bare=(768, 0, 256, 256),
    black=(1024, 0, 128, 128), gold=(1152, 0, 128, 128), yellow=(1280, 0, 128, 128), copper=(1408, 0, 128, 128),
    rubber=(1536, 0, 128, 128), orange=(1664, 0, 128, 128), kevlar=(1792, 0, 256, 128),
    glass=(1024, 128, 128, 128), red=(1152, 128, 128, 128), blue=(1280, 128, 128, 128), hazard=(1408, 128, 256, 64),
    hazard2=(1408, 192, 256, 64), steel=(1664, 128, 128, 128), lens=(1792, 128, 128, 128), lamp=(1920, 128, 128, 128),
    mli_gold=(0, 256, 512, 512), mli_silver=(512, 256, 512, 512), beta=(1024, 256, 512, 512), mli_black=(1536, 256, 512, 512),
    vent=(0, 768, 256, 256), louver=(256, 768, 256, 256), grating=(512, 768, 256, 256), connector=(768, 768, 256, 256),
    solar=(1024, 768, 512, 512), access=(1536, 768, 256, 256), radpanel=(1792, 768, 256, 256),
    tank_white=(0, 1024, 512, 256), tank_grey=(512, 1024, 512, 256),
    copv=(0, 1280, 256, 256), wrap=(256, 1280, 256, 256), nozzle=(512, 1280, 256, 256), nozzle_in=(768, 1280, 256, 256),
    target=(1536, 1024, 128, 128), logo=(1664, 1024, 384, 128), stencil=(1536, 1152, 512, 128),
    tile=(1024, 1280, 512, 512), ablator=(1536, 1280, 512, 512),
    plumbing=(0, 1536, 512, 256), deck=(512, 1536, 512, 256), lander_panel=(0, 1792, 512, 256), hex=(512, 1792, 512, 256),
    foil_dark=(1024, 1792, 512, 256), nomex=(1536, 1792, 512, 256),
)
