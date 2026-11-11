"""Render the interior the way KSP assembles it: internal .mu + every PROP in the cfg, with
back faces culled. Camera given in part coordinates.
usage: blender -b -P render_iva.py -- out.png cfg gamedata --cam px,py,pz,tx,ty,tz[,lens] [--res WxH] [--samples N]"""
import bpy, sys, os, math, re, glob
from mathutils import Vector, Matrix, Quaternion
import addon_utils
addon_utils.enable('io_object_mu', default_set=True)
a = sys.argv[sys.argv.index('--') + 1:]
out, cfgp, G = a[0], a[1], a[2]
res = (1000, 760); cam = None; samples = 40; lens = 16
i = 3
while i < len(a):
    if a[i] == '--res': res = tuple(int(v) for v in a[i + 1].split('x')); i += 2
    elif a[i] == '--cam':
        v = [float(x) for x in a[i + 1].split(',')]; cam = v; i += 2
    elif a[i] == '--samples': samples = int(a[i + 1]); i += 2
    else: i += 1
if len(cam) > 6: lens = cam[6]
R_IVA = Matrix(((-1, 0, 0), (0, 0, -1), (0, -1, 0)))
# prop name -> mu
propmu = {}
for root in ('HabTechProps', 'Squad/Props', 'Benjee10_sharedAssets'):
    for f in glob.glob(os.path.join(G, root, '**', '*.cfg'), recursive=True):
        t = open(f, errors='replace').read().replace('\r', '')
        for b in re.split(r'^\s*PROP\s*$', t, flags=re.M)[1:]:
            n = re.search(r'^\s*name\s*=\s*(\S+)', b, re.M)
            if not n:
                continue
            m = re.search(r'^\s*model\s*=\s*(\S+)', b, re.M); me = re.search(r'^\s*mesh\s*=\s*(\S+)', b, re.M)
            if m: p = os.path.join(G, m.group(1) + '.mu')
            elif me:
                p = os.path.join(os.path.dirname(f), me.group(1)); p = p if p.endswith('.mu') else p + '.mu'
            else: p = os.path.join(os.path.dirname(f), 'model.mu')
            propmu.setdefault(n.group(1), p)
sc = bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
imgs = {}; nimg = {}
def load_tex(dirn, name):
    base = name.rsplit('.', 1)[0]
    for ext in ('.dds', '.png', '.jpg', '.tga', '.DDS', '.PNG', '.mbm'):
        p = os.path.join(dirn, base + ext)
        if os.path.exists(p):
            if p not in imgs: imgs[p] = bpy.data.images.load(p)
            return imgs[p], ext
    return None, None
def nmap(im):
    import numpy as np
    w, h = im.size
    if w * h > 4200000: pass
    px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    nx = px[..., 3] * 2 - 1; ny = px[..., 1] * 2 - 1
    if abs(px[..., 0].mean() - 1) > .1: nx = px[..., 0] * 2 - 1
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    new = bpy.data.images.new(im.name + '_n', w, h); new.colorspace_settings.name = 'Non-Color'
    new.pixels.foreach_set(np.dstack([nx * .5 + .5, ny * .5 + .5, nz, np.ones_like(nz)]).ravel()); new.pack()
    return new
def setup(objs, dirn):
    for o in objs:
        if o.type != 'MESH': continue
        if o.muproperties.collider != 'MU_COL_NONE':
            o.hide_render = True; continue
        for sl in o.material_slots:
            m = sl.material
            if m is None or m.get('_d'): continue
            m['_d'] = 1
            mp = m.mumatprop
            tx = {t.name: t.tex for t in mp.texture.properties}
            m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
            sh = nt.nodes.new('ShaderNodeBsdfPrincipled'); ou = nt.nodes.new('ShaderNodeOutputMaterial')
            sh.inputs['Specular'].default_value = .25; sh.inputs['Roughness'].default_value = .6
            geo = nt.nodes.new('ShaderNodeNewGeometry'); cull = nt.nodes.new('ShaderNodeMixShader'); tr0 = nt.nodes.new('ShaderNodeBsdfTransparent')
            nt.links.new(geo.outputs['Backfacing'], cull.inputs[0]); nt.links.new(tr0.outputs[0], cull.inputs[2])
            last = sh.outputs[0]
            def uvn(ext):
                n = nt.nodes.new('ShaderNodeUVMap')
                if ext and ext.lower() == '.dds':
                    mp2 = nt.nodes.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (1, -1, 1)
                    nt.links.new(n.outputs['UV'], mp2.inputs['Vector']); return mp2.outputs[0]
                return n.outputs['UV']
            if '_MainTex' in tx:
                im, ext = load_tex(dirn, tx['_MainTex'])
                if im:
                    it = nt.nodes.new('ShaderNodeTexImage'); it.image = im
                    nt.links.new(uvn(ext), it.inputs['Vector']); nt.links.new(it.outputs['Color'], sh.inputs['Base Color'])
                    if 'Translucent' in mp.shaderName or 'Cutout' in mp.shaderName or 'Alpha' in mp.shaderName:
                        tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
                        nt.links.new(it.outputs['Alpha'], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(sh.outputs[0], mx.inputs[2])
                        last = mx.outputs[0]
            if '_BumpMap' in tx:
                im, ext = load_tex(dirn, tx['_BumpMap'])
                if im:
                    if im.name not in nimg:
                        im.colorspace_settings.name = 'Non-Color'; nimg[im.name] = nmap(im)
                    it = nt.nodes.new('ShaderNodeTexImage'); it.image = nimg[im.name]
                    nt.links.new(uvn(ext), it.inputs['Vector'])
                    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.space = 'TANGENT'
                    nt.links.new(it.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs[0], sh.inputs['Normal'])
            nt.links.new(last, cull.inputs[1]); nt.links.new(cull.outputs[0], ou.inputs[0])
# internal model
t = open(cfgp).read()
model = re.search(r'model\s*=\s*SHABTech/Internals/(\S+)', t).group(1)
mu = os.path.join(os.path.dirname(cfgp), model + '.mu')
bpy.ops.import_object.ksp_mu(filepath=mu)
setup(list(bpy.data.objects), os.path.dirname(mu))
bad = []
for m in re.finditer(r'PROP\s*\{\s*name = (\S+)\s*position = ([^\n]+)\s*rotation = ([^\n]+)\s*scale = ([^\n]+)', t):
    name = m.group(1); pos = [float(x) for x in m.group(2).split(',')]; q = [float(x) for x in m.group(3).split(',')]; s = [float(x) for x in m.group(4).split(',')]
    p = propmu.get(name)
    if not p or not os.path.exists(p):
        bad.append(name); continue
    before = set(bpy.data.objects)
    bpy.ops.import_object.ksp_mu(filepath=p)
    new = [o for o in bpy.data.objects if o not in before]
    setup(new, os.path.dirname(p))
    for o in new:
        if o.type == 'LIGHT' or o.type == 'CAMERA':
            bpy.data.objects.remove(o)
    new = [o for o in new if o.name in bpy.data.objects]
    roots = [o for o in new if o.parent is None]
    for r in roots:
        r.rotation_mode = 'QUATERNION'
        r.matrix_world = Matrix.Translation((pos[0], pos[2], pos[1])) @ Quaternion((q[3], -q[0], -q[2], -q[1])).to_matrix().to_4x4() @ Matrix.Diagonal((s[0], s[2], s[1], 1)) @ r.matrix_basis
print('MISSING PROPS', bad)
for o in bpy.data.objects:
    if o.type == 'LIGHT':
        o.data.energy = 9.0; o.data.shadow_soft_size = .05; o.data.cycles.cast_shadow = False   # KSP's IVA point lights cast no shadows
bpy.context.view_layer.update()
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 4
sc.render.resolution_x, sc.render.resolution_y = res
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (.62, .72, .9, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 1.6
cd = bpy.data.cameras.new('c'); cd.lens = lens; cd.clip_start = .02; cd.clip_end = 100
co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co
loc = R_IVA @ Vector(cam[:3]); tgt = R_IVA @ Vector(cam[3:6]); up = R_IVA @ Vector((0, 0, 1))
f = (tgt - loc).normalized(); rgt = f.cross(up).normalized(); u2 = rgt.cross(f)
M = Matrix((rgt, u2, -f)).transposed().to_4x4(); M.translation = loc
co.matrix_world = M
sc.render.filepath = out; sc.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
