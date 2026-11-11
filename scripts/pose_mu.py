"""Render a built part's .blend at a chosen clip frame with real textures, for checking
stowed and deployed poses. The .mu importer loses NLA keys we want, so this opens the .blend.
usage: blender -b build/mu/X.blend -P pose_mu.py -- out.png --frame N --res WxH --view az,el,dist[,tx,ty,tz] [--samples N] [--hide name] [--sun az,el]"""
import bpy, sys, os, math, addon_utils
from mathutils import Vector
addon_utils.enable('io_object_mu', default_set=True)
a = sys.argv[sys.argv.index('--') + 1:]
out = a[0]; a = a[1:]
frame = 0; res = (1000, 800); view = None; samples = 48; sun = (35, 40); hide = []
i = 0
while i < len(a):
    if a[i] == '--frame': frame = int(a[i + 1]); i += 2
    elif a[i] == '--res': res = tuple(int(v) for v in a[i + 1].split('x')); i += 2
    elif a[i] == '--view': view = [float(v) for v in a[i + 1].split(',')]; i += 2
    elif a[i] == '--samples': samples = int(a[i + 1]); i += 2
    elif a[i] == '--sun': sun = tuple(float(v) for v in a[i + 1].split(',')); i += 2
    elif a[i] == '--hide': hide.append(a[i + 1]); i += 2
    else: i += 1
sc = bpy.context.scene
texdir = os.path.join(os.path.dirname(bpy.data.filepath), '..', 'tex')
imgs = {}
def tex(name):
    base = name.rsplit('.', 1)[0]
    p = os.path.join(texdir, base + '.dds')
    if not os.path.exists(p):
        print('NOTEX', name); return None
    if p not in imgs:
        imgs[p] = bpy.data.images.load(p)
    return imgs[p]
def nimage(im):
    import numpy as np
    w, h = im.size
    px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    nx = px[..., 3] * 2 - 1; ny = px[..., 1] * 2 - 1
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    new = bpy.data.images.new(im.name + '_n', w, h)
    new.colorspace_settings.name = 'Non-Color'
    new.pixels.foreach_set(np.dstack([nx * .5 + .5, ny * .5 + .5, nz, np.ones_like(nz)]).ravel()); new.pack()
    return new
nm = {}
for m in bpy.data.materials:
    tx = {t.name: t.tex for t in m.mumatprop.texture.properties}
    if '_MainTex' not in tx:
        continue
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    sh = nt.nodes.new('ShaderNodeBsdfPrincipled'); ou = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(sh.outputs[0], ou.inputs[0])
    sh.inputs['Specular'].default_value = .4
    uv = nt.nodes.new('ShaderNodeUVMap'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, -1, 1)
    nt.links.new(uv.outputs[0], mp.inputs[0])
    im = tex(tx['_MainTex'])
    if im:
        it = nt.nodes.new('ShaderNodeTexImage'); it.image = im; nt.links.new(mp.outputs[0], it.inputs[0])
        nt.links.new(it.outputs['Color'], sh.inputs['Base Color'])
        inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = .85
        nt.links.new(it.outputs['Alpha'], inv.inputs[1]); nt.links.new(inv.outputs[0], sh.inputs['Roughness'])
    if '_BumpMap' in tx:
        im = tex(tx['_BumpMap'])
        if im:
            if im.name not in nm:
                im.colorspace_settings.name = 'Non-Color'; nm[im.name] = nimage(im)
            it = nt.nodes.new('ShaderNodeTexImage'); it.image = nm[im.name]; nt.links.new(mp.outputs[0], it.inputs[0])
            n = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(it.outputs['Color'], n.inputs['Color']); nt.links.new(n.outputs[0], sh.inputs['Normal'])
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.hide_render = o.muproperties.collider != 'MU_COL_NONE' or any(h in o.name for h in hide)
sc.frame_set(frame)
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render for c in o.bound_box]
mn = Vector([min(p[k] for p in pts) for k in range(3)]); mx = Vector([max(p[k] for p in pts) for k in range(3)])
ctr = (mn + mx) / 2; rad = (mx - mn).length / 2
print('BBOX', [round(v, 3) for v in mn], [round(v, 3) for v in mx])
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 3
sc.render.resolution_x, sc.render.resolution_y = res
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (.02, .025, .03, 1)
sd = bpy.data.lights.new('s', 'SUN'); sd.energy = 5.5; sd.angle = math.radians(1.5)
so = bpy.data.objects.new('s', sd); sc.collection.objects.link(so); so.rotation_euler = (math.radians(90 - sun[1]), 0, math.radians(sun[0] + 90))
fd = bpy.data.lights.new('f', 'SUN'); fd.energy = .8; fo = bpy.data.objects.new('f', fd); sc.collection.objects.link(fo); fo.rotation_euler = (math.radians(75), 0, math.radians(sun[0] - 110))
cd = bpy.data.cameras.new('c'); cd.lens = 55; cd.clip_start = .02; cd.clip_end = 1000
cam = bpy.data.objects.new('c', cd); sc.collection.objects.link(cam); sc.camera = cam
az, el = (view[0], view[1]) if view else (35, 15)
dist = view[2] if view and len(view) > 2 and view[2] > 0 else rad * 3.2
tgt = Vector(view[3:6]) if view and len(view) >= 6 else ctr
d = Vector((math.cos(math.radians(el)) * math.sin(math.radians(az)), -math.cos(math.radians(el)) * math.cos(math.radians(az)), math.sin(math.radians(el))))
cam.location = tgt + d * dist; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = out; sc.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
