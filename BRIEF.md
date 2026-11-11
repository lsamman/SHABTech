# SHABTech build contract

Stack, top to bottom: `shab_TPS` -> `shab_PCM` -> (`shab_SM` for orbit, or for Mars:) `shab_Lander` -> `shab_HIAD` -> `shab_Nose` -> `shab_Adapter` -> F9 upper stage (Tundra).

## Scale
HabTech: real metres x 0.585 (`sl.SCALE`, `sl.real()`). Diameters that come out: PCM 1.875 m, stowed lander 5.85 m (real 10 m), inflated HIAD 9.36 m (real 16 m), PCM mounts at r = 0.80 with a size-2 node.

## Rules every part follows
- Build script: `scripts/build_<part>.py`, takes the output dir after `--`, uses `sl.py` and `greebles.py`. Model at final KSP metres, +Z up. Export with `P.export(out)` and `P.save_blend(out)`. Part name equals the .mu name.
- `cfg/<part>.cfg`: hand-written PART config, `MODEL { model = SHABTech/Parts/<part> }`, title/description in a dry KSP tone, manufacturer `SHABTech Consortium`, author `lsamman`.
- New texture sheets: `scripts/tex_<sheet>.py` using `tl.py`, writing `<sheet>_diff/nrm.dds` into `$SHAB_TEX` (build/tex). Greebles use the shared `shab_details` atlas. Unique-mapped sheets get an AO bake from `scripts/bake_ao.py` multiplied in, the way `tex_hull.py` does it. Target diffuse p90 about 0.78, gloss by material (see `tex_details.py`).
- Add helpers in your own module (for example `scripts/gr_lander.py`). `sl.py`, `tl.py`, `layout.py`, `greebles.py`, `tex_details.py`: additive changes only, never change behaviour other parts rely on. New atlas zones go in your own sheet.
- Texture style is HabTech2 and Benjee10's Orion: brand-new and stylised, never weathered. Flat colour, crisp thin panel lines, bright bevel edges, no grime, soot, scorch, scuffs or noise. About 85% of a normal map should be perfectly flat, with relief only on real features. `tl.CLEAN` turns the noise generators off.
- KSP culls backfaces and Cycles does not. Check with `scripts/render_stack.py` (culls by default) and `scripts/audit_culling.sh <dir>`. `scripts/facing.py` flips or doubles wrongly facing islands at export.
- Quality bar is HabTech2. Simple hull with a rich unique or trim texture, real geometry for what sticks out, bolts and fine detail in the normal map, baked AO for contact shadows, one material per mesh object. Budget: under 60k tris per part, under 2 draw-call-heavy sheets per part.
- Real panels, fasteners, stencils and plumbing that make functional sense. Improvise from real spacecraft where the paper is silent. Nothing floats, nothing clips by accident.
- Colliders: convex hulls only (under 255 tris each, `P.hull_collider`); hollow things need several. Triggers via `P.box_trigger`.
- Animations: `P.key(clip, obj, frame, rotation_quaternion=..., location=...)`, then `P.bake_clips(0)`; the clip's frame 0 is the stowed pose. The exporter ignores `matrix_parent_inverse`; use `P.place`/`P.mesh(frame=...)`. Thrust transforms: `thrustTransform` empties with local +Z along the exhaust (the exporter adds a +90 deg X correction).
- Unity = (bx, bz, by) for cfg positions. `P.node` handles it in the json; the cfg must match.
- Tangents need tris/quads only, no n-gons. Faces must point outward (single-sided in KSP).

## Machine limits
KSP is running at about 37 GB of 46 GB RAM. Never run two Cycles jobs at once: wrap every render or bake in `flock build/.render.lock`. Keep previews at or below 1100x1000, 48 samples. Never kill KSP. Do not write into the KSP install (deployment is done at the end).

## Review
Render with `scripts/render_mu.py` (see its docstring; `--hide name` hides a variant) and LOOK at the image with Read. Iterate until it would sit credibly next to HabTech's Destiny. Check from at least three angles, deployed and stowed. Run `python3 -I scripts/lint.py` on a staging copy of your parts if useful; the full lint runs at integration.

## Not yet testable in-game
Nobody can launch KSP during this build. Base every module config on a working stock or Benjee10 config read from the install, quote real module and field names, and flag anything unverified.
