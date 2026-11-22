"""Methalox engine family (lander descent engine, SM main engine): sheet shab_engine. No bpy.
Zones as (x, y, w, h) in a 1024 px sheet, origin at the image's top left, as painted."""
ATLAS = 1024
ENG = dict(
    bell=(0, 0, 1024, 384),         # regen nozzle outside: dark, vertical coolant channels; t=0 at the exit
    bell_in=(0, 384, 1024, 192),    # nozzle inside: t=0 at the exit, t=1 at the throat
    chamber=(0, 576, 512, 256),     # copper chamber and throat; heat tint peaks at t = T_THROAT
    steel=(512, 576, 256, 128),     # pump housings, injector dome
    tint=(768, 576, 256, 128),      # preburner and turbine: steel with a straw-to-blue heat tint up t
    dark=(512, 704, 256, 128),      # gimbal block, lugs, valve bodies
    band=(768, 704, 256, 128),      # hat-band stiffeners and the exit ring: dark with a raised land
    flange=(0, 832, 1024, 64),      # bolted flange: 64 bolt heads once around
    bellows=(0, 896, 512, 128),     # flex joint convolutions across t
    duct=(512, 896, 512, 128),      # bare steel duct, weld bands along t
)
RIBS = 128                          # coolant channels once around the nozzle
T_THROAT = .30                      # where the copper zone's t meets the throat
