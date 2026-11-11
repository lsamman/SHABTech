"""Lander family layout: numbers shared by the lander/HIAD geometry and texture painters. No bpy."""
import math

# ---- shab_Lander deck (part origin at deck centre)
DECK_R = 2.5
DECK_TOP, DECK_BOT = 0.65, -0.65
MOUNT_R = 0.80          # PCM aft ring
MOUNT_Z = 0.72          # node_stack_top: PCM's bottom plane
ENGINE_R = 1.20
N_ENG = 8
LEG_AZ = [30 + 60 * i for i in range(6)]
LEG_Z = 0.30
RCS_AZ = [60, 120, 240, 300]

# ---- sheet shab_lander (2048 px): zones as (x, y, w, h), origin image top-left
TOP = (0, 0, 1320, 1320); TOP_RMAX = 2.56
UNDER = (1320, 0, 728, 728); UNDER_RMAX = 2.56
SIDE = (0, 1340, 1024, 508)     # one 60 degree sector of the deck wall; repeats six times
BOXES = (1024, 1340, 1024, 508) # trim for avionics boxes and tank skirts
PLATE = (1320, 740, 728, 580)   # mount ring wall and small plates


def polar_uv(zone, az, r, rmax, atlas=2048):
    x0, y0, w, h = zone
    a = math.radians(az)
    px = x0 + w / 2 + math.sin(a) * r / rmax * w / 2
    py = y0 + h / 2 + math.cos(a) * r / rmax * h / 2
    return px / atlas, 1 - py / atlas


def rect_uv(zone, s, t, atlas=2048):
    """s,t 0..1 across the zone, t=0 at the zone's bottom edge."""
    x0, y0, w, h = zone
    return (x0 + s * w) / atlas, 1 - (y0 + (1 - t) * h) / atlas


# ---- shab_HIAD (origin at top node = deck underside; +Z up, windward faces down)
HUB_R = 1.72            # engine opening: everything inside this stays clear
CONE_R0 = 1.82; CONE_Z0 = -0.85
SLOPE = math.radians(27)
TORUS = [   # name, s along the cone, minor radius, extra offset above the skin, group index
    ('T1', 0.25, 0.21, 0.0, 0), ('T2', 0.65, 0.21, 0.0, 0),
    ('T3', 1.05, 0.21, 0.0, 1), ('T4', 1.45, 0.21, 0.0, 1),
    ('T5', 1.85, 0.21, 0.0, 2), ('T6', 2.25, 0.21, 0.0, 2),
    ('T6.5', 2.45, 0.17, 0.27, 3), ('T7', 2.65, 0.21, 0.0, 3), ('T8', 3.00, 0.15, 0.0, 3),
]
GROUP_S = [0.0, 0.85, 1.65, 2.45, 3.22]    # skin group boundaries along the cone
# stowed transform per group: xy scale, z scale, z of the group's windward inner edge
STOW = [(1.00, .20, -.85), (.80, .20, -.72), (.68, .20, -.60), (.60, .20, -.48)]
HIAD_OUT_R = 4.68       # 16 m real x 0.585
STOW_OUT_R = 2.925      # 10 m real x 0.585
RIM_H = 0.85
RIM_DEPLOY_Z = 0.80; RIM_A = HIAD_OUT_R / STOW_OUT_R; RIM_B = 0.35
BOTTOM_NODE_Z = -0.85


def cone_rz(s, off=0.0):
    """(r, z) on the windward cone at distance s from its inner edge, offset along its normal."""
    return (CONE_R0 + s * math.cos(SLOPE) - off * math.sin(SLOPE), CONE_Z0 + s * math.sin(SLOPE) + off * math.cos(SLOPE))


# ---- sheet shab_hiad (2048 px)
SKIN = (0, 0, 1024, 1024)       # one 30 degree gore, inner edge at the bottom
BRAID = (1024, 0, 1024, 512)    # torus bladder braid: repeats around the major circle
RIMZ = (1024, 512, 1024, 256)   # dark stowage band with lacing, wraps the whole rim
NOSE = (1024, 768, 1024, 1024)  # ablator plug, polar
BACK = (0, 1024, 1024, 512)     # grey back cover / top ledge
HUBZ = (0, 1536, 1024, 512)     # hub wall and valve panel trim
