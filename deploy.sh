#!/bin/sh
# Copy GameData/SHABTech into the Sol KSP install. New parts appear on the next KSP start.
set -e
cd "$(dirname "$0")"
DEST="$HOME/.local/share/Steam/steamapps/common/Kerbal Space Program Modded SOL/GameData/SHABTech"
mkdir -p "$DEST"
cp -a GameData/SHABTech/. "$DEST/"
echo "deployed to $DEST"
