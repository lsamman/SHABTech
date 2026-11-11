#!/bin/bash
# Rebuild every SHABTech part and assemble GameData/SHABTech. Set SKIP_TEX=1 to reuse textures,
# SKIP_MODELS=1 to reuse models. ONLY="leg roverwheel" rebuilds just those build scripts.
set -eo pipefail
cd "$(dirname "$0")"
B="$HOME/Applications/blender-3.6/blender"
export SHAB_TEX=build/tex
mkdir -p build/mu build/tex
if [ -z "$SKIP_MODELS" ]; then
for s in scripts/build_*.py; do
    n=$(basename "$s" .py); n=${n#build_}
    if [ -n "$ONLY" ]; then case " $ONLY " in *" $n "*) ;; *) continue ;; esac; fi
    "$B" -b --factory-startup --python-exit-code 1 -P "$s" -- build/mu 2>&1 | grep -E "EXPORT|FACING|Error|Traceback|rror:" || true
done
fi
if [ -z "$SKIP_TEX" ]; then
for t in scripts/tex_*.py; do python3 -I "$t" | tail -3; done
fi
D=GameData/SHABTech
rm -rf "$D"
mkdir -p "$D/Parts" "$D/Patches" "$D/Internals"
for f in build/mu/*.mu; do
    case "$f" in *_IVA*) ;; *) cp "$f" "$D/Parts/" ;; esac
done
cp build/tex/*.dds "$D/Parts/"
cp cfg/*.cfg "$D/Parts/"
[ -d patches ] && cp patches/*.cfg "$D/Patches/" 2>/dev/null || true
[ -d internals ] && cp -r internals/. "$D/Internals/" 2>/dev/null || true
mkdir -p "$D/Flags"
python3 -I scripts/make_flags.py "$D/Flags"
cp README.md "$D/README.md"
mkdir -p "$D/Icons"
python3 -I scripts/make_icon.py "$D/Icons"
python3 -I scripts/lint.py "$D"
