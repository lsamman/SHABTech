"""Fix surfaces KSP would cull. KSP draws front faces only, so a face seen from behind is a hole.
For each connected island, rays from its faces test which side can see out of the part, in the clip's
end poses. Back side only: flip the island. Both sides: add a reversed copy. Runs at export."""
import math, random
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

N_DIRS = 8


def _hemi(n, rnd):
    # the normal, then random directions in its hemisphere
    yield n
    for _ in range(N_DIRS):
        d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
        yield d if d.dot(n) > 0 else -d


def _islands(bm):
    seen = set(); out = []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack = [f]; seen.add(f.index); isl = []
        while stack:
            c = stack.pop(); isl.append(c)
            for v in c.verts:
                for o in v.link_faces:
                    if o.index not in seen:
                        seen.add(o.index); stack.append(o)
        out.append(isl)
    return out


def _bvh(objs, dg):
    verts = []; polys = []
    for o in objs:
        ev = o.evaluated_get(dg); me = ev.data; m = ev.matrix_world
        off = len(verts)
        verts.extend(m @ v.co for v in me.vertices)
        polys.extend([off + i for i in p.vertices] for p in me.polygons)
    return BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0) if polys else None


def fix_facing(objects, frames, verbose=True, variants=()):
    # variants: one set of mesh names per B9 subtype. They are never shown together, so they don't block each other.
    meshes = [o for o in objects if o.type == 'MESH' and o.muproperties.collider == 'MU_COL_NONE' and len(o.data.polygons)]
    # damaged-state meshes share space with the good ones, so they only block themselves
    hidden = [o for o in meshes if o.muproperties.tag == 'Icon_Hidden']
    normal = [o for o in meshes if o not in hidden]
    sc = bpy.context.scene
    rnd = random.Random(7)
    votes = {o.name: {} for o in meshes}
    data = {o.name: bmesh.new() for o in meshes}
    isl_of = {}
    for o in meshes:
        bm = data[o.name]; bm.from_mesh(o.data); bm.faces.ensure_lookup_table(); bm.faces.index_update()
        isl_of[o.name] = _islands(bm)
    for fr in frames:
        sc.frame_set(fr); bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        trees = {}
        for o in meshes:
            if o in hidden:
                tree = _bvh([o], dg)
            else:
                skip = frozenset(n for g in variants if o.name in g for h in variants if h is not g for n in h)
                if skip not in trees:
                    trees[skip] = _bvh([q for q in normal if q.name not in skip], dg)
                tree = trees[skip]
            m = o.evaluated_get(dg).matrix_world; nm = m.to_3x3().inverted_safe().transposed()
            for k, isl in enumerate(isl_of[o.name]):
                v = votes[o.name].setdefault(k, [0.0, 0.0])
                step = max(1, len(isl) // 60)
                for f in isl[::step]:
                    area = f.calc_area()
                    if area < 1e-9:
                        continue
                    c = m @ f.calc_center_median()
                    n = (nm @ f.normal).normalized()
                    for side, sgn in ((0, 1), (1, -1)):
                        # score by how much of the hemisphere sees out, so a hollow interior
                        # peeking through a small gap doesn't count as an exposed surface
                        out = sum(tree.ray_cast(c + n * sgn * .0015 + d * .0005, d)[0] is None for d in _hemi(n * sgn, rnd))
                        v[side] += area * step * out / (N_DIRS + 1)
    flipped = doubled = 0
    for o in meshes:
        bm = data[o.name]
        for k, isl in enumerate(isl_of[o.name]):
            front, back = votes[o.name][k]
            if back <= 0 or back < .15 * front:
                continue
            if front < .25 * back:
                bmesh.ops.reverse_faces(bm, faces=isl)
                flipped += 1
            else:
                r = bmesh.ops.duplicate(bm, geom=list({e for f in isl for e in f.edges}) + list({v_ for f in isl for v_ in f.verts}) + isl)
                new = [g for g in r['geom'] if isinstance(g, bmesh.types.BMFace)]
                bmesh.ops.reverse_faces(bm, faces=new)
                bm.normal_update()
                # sit the copy just behind the original so the two never share a depth
                for v_ in {v2 for f in new for v2 in f.verts}:
                    v_.co += v_.normal * .0004
                doubled += 1
        bm.to_mesh(o.data); bm.free(); o.data.update()
    sc.frame_set(frames[0]); bpy.context.view_layer.update()
    if verbose:
        print(f'FACING flipped {flipped} islands, doubled {doubled}')
