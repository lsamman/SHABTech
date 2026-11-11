"""Offline checks for the SHABTech package, since KSP itself can't run here unattended:
  * every cfg parses (balanced braces)
  * every MODEL exists; every texture a .mu references exists as a DDS next to it
  * transform / animation names used by modules exist in the .mu
  * module names exist in installed assemblies; B9 tank types are defined
usage: python3 -I scripts/lint.py <GameData/SHABTech> [installed GameData]"""
import os, re, sys, glob
A = os.path.expanduser('~/Applications/blender-3.6/3.6/scripts/addons/io_object_mu')
sys.path.insert(0, A)
from mu import Mu
root = sys.argv[1]
gd = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser('~/.local/share/Steam/steamapps/common/Kerbal Space Program Modded SOL/GameData')
errs = []; warns = []
STOCK = open(os.path.join(os.path.dirname(gd), 'KSP_x64_Data', 'Managed', 'Assembly-CSharp.dll'), 'rb').read() if os.path.exists(os.path.join(os.path.dirname(gd), 'KSP_x64_Data', 'Managed', 'Assembly-CSharp.dll')) else b''
extra = b''
for dll in ('B9PartSwitch', 'Waterfall', 'KAS', 'FreeIva', 'KSPCommunityPartModules'):
    for f in glob.glob(os.path.join(gd, dll, '**', '*.dll'), recursive=True):
        extra += open(f, 'rb').read()
ASMS = STOCK + extra


def known_module(n):
    return n.encode() in ASMS or n.encode('utf-16-le') in ASMS


def walk(o, names, anims, mats):
    names.add(o.transform.name)
    if hasattr(o, 'animation'):
        for c in o.animation.clips:
            anims.add(c.name)
    for c in o.children:
        walk(c, names, anims, mats)


mu_info = {}
for f in glob.glob(os.path.join(root, '**', '*.mu'), recursive=True):
    m = Mu()
    if not m.read(f):
        errs.append(f'unreadable mu {f}'); continue
    names, anims = set(), set()
    walk(m.obj, names, anims, None)
    mu_info[os.path.splitext(os.path.relpath(f, os.path.dirname(root)))[0]] = (names, anims)
    d = os.path.dirname(f)
    for t in m.textures:
        base = os.path.splitext(t.name)[0]
        if not any(os.path.exists(os.path.join(d, base + e)) for e in ('.dds', '.png')):
            errs.append(f'{os.path.basename(f)}: missing texture {t.name}')
    # vertex limit
    def verts(o):
        if hasattr(o, 'shared_mesh') and len(o.shared_mesh.verts) > 65000:
            errs.append(f'{os.path.basename(f)}: {o.transform.name} has {len(o.shared_mesh.verts)} verts')
        for c in o.children:
            verts(c)
    verts(m.obj)
tanks = set()
for c in glob.glob(os.path.join(root, '**', '*.cfg'), recursive=True):
    tanks |= set(re.findall(r'B9_TANK_TYPE\s*\{\s*name\s*=\s*(\S+)', open(c, errors='replace').read()))
for c in glob.glob(os.path.join(gd, 'B9PartSwitch', '**', '*.cfg'), recursive=True) + glob.glob(os.path.join(gd, 'CommunityResourcePack', '**', '*.cfg'), recursive=True):
    tanks |= set(re.findall(r'B9_TANK_TYPE\s*\{\s*name\s*=\s*(\S+)', open(c, errors='replace').read()))
TF = {'pivotName', 'raycastTransformName', 'thrustVectorTransformName', 'transformName', 'gimbalTransformName', 'wheelColliderTransformName', 'wheelTransformName', 'suspensionTransformName', 'lightName', 'jettisonName', 'bottomNodeName_', 'secondaryTransformName', 'referenceTransformName', 'RCSTransformName', 'thrustTransformName', 'partCollider_', 'portTransformName', 'nodeTransformName', 'controlTransformName', 'includedRenderer', 'transform', 'deployTargetTransformName', 'retractedDeployTransformName', 'wheelTransformName', 'leverTransform', 'ImpactTransform', 'colliderTransformName', 'wheelColliderTransformName', 'suspensionTransformName', 'suspensionColliderName', 'clipObject', 'bogeyTransformName', 'animationTrfName', 'retractTransformName', 'deployTargetTransformName', 'damagedTransformName', 'undamagedTransformName', 'impactDamageColliderName', 'caliperTransformName', 'thrusterTransformName', 'gimbalTransformName', 'targetName', 'rotatorsName'}
for c in glob.glob(os.path.join(root, '**', '*.cfg'), recursive=True):
    t = open(c, errors='replace').read()
    s = re.sub(r'//.*', '', t)
    if s.count('{') != s.count('}'):
        errs.append(f'{c}: unbalanced braces {s.count("{")} vs {s.count("}")}')
    for pt in re.finditer(r'^\s*PART\s*\{', s, re.M):
        pass
    models = [m_ for m_ in re.findall(r'model\s*=\s*(\S+)', s) if '*' not in m_]   # KAS renderer paths use * patterns
    allnames = set(); allanims = set()
    for m_ in models:
        key = m_
        if key in mu_info:
            allnames |= mu_info[key][0]; allanims |= mu_info[key][1]
        elif not os.path.exists(os.path.join(gd, key + '.mu')) and not os.path.exists(os.path.join(os.path.dirname(root), key + '.mu')):
            errs.append(f'{os.path.basename(c)}: model not found {m_}')
    for n in re.findall(r'MODULE\s*\{\s*name\s*=\s*(\S+)', s):
        if not known_module(n):
            warns.append(f'{os.path.basename(c)}: module {n} not found in scanned assemblies')
    if models and all(m_ in mu_info for m_ in models):
        for k, v in re.findall(r'^\s*(\w+)\s*=\s*([^\n]+)$', s, re.M):
            v = v.strip()
            if k == 'animationName' and v not in allanims:
                errs.append(f'{os.path.basename(c)}: animation {v} not in model {sorted(allanims)}')
            if k in TF and k != 'includedRenderer':
                for name in re.split(r'\s*,\s*', v):
                    if name and name not in allnames and name not in ('Thrust', 'thrustTransform'):
                        errs.append(f'{os.path.basename(c)}: {k} = {name} not in model')
            if k == 'includedRenderer':
                for name in re.split(r'\s*,\s*', v):
                    if name and name not in allnames:
                        errs.append(f'{os.path.basename(c)}: includedRenderer {name} not in model')
            if k == 'tankType' and v not in tanks:
                errs.append(f'{os.path.basename(c)}: tankType {v} undefined')
    if not STOCK:
        warns.append('stock assembly not found, module names unchecked')
for w in sorted(set(warns)):
    print('WARN', w)
for e in errs:
    print('ERROR', e)
print(f'lint: {len(mu_info)} models, {len(errs)} errors, {len(set(warns))} warnings')
sys.exit(1 if errs else 0)
