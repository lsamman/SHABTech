"""Layout shared by the service module / radiator / antenna builders and tex_sm.py. No bpy."""
import math

# ---- 12-sided service module (paper fig. 1). Circumscribed radius matches the PCM envelope.
R = 0.9375
Z_TOP, Z_BOT = 0.425, -0.425
Z_DECK = -0.17          # aft bulkhead, recessed so the engine sits inside the skirt
R_WALL = R - 0.05       # inner wall of the aft skirt
NF = 12
FACET = 30.0
A0 = -15.0              # first vertex azimuth; facets are centred on 0, 30, 60...
BAND = 0.07             # height of the top and bottom ring frames
MID = 0.018             # half height of the mid belt

# ---- sheet: 2048 px
ATLAS = 2048
PPM = ATLAS / (NF * 2 * R * math.sin(math.radians(FACET / 2)))    # about 352 px/m
Y_TOP = 1720            # image row of z = Z_TOP on the blanket strip


def az_wrap(az):
    d = az - A0
    while d < 0:
        d += 360.0
    while d > 360.0:
        d -= 360.0
    return d


def strip_px(az, z):
    return az_wrap(az) / 360.0 * ATLAS, Y_TOP + (Z_TOP - z) * PPM


def strip_uv(az, z):
    x, y = strip_px(az, z)
    return x / ATLAS, 1 - y / ATLAS


def polar_uv(cx, cy, rpx, rmax, az, r):
    a = math.radians(az)
    return (cx + math.sin(a) * r / rmax * rpx) / ATLAS, 1 - (cy + math.cos(a) * r / rmax * rpx) / ATLAS


# zones on the sheet: polar centres and rectangles in px
AFT = (512, 512, 500, 0.92)                 # aft bulkhead: cx, cy, r_px, r_max
TOPRING = (1280, 768, 250, 0.96)            # top deck ring
RAD = (1024, 0, 512, 512)                   # radiator panel
DISH_IN = (1792, 256, 250, 0.56)            # dish inner surface
DISH_OUT = (1792, 768, 250, 0.56)           # dish back

def aft_uv(az, r):
    return polar_uv(*AFT, az, r)

def top_uv(az, r):
    return polar_uv(*TOPRING, az, r)

def rad_uv(s, t):
    """s across the panel, t along the span, 0..1."""
    x, y, w, h = RAD
    return (x + 2 + s * (w - 4)) / ATLAS, 1 - (y + 2 + (1 - t) * (h - 4)) / ATLAS

def dish_in_uv(az, r):
    return polar_uv(*DISH_IN, az, r)

def dish_out_uv(az, r):
    return polar_uv(*DISH_OUT, az, r)

# ---- UltraFlex fan sheet: 1024 px, wedge apex at the bottom
FAN_ATLAS = 1024
FAN_R = 2.135           # gore radius in metres at standard size (7.3 m real x 0.585)
FAN_RH = 0.095          # inner gore radius at the hub
FAN_N = 20
FAN_PPM = 1000.0 / FAN_R
FRONT_CX, BACK_CX = 170, 510
APEX_Y = 1018
HUB_POLAR = (830, 190, 160, 0.13)          # hub face: cx, cy, r_px, r_max
STRIP_FAN = (690, 380, 320, 120)            # spare trim

def fan_front_uv(lat, rad):
    return (FRONT_CX - lat * FAN_PPM) / FAN_ATLAS, 1 - (APEX_Y - rad * FAN_PPM) / FAN_ATLAS

def fan_back_uv(lat, rad):
    return (BACK_CX + lat * FAN_PPM) / FAN_ATLAS, 1 - (APEX_Y - rad * FAN_PPM) / FAN_ATLAS

def fan_hub_uv(az, r):
    cx, cy, rp, rm = HUB_POLAR
    a = math.radians(az)
    return (cx + math.sin(a) * r / rm * rp) / FAN_ATLAS, 1 - (cy + math.cos(a) * r / rm * rp) / FAN_ATLAS
