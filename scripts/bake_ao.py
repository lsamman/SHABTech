"""Bake ambient occlusion onto a hull sheet from a built part .blend, including everything
parented under it that isn't a collider. Output: build/tex/ao_<sheet>.png
usage: blender -b build/mu/X.blend -P bake_ao.py -- <material tex name> <out dir> [--exclude name ...] [--samples N] [--dist D]"""
import bpy, sys, os
a = sys.argv[sys.argv.index('--') + 1:]
sheet, out = a[0], a[1]
excl = []; samples = 96; dist = .35; frame = None
i = 2
while i < len(a):
    if a[i] == '--exclude': excl.append(a[i + 1]); i += 2
    elif a[i] == '--samples': samples = int(a[i + 1]); i += 2
    elif a[i] == '--dist': dist = float(a[i + 1]); i += 2
    elif a[i] == '--frame': frame = int(a[i + 1]); i += 2
    else: i += 1
import addon_utils
addon_utils.enable('io_object_mu', default_set=True)
sc = bpy.context.scene
if frame is not None:
    sc.frame_set(frame)
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = False
w = bpy.data.worlds.new('w'); sc.world = w
w.light_settings.distance = dist
img = bpy.data.images.new('ao', 2048, 2048, alpha=False, float_buffer=False)
img.generated_color = (1, 1, 1, 1)
targets = []
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    if o.muproperties.collider != 'MU_COL_NONE' or any(e == o.name for e in excl):
        o.hide_render = True; o.hide_set(True); continue
    o.hide_render = False
    has = False
    for sl in o.material_slots:
        m = sl.material
        if not m:
            continue
        m.use_nodes = True
        nt = m.node_tree; nt.nodes.clear()
        bs = nt.nodes.new('ShaderNodeBsdfDiffuse'); ou = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(bs.outputs[0], ou.inputs[0])
        tx = {t.name: t.tex for t in m.mumatprop.texture.properties}
        if tx.get('_MainTex', '').startswith(sheet + '_'):
            it = nt.nodes.new('ShaderNodeTexImage'); it.image = img; nt.nodes.active = it
            has = True
    if has:
        targets.append(o)
print('BAKE targets', [o.name for o in targets])
bpy.ops.object.select_all(action='DESELECT')
for o in targets:
    o.select_set(True)
bpy.context.view_layer.objects.active = targets[0]
bpy.ops.object.bake(type='AO', margin=6, use_clear=False)
img.filepath_raw = os.path.join(out, f'ao_{sheet}.png'); img.file_format = 'PNG'; img.save()
print('BAKED', img.filepath_raw)
