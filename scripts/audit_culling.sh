#!/bin/bash
# Find surfaces KSP would cull: render each part with and without backface culling and diff the images.
# usage: scripts/audit_culling.sh <empty output dir>
cd "$(dirname "$0")/.."
B="$HOME/Applications/blender-3.6/blender"; M=build/mu; S="$1"; mkdir -p "$S"
for p in Lander:0 Lander2:90 HIAD:180 HIAD2:0 Nose:0 Adapter:0 PCM:0 TPS:0 SM:0 UltraFlex:240 RadiatorWing:150 HGA:180 Leg:90 ReactorRover:60 RoverWheel:0 ISRU:60; do
    n=${p%%:*}; f=${p##*:}; b=${n%2}
    for v in 35,20 215,-35; do
        for mode in cull nocull; do
            flag=""; [ "$mode" = nocull ] && flag="--nocull"
            flock build/.render.lock "$B" -b --factory-startup -P scripts/render_stack.py -- "$S/${n}_${v%%,*}_$mode.png" --res 420x360 --samples 8 $flag --view "$v,0" "$M/shab_$b.blend:$f" >/dev/null 2>&1
        done
    done
done
python3 -I - "$S" <<'E'
import glob, sys, os
import numpy as np
from PIL import Image
for f in sorted(glob.glob(sys.argv[1] + '/*_cull.png')):
    a = np.asarray(Image.open(f).convert('RGB')).astype(int)
    b = np.asarray(Image.open(f.replace('_cull.png', '_nocull.png')).convert('RGB')).astype(int)
    d = np.abs(a - b).max(axis=2) > 45
    if d.sum() > 15:
        print(os.path.basename(f)[:-9], int(d.sum()))
        Image.fromarray((d * 255).astype(np.uint8)).save(f.replace('_cull.png', '_diff.png'))
print('audit done')
E
