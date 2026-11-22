"""Zones of the shab_mech sheet (scripts/tex_mech.py): radiator wing panel, landing-leg trim and the HIAD
stowage band. Shared by the painter and the build scripts. No bpy. (x, y, w, h) px, origin image top-left."""
import math

ATLAS = 2048
WING = (0, 0, 1024, 1536)        # one radiator panel face, s across the 0.40 m width, t along the 0.60 m span
WING_W, WING_SPAN = .40, .60
WING_TUBES = 22                  # flow tubes across the panel
WING_EDGE = .026                 # closeout band at each long edge (rail + doubler), metres
WING_HDR = .034                  # header band at each end, metres
BAND = (1024, 0, 1024, 512)      # HIAD stowage band, one 30 degree tile; t = 0 at the band's bottom
BAND_TILES = 12
BAND_STRAPS = 2                  # Kevlar straps per tile, at s = .25 and .75
LEDGE = (1024, 512, 1024, 256)   # HIAD back-cover cloth for the band's ledges; right 64 px dark
PADTOP = (1024, 768, 512, 512)   # footpad top, polar, r = PAD_RMAX at the zone edge
PAD_RMAX = .205
STRUT = (1536, 768, 256, 1024)   # landing-leg outer sleeve wrap: s around, t along the sleeve
CART = (1792, 768, 256, 512)     # crush cartridge wrap: s around, t along
SOLE = (1792, 1280, 256, 256)    # footpad underside, plain


def rect_uv(zone, s, t, atlas=ATLAS):
    """s, t 0..1 across the zone, t = 0 at the zone's bottom edge (inset half a texel)."""
    x0, y0, w, h = zone
    s = min(max(s, 0.0), 1.0); t = min(max(t, 0.0), 1.0)
    return (x0 + .5 + s * (w - 1)) / atlas, 1 - (y0 + .5 + (1 - t) * (h - 1)) / atlas


def polar_uv(zone, az, r, rmax, atlas=ATLAS):
    x0, y0, w, h = zone
    a = math.radians(az)
    px = x0 + w / 2 + math.sin(a) * r / rmax * (w / 2 - 2)
    py = y0 + h / 2 + math.cos(a) * r / rmax * (h / 2 - 2)
    return px / atlas, 1 - py / atlas
