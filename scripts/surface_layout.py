"""Layout shared by the surface parts (reactor rover, wheel, ISRU) and their texture painter. No bpy."""
# shab_surface sheet: trim zones, (x, y, w, h)
SURF = dict(
    vessel=(0, 0, 512, 512), shield=(512, 0, 512, 512), heatpipe=(1024, 0, 512, 512),
    cable=(1536, 0, 256, 256), tread=(1792, 0, 256, 256), ctrl=(1536, 256, 256, 256), hub=(1792, 256, 256, 256),
    chassis=(0, 512, 1024, 256), cdeck=(1024, 512, 512, 256), trefoil=(1536, 512, 256, 256), dark_box=(1792, 512, 256, 256),
    soec=(0, 768, 512, 256), filter=(512, 768, 256, 256), isru=(768, 768, 512, 256), lox=(1280, 768, 384, 256), h2o=(1664, 768, 384, 256),
    fins=(0, 1024, 512, 256), stirling=(512, 1024, 512, 256), flange=(1024, 1024, 256, 256), valve=(1280, 1024, 256, 256),
)
# shab_rover sheet (1024 px): chassis, unique-mapped, about 400 px/m, AO-baked
ROVER_ATLAS = 1024
ROV = dict(deck=(0, 0, 640, 440), sideL=(0, 440, 640, 96), sideR=(0, 536, 640, 96), front=(0, 632, 440, 96), rear=(0, 728, 440, 96), belly=(640, 0, 384, 264))
# chassis size in KSP metres
CH_X, CH_Y, CH_Z = .55, .80, .12
# shab_isru sheet (1024 px): pallet and rack skins, unique-mapped, AO-baked
ISRU_ATLAS = 1024
ISR = dict(deck=(0, 0, 640, 470), front=(0, 470, 640, 300), rear=(640, 0, 384, 300), left=(640, 300, 384, 300), right=(640, 600, 384, 300), lip=(0, 770, 640, 60))
ISRU_X, ISRU_Y = .475, .35
