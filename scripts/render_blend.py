"""Render a part .blend at an animation frame with real textures (Cycles CPU), optionally with
extra .mu files placed in the scene. Handles Cutoff shaders and hides broken-wheel stand-ins.
usage: blender -b X.blend -P render_blend.py -- out.png --frame N --res WxH --view az,el,dist[,tx,ty,tz] [--hide name] [--mu file@x,y,z[,yaw]] [--samples N]"""
import bpy, sys, os, math, addon_utils
from mathutils import Vector
addon_utils.enable('io_object_mu', default_set=True)
a = sys.argv[sys.argv.index('--') + 1:]
out = a[0]; a = a[1:]
res = (1100, 800); view = None; hide = ['bustedwheel', 'bustedrotor']; samples = 48; frame = 0; mus = []; sun = (35, 40); bg = (.02, .025, .03)
i = 0
while i < len(a):
    k = a[i]
    if k == '--res': res = tuple(int(v) for v in a[i + 1].split('x'))
    elif k == '--view': view = [float(v) for v in a[i + 1].split(',')]
    elif k == '--hide': hide.append(a[i + 1])
    elif k == '--samples': samples = int(a[i + 1])
    elif k == '--frame': frame = int(a[i + 1])
    elif k == '--mu': mus.append(a[i + 1])
    elif k == '--sun': sun = tuple(float(v) for v in a[i + 1].split(','))
    i += 2
sc = bpy.context.scene
texdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build', 'tex')
extra_dirs = []
for spec in mus:
    pos = (0, 0, 0); yaw = 0
    if '@' in spec:
        spec, tr = spec.split('@'); t = [float(v) for v in tr.split(',')]
        pos = tuple(t[:3]); yaw = t[3] if len(t) > 3 else 0
    before = set(bpy.data.objects)
    bpy.ops.import_object.ksp_mu(filepath=spec)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.type in ('CAMERA', 'LIGHT'):
            bpy.data.objects.remove(o)
    new = [o for o in bpy.data.objects if o not in before]
    for r in [o for o in new if o.parent is None]:
        r.location = Vector(pos) + r.location
        if yaw:
            r.rotation_mode = 'XYZ'; r.rotation_euler.z += math.radians(yaw)
    extra_dirs.append(os.path.dirname(spec))
imgs = {}; nimg = {}
def load_tex(name):
    base = name.rsplit('.', 1)[0]
    for d_ in [texdir] + extra_dirs:
        for ext in ('.dds', '.png'):
            p = os.path.join(d_, base + ext)
            if os.path.exists(p):
                if p not in imgs:
                    imgs[p] = bpy.data.images.load(p)
                return imgs[p], ext
    print('NOTEX', name); return None, None
def prev_normal(im):
    import numpy as np
    w, h = im.size
    px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    nx = px[..., 3] * 2 - 1; ny = px[..., 1] * 2 - 1
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    new = bpy.data.images.new(im.name + '_n', w, h)
    new.colorspace_settings.name = 'Non-Color'
    new.pixels.foreach_set(np.dstack([nx * .5 + .5, ny * .5 + .5, nz, np.ones_like(nz)]).ravel()); new.pack()
    return new
for o in bpy.data.objects:
    if o.type == 'LIGHT':
        o.hide_render = True
    if o.type != 'MESH':
        continue
    if o.muproperties.collider != 'MU_COL_NONE' or any(h == o.name.split('.')[0] or h in o.name for h in hide):
        o.hide_render = True; continue
    for sl in o.material_slots:
        m = sl.material
        if m is None or m.get('_done'):
            continue
        m['_done'] = 1
        mp = m.mumatprop
        tx = {t.name: t.tex for t in mp.texture.properties}
        flts = {t.name: t.value for t in mp.float3.properties}
        cols = {t.name: t.value for t in mp.color.properties}
        m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
        sh = nt.nodes.new('ShaderNodeBsdfPrincipled'); ou = nt.nodes.new('ShaderNodeOutputMaterial')
        sh.inputs['Specular'].default_value = .4; sh.inputs['Roughness'].default_value = .55
        def uvnode(ext):
            n = nt.nodes.new('ShaderNodeUVMap')
            if ext and ext.lower() == '.dds':
                mp2 = nt.nodes.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (1, -1, 1)
                nt.links.new(n.outputs['UV'], mp2.inputs['Vector']); return mp2.outputs[0]
            return n.outputs['UV']
        linked = False
        if '_MainTex' in tx:
            im, ext = load_tex(tx['_MainTex'])
            if im:
                it = nt.nodes.new('ShaderNodeTexImage'); it.image = im
                nt.links.new(uvnode(ext), it.inputs['Vector'])
                nt.links.new(it.outputs['Color'], sh.inputs['Base Color'])
                if 'Cutoff' in mp.shaderName or 'Translucent' in mp.shaderName:
                    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
                    if 'Cutoff' in mp.shaderName:
                        gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = flts.get('_Cutoff', .5)
                        nt.links.new(it.outputs['Alpha'], gt.inputs[0]); nt.links.new(gt.outputs[0], mx.inputs[0])
                    else:
                        nt.links.new(it.outputs['Alpha'], mx.inputs[0])
                    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(sh.outputs[0], mx.inputs[2])
                    nt.links.new(mx.outputs[0], ou.inputs[0]); m.blend_method = 'HASHED'; linked = True
                else:
                    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = .85
                    nt.links.new(it.outputs['Alpha'], inv.inputs[1]); nt.links.new(inv.outputs[0], sh.inputs['Roughness'])
        if '_BumpMap' in tx:
            im, ext = load_tex(tx['_BumpMap'])
            if im:
                if im.name not in nimg:
                    im.colorspace_settings.name = 'Non-Color'
                    nimg[im.name] = prev_normal(im)
                it = nt.nodes.new('ShaderNodeTexImage'); it.image = nimg[im.name]
                nt.links.new(uvnode(ext), it.inputs['Vector'])
                nm = nt.nodes.new('ShaderNodeNormalMap'); nm.space = 'TANGENT'
                nt.links.new(it.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs[0], sh.inputs['Normal'])
        if not linked:
            nt.links.new(sh.outputs[0], ou.inputs[0])
sc.frame_set(frame)
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render for c in o.bound_box]
mn = Vector([min(p[k] for p in pts) for k in range(3)]); mx = Vector([max(p[k] for p in pts) for k in range(3)])
ctr = (mn + mx) / 2; rad = (mx - mn).length / 2
print('BBOX', [round(v, 3) for v in mn], [round(v, 3) for v in mx])
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 4
sc.render.resolution_x, sc.render.resolution_y = res
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (.02, .025, .03, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 1
sd = bpy.data.lights.new('s', 'SUN'); sd.energy = 5.5; sd.angle = math.radians(1.5)
so = bpy.data.objects.new('s', sd); sc.collection.objects.link(so)
so.rotation_euler = (math.radians(90 - sun[1]), 0, math.radians(sun[0] + 90))
fd = bpy.data.lights.new('f', 'SUN'); fd.energy = .8; fo = bpy.data.objects.new('f', fd); sc.collection.objects.link(fo)
fo.rotation_euler = (math.radians(75), 0, math.radians(sun[0] - 110))
cd = bpy.data.cameras.new('c'); cd.lens = 55; cd.clip_start = .02; cd.clip_end = 1000
cam = bpy.data.objects.new('c', cd); sc.collection.objects.link(cam); sc.camera = cam
az, el = (view[0], view[1]) if view else (35, 15)
dist = view[2] if view and len(view) > 2 and view[2] > 0 else rad * 3.2
tgt = Vector(view[3:6]) if view and len(view) >= 6 else ctr
d = Vector((math.cos(math.radians(el)) * math.sin(math.radians(az)), -math.cos(math.radians(el)) * math.cos(math.radians(az)), math.sin(math.radians(el))))
cam.location = tgt + d * dist
cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = out; sc.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
