# SHABTech

A KSP 1.12 part pack for the Mars Surface Habitat proposed in Yusuf Rafi's paper "Reconfiguring Cygnus Expendable Cargo Spacecraft into Mars Transit & Surface Habitat" (AIAA Regional Student Conferences 2023, DOI 10.2514/6.2023-71065). Parts are scaled to match HabTech2 (real metres x 0.585).

SHABTech is an unofficial fan project. It isn't affiliated with or endorsed by the paper's author, NASA, Northrop Grumman or SpaceX.

## Needs
- ModuleManager, B9PartSwitch, Community Resource Pack
- Optional: Waterfall (engine plumes), KAS (reactor power cable), FreeIva, VAB Organizer

Tundra Exploration's Falcon parts make the Earth departure stage in the paper's stack.

## Parts
Stack for Mars, top to bottom: `TS-4 Entry Cap`, `SH-4 Habitat`, `ML-8 Lander Deck`, `HD-16 Decelerator`, `NP-3 Nose Plug`, `TA-25 Adapter`, Tundra's Falcon upper stage. For the trip to orbit, put the `SM-2 Service Module` under the habitat instead.

| Part | What it is |
|---|---|
| SH-4 "Longship" | Two-floor crew habitat with internal airlock, IVA and FreeIva support. FIB blanket or bare MMOD shell |
| TS-4 Entry Cap | Jettisonable tiled shell over the top half of the habitat, with a low crown and a hinged nose cone over the docking port seated in the habitat's collar, and two chutes that drag it clear when it jettisons |
| SM-2 "Tugboat" | Gold-foil Cygnus service module with engine and RCS |
| UF-7 / UF-10 | Fan solar arrays: 2.2 m (the real 3.7 m at HabTech scale) and a larger 3 m transit size |
| TR-3 | Folding radiator wing |
| HG-110 | Deployable high-gain Mars antenna |
| ML-8 "Doorstep" | Lander deck with eight methalox engines, methalox RCS and a built-in probe core, so it can control the vessel without crew |
| LL-6 | Rim landing leg. Six nodes on the deck, or six-way symmetry on its wall |
| HD-16 | Inflatable decelerator, 16 m real and 9.36 m in game. Reversible |
| NP-3 | Ablative plug for the decelerator's hub. Jettison before ignition |
| TA-25 | Interstage to a 2.5 m stage, with retro motors |
| KP-100 "Hearthstone" | Reactor cart, 80 EC/s. Takes four SR-28 wheels. KAS power cable to the habitat |
| OX-1 "Bellows" | Oxygen plant: Mars CO2 to oxidizer, oxygen and water |

## Flying it
Mars entry order: inflate the HD-16, enter shield first, jettison the entry cap and nose plug below about Mach 3, light the engines, retract the HD-16 and lower the legs, land, extend the ladder. Lowering the legs while the HD-16 is inflated pushes them through the fabric, which is only cosmetic.

## Licences
- Original art, models and configs: CC BY-NC-SA 4.0.
- Build scripts: MIT.
- `io_object_mu` exporter patch: GPL, as the upstream add-on.
- Nothing from HabTech2, Benjee10's mods or RN_Cygnus is copied. Those mods were used as visual references, and anything used from them (such as IVA props) is referenced at runtime and needs them installed.

## Rebuilding
`./build_all.sh` rebuilds everything in headless Blender 3.6 with io_object_mu and writes `GameData/SHABTech`. `./deploy.sh` copies it into the Sol install.
