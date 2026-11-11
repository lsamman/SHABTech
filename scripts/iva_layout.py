"""Interior layout shared by build_iva.py and tex_iva.py. Coordinates are part-frame Blender
metres (+Z up the part, az 0 faces -Y), the same frame as build_pcm.py."""
import layout as L

R_WALL = 0.82
Z_FLOOR = -1.70       # lower floor walking surface
Z_DECK_TOP = -0.24    # upper floor walking surface
Z_DECK_BOT = -0.36    # lower floor ceiling
Z_CEIL = 1.10         # where the wall meets the crown liner
Z_HATCH_TOP = 1.72
HATCH_C = (0.12, 0.52)   # deck hatch centre (x, y); ladder stands on the wall behind it
HATCH_R = 0.24
BULK_Y = -0.26        # airlock bulkhead plane
BULK_T = 0.06
DOOR_W, DOOR_H = 0.76, 1.08
DOOR_Z = -1.06
LADDER_AZ = 167.0

ATLAS = 2048
ZONES = dict(
    wall=(0, 0, 700, 1024), rack=(700, 0, 512, 512), science=(1212, 0, 512, 512),
    lockers=(1724, 0, 324, 512), eclss=(700, 512, 512, 512), console=(1212, 512, 836, 512),
    bulkhead=(0, 1024, 700, 620), door=(700, 1024, 340, 520), water=(1040, 1024, 512, 256),
    deck=(1552, 1024, 496, 496), ceiling=(1040, 1280, 512, 512), crown=(0, 1644, 700, 200),
    sleep=(700, 1544, 340, 340), curtain=(1552, 1520, 248, 264), suit=(1800, 1520, 248, 264),
    dust=(0, 1844, 350, 204), shelter=(350, 1844, 350, 204), bike=(700, 1884, 340, 164),
)
# flat colour cells: row of 84 px squares from (1040, 1792)
CELLS = ['white', 'grey', 'dark', 'black', 'yellow', 'red', 'blue', 'steel', 'copper', 'rubber', 'gold', 'foam',
         'tan', 'green', 'orange', 'softwhite', 'hose', 'lamp', 'glove', 'pad', 'rail', 'bag', 'frame', 'grate']
for i, n in enumerate(CELLS):
    ZONES[n] = (1040 + (i % 12) * 84, 1792 + (i // 12) * 84, 84, 84)
