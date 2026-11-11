"""Render one or more KSP .mu files with their real textures in Cycles CPU.
usage: blender -b -P render_mu.py -- out.png --res 1100x800 --view az,el,dist[,tx,ty,tz] file1.mu[@x,y,z[,yawdeg]] ...
KSP-like lighting: one hard sun plus dim ambient, specular via principled.
"""
import bpy, sys, os, math, addon_utils
from mathutils import Vector
addon_utils.enable('io_object_mu', default_set=True)
a = sys.argv[sys.argv.index('--') + 1:]
out = a[0]; a = a[1:]
res = (1100, 800); view = None; files = []; hide = []; anim = {}; samples = 48; sun = (35, 40)
i = 0
while i < len(a):
    if a[i] == '--res': res = tuple(int(v) for v in a[i + 1].split('x')); i += 2
    elif a[i] == '--view': view = [float(v) for v in a[i + 1].split(',')]; i += 2
    elif a[i] == '--hide': hide.append(a[i + 1]); i += 2
    elif a[i] == '--samples': samples = int(a[i + 1]); i += 2
    elif a[i] == '--sun': sun = tuple(float(v) for v in a[i + 1].split(',')); i += 2
    elif a[i] == '--anim': anim[a[i + 1].split('=')[0]] = float(a[i + 1].split('=')[1]); i += 2
    else: files.append(a[i]); i += 1
sc = bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
imgs = {}
def load_tex(dirn, name):
    base = name.rsplit('.', 1)[0]
    for d_ in (dirn, os.path.join(dirn, '..', 'tex')):
        for ext in ('.dds', '.png', '.jpg', '.tga', '.DDS'):
            p = os.path.join(d_, base + ext)
            if os.path.exists(p):
                if p not in imgs:
                    imgs[p] = bpy.data.images.load(p)
                return imgs[p], ext
    print('NOTEX', name)
    return None, None
def prev_normal_image(im):
    # DXT5nm -> tangent normal: x in A, y in G
    import numpy as np
    w, h = im.size
    px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    nx = px[..., 3] * 2 - 1; ny = px[..., 1] * 2 - 1
    if abs(px[..., 0].mean() - 1) > 0.1:   # plain RGB normal (png)
        nx = px[..., 0] * 2 - 1
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    new = bpy.data.images.new(im.name + '_n', w, h, float_buffer=False)
    new.colorspace_settings.name = 'Non-Color'
    p2 = np.dstack([nx * .5 + .5, ny * .5 + .5, nz, np.ones_like(nz)])
    new.pixels.foreach_set(p2.ravel()); new.pack()
    return new
nimg = {}
all_new = []
for spec in files:
    pos = (0, 0, 0); yaw = 0; pitch = 0
    if '@' in spec:
        spec, tr = spec.split('@'); t = [float(v) for v in tr.split(',')]
        pos = tuple(t[:3]); yaw = t[3] if len(t) > 3 else 0
        pitch = t[4] if len(t) > 4 else 0
    before = set(bpy.data.objects)
    bpy.ops.import_object.ksp_mu(filepath=spec)
    new = [o for o in bpy.data.objects if o not in before]
    all_new += new
    for o in new:
        o.hide_render = False
    dirn = os.path.dirname(spec)
    for o in new:
        if o.type != 'MESH':
            continue
        if o.muproperties.collider != 'MU_COL_NONE' or any(h in o.name for h in hide):
            o.hide_render = True; continue
        for sl in o.material_slots:
            m = sl.material
            if m is None or m.get('_done'):
                continue
            m['_done'] = 1
            mp = m.mumatprop
            tx = {t.name: t.tex for t in mp.texture.properties}
            cols = {t.name: t.value for t in mp.color.properties}
            flts = {t.name: t.value for t in mp.float3.properties}
            m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
            sh = nt.nodes.new('ShaderNodeBsdfPrincipled'); ou = nt.nodes.new('ShaderNodeOutputMaterial')
            sh.inputs['Base Color'].default_value = (.6, .6, .6, 1)
            sh.inputs['Metallic'].default_value = 0; sh.inputs['Roughness'].default_value = .55
            sh.inputs['Specular'].default_value = .4
            flip = None
            def uvnode(ext):
                n = nt.nodes.new('ShaderNodeUVMap')
                if ext and ext.lower() == '.dds':
                    # DDS rows are stored top-down in KSP's sense: flip V for Blender
                    mp2 = nt.nodes.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (1, -1, 1); mp2.inputs['Location'].default_value = (0, 0, 0)
                    nt.links.new(n.outputs['UV'], mp2.inputs['Vector']); return mp2.outputs[0]
                return n.outputs['UV']
            if '_MainTex' in tx:
                im, ext = load_tex(dirn, tx['_MainTex'])
                if im:
                    it = nt.nodes.new('ShaderNodeTexImage'); it.image = im
                    nt.links.new(uvnode(ext), it.inputs['Vector'])
                    nt.links.new(it.outputs['Color'], sh.inputs['Base Color'])
                    trans = 'Alpha/Translucent' in mp.shaderName or 'Translucent' in mp.shaderName
                    if trans:
                        tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
                        nt.links.new(it.outputs['Alpha'], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(sh.outputs[0], mx.inputs[2])
                        nt.links.new(mx.outputs[0], ou.inputs[0]); m.blend_method = 'BLEND'
                    else:
                        inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = .85
                        nt.links.new(it.outputs['Alpha'], inv.inputs[1]); nt.links.new(inv.outputs[0], sh.inputs['Roughness'])
            if '_BumpMap' in tx:
                im, ext = load_tex(dirn, tx['_BumpMap'])
                if im:
                    if im.name not in nimg:
                        im.colorspace_settings.name = 'Non-Color'
                        nimg[im.name] = prev_normal_image(im)
                    it = nt.nodes.new('ShaderNodeTexImage'); it.image = nimg[im.name]
                    nt.links.new(uvnode(ext), it.inputs['Vector'])
                    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.space = 'TANGENT'
                    nt.links.new(it.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs[0], sh.inputs['Normal'])
            if '_Emissive' in tx:
                im, ext = load_tex(dirn, tx['_Emissive'])
                if im and flts.get('_EmissiveOn', 1):
                    it = nt.nodes.new('ShaderNodeTexImage'); it.image = im
                    nt.links.new(uvnode(ext), it.inputs['Vector'])
                    nt.links.new(it.outputs['Color'], sh.inputs['Emission'])
                    ec = cols.get('_EmissiveColor', (0, 0, 0, 1)); sh.inputs['Emission Strength'].default_value = max(ec[0], ec[1], ec[2])
            if not ou.inputs[0].is_linked:
                nt.links.new(sh.outputs[0], ou.inputs[0])
    roots = [o for o in new if o.parent is None]
    for r in roots:
        r.location = Vector(pos) + r.location
        if yaw or pitch:
            r.rotation_mode = 'XYZ'; r.rotation_euler.z += math.radians(yaw); r.rotation_euler.y += math.radians(pitch)
    # keep the import's cameras/lights out
    for o in new:
        if o.type in ('CAMERA', 'LIGHT'):
            bpy.data.objects.remove(o)
all_new = [o for o in bpy.data.objects]
# animation scrub: set NLA strip at a given fraction
for name, frac in anim.items():
    pass
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render for c in o.bound_box]
mn = Vector([min(p[k] for p in pts) for k in range(3)]); mx = Vector([max(p[k] for p in pts) for k in range(3)])
ctr = (mn + mx) / 2; rad = (mx - mn).length / 2
print('BBOX', [round(v, 3) for v in mn], [round(v, 3) for v in mx])
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 3
sc.render.resolution_x, sc.render.resolution_y = res
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (.02, .025, .03, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
sd = bpy.data.lights.new('s', 'SUN'); sd.energy = 5.5; sd.angle = math.radians(1.5)
so = bpy.data.objects.new('s', sd); sc.collection.objects.link(so)
so.rotation_euler = (math.radians(90 - sun[1]), 0, math.radians(sun[0] + 90))
fd = bpy.data.lights.new('f', 'SUN'); fd.energy = .8; fo = bpy.data.objects.new('f', fd); sc.collection.objects.link(fo)
fo.rotation_euler = (math.radians(75), 0, math.radians(sun[0] - 110))
cd = bpy.data.cameras.new('c'); cd.lens = 55; cd.clip_start = .02; cd.clip_end = 1000
cam = bpy.data.objects.new('c', cd); sc.collection.objects.link(cam); sc.camera = cam
az, el = (view[0], view[1]) if view else (35, 15)
dist = (view[2] if view and len(view) > 2 and view[2] > 0 else rad * 3.2)
tgt = Vector(view[3:6]) if view and len(view) >= 6 else ctr
d = Vector((math.cos(math.radians(el)) * math.sin(math.radians(az)), -math.cos(math.radians(el)) * math.cos(math.radians(az)), math.sin(math.radians(el))))
cam.location = tgt + d * dist
cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = out; sc.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
