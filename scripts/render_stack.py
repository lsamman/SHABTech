"""Render an assembly of built parts, each posed at its own clip frame, with real textures.
usage: blender -b --factory-startup -P render_stack.py -- out.png --res WxH --view az,el,dist[,tx,ty,tz]
       [--samples N] [--sun az,el] [--hide name] [--cullcheck | --nocull] part.blend[@x,y,z[,yaw[,pitch]]][:frame] ...
Opens the .blend files because the .mu importer loses the NLA keys. Blender coordinates, +Z up."""
import bpy, sys, os, math, addon_utils
import numpy as np
from mathutils import Vector, Matrix
addon_utils.enable('io_object_mu', default_set=True)
a = sys.argv[sys.argv.index('--') + 1:]
out = a[0]; a = a[1:]
res = (1100, 900); view = None; samples = 48; sun = (35, 40); hide = []; specs = []
cullcheck = False   # paints backfaces magenta instead of hiding them, to audit winding
nocull = False      # draws both sides; diff against a normal render to find real holes
i = 0
while i < len(a):
    if a[i] == '--res': res = tuple(int(v) for v in a[i + 1].split('x')); i += 2
    elif a[i] == '--view': view = [float(v) for v in a[i + 1].split(',')]; i += 2
    elif a[i] == '--samples': samples = int(a[i + 1]); i += 2
    elif a[i] == '--sun': sun = tuple(float(v) for v in a[i + 1].split(',')); i += 2
    elif a[i] == '--hide': hide.append(a[i + 1]); i += 2
    elif a[i] == '--cullcheck': cullcheck = True; i += 1
    elif a[i] == '--nocull': nocull = True; i += 1
    else: specs.append(a[i]); i += 1
sc = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
texdir = os.environ.get('RENDER_TEX') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build', 'tex')
imgs = {}; nm = {}


def tex(name):
    base = name.rsplit('.', 1)[0]
    p = os.path.join(texdir, base + '.dds')
    if not os.path.exists(p):
        print('NOTEX', name); return None
    if p not in imgs:
        imgs[p] = bpy.data.images.load(p)
    return imgs[p]


def nimage(im):
    w, h = im.size
    px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    nx = px[..., 3] * 2 - 1; ny = px[..., 1] * 2 - 1
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    new = bpy.data.images.new(im.name + '_n', w, h)
    new.colorspace_settings.name = 'Non-Color'
    new.pixels.foreach_set(np.dstack([nx * .5 + .5, ny * .5 + .5, nz, np.ones_like(nz)]).ravel()); new.pack()
    return new


def setup_material(m):
    if m.get('_done'):
        return
    m['_done'] = 1
    tx = {t.name: t.tex for t in m.mumatprop.texture.properties}
    if '_MainTex' not in tx:
        return
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    sh = nt.nodes.new('ShaderNodeBsdfPrincipled'); ou = nt.nodes.new('ShaderNodeOutputMaterial')
    # KSP draws front faces only, so backfaces must not show here either
    geo = nt.nodes.new('ShaderNodeNewGeometry'); mix = nt.nodes.new('ShaderNodeMixShader')
    if cullcheck:
        bk = nt.nodes.new('ShaderNodeEmission'); bk.inputs[0].default_value = (1, 0, 1, 1); bk.inputs[1].default_value = 2
    else:
        bk = nt.nodes.new('ShaderNodeBsdfTransparent')
    nt.links.new(geo.outputs['Backfacing'], mix.inputs[0]); nt.links.new(sh.outputs[0], mix.inputs[1]); nt.links.new(sh.outputs[0] if nocull else bk.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], ou.inputs[0])
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


for spec in specs:
    frame = 0; pos = (0, 0, 0); yaw = 0; pitch = 0
    if ':' in spec:
        spec, f_ = spec.rsplit(':', 1); frame = int(f_)
    if '@' in spec:
        spec, tr = spec.split('@'); t = [float(v) for v in tr.split(',')]
        pos = tuple(t[:3]); yaw = t[3] if len(t) > 3 else 0; pitch = t[4] if len(t) > 4 else 0
    with bpy.data.libraries.load(spec, link=False) as (src, dst):
        dst.objects = list(src.objects)
    objs = [o for o in dst.objects if o is not None]
    for o in objs:
        sc.collection.objects.link(o)
    sc.frame_set(frame)
    bpy.context.view_layer.update()
    place = Matrix.Translation(pos) @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(pitch), 4, 'X')
    wm = {o: o.matrix_world.copy() for o in objs}
    for o in objs:
        o.animation_data_clear()
    for o in objs:
        o.parent = None
        o.matrix_parent_inverse = Matrix.Identity(4)
    for o in objs:
        o.matrix_world = place @ wm[o]
    for o in objs:
        o.hide_render = o.type != 'MESH' or o.muproperties.collider != 'MU_COL_NONE' or any(h in o.name for h in hide)
        if o.type == 'MESH' and not o.hide_render:
            for s_ in o.material_slots:
                if s_.material:
                    setup_material(s_.material)
sc.frame_set(0)
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render for c in o.bound_box]
mn = Vector([min(p[k] for p in pts) for k in range(3)]); mx = Vector([max(p[k] for p in pts) for k in range(3)])
ctr = (mn + mx) / 2; rad = (mx - mn).length / 2
print('BBOX', [round(v, 3) for v in mn], [round(v, 3) for v in mx])
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 8; sc.cycles.transparent_max_bounces = 16
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
sc.render.filepath = os.path.abspath(out); sc.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
