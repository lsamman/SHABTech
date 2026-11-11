"""SHABTech geometry library: procedural KSP parts in Blender 3.6, exported with io_object_mu.

Conventions
  * Blender frame of a part: +Z becomes Unity +Y (part "up"). Unity = (bx, bz, by).
  * All geometry is authored at final KSP size (metres). SCALE converts real metres.
  * Each exported mesh object has exactly one material, like HabTech.
  * Single-sided, tris and quads only (the exporter skips tangents on n-gons).
  * Hard edges come from the auto-smooth angle, so bevels catch highlights.

A Geo is a plain accumulator of verts/faces/uvs. Primitives return a Geo; add them with
Geo.add(other, matrix). Geo.to_object() turns the result into a mesh under a Part.
"""
import bpy, bmesh, json, math, os
import numpy as np
from mathutils import Matrix, Vector, Quaternion

SCALE = 0.585          # HabTech2 Destiny: 2.5 m hull / 4.27 m real
FPS = 30
TAU = math.tau


def real(m):
    """Real-world metres -> KSP metres at HabTech scale."""
    return m * SCALE


def enable_addon():
    import addon_utils
    addon_utils.enable('io_object_mu', default_set=True)


# ------------------------------------------------------------------ transforms
def T(x=0, y=0, z=0):
    return Matrix.Translation((x, y, z))


def Rz(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Z')


def Rx(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'X')


def Ry(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Y')


def S(x, y=None, z=None):
    y = x if y is None else y
    z = x if z is None else z
    return Matrix.Diagonal((x, y, z, 1))


def on_cyl(az_deg, z, r):
    """Frame on a Z-axis cylinder: local +Z points radially out, local +Y points up the
    part, local +X is tangent. Azimuth 0 faces -Y (the VAB front), increasing toward +X."""
    a = math.radians(az_deg)
    out = Vector((math.sin(a), -math.cos(a), 0))
    up = Vector((0, 0, 1))
    tan = up.cross(out)
    m = Matrix((tan, up, out)).transposed().to_4x4()
    m.translation = out * r + Vector((0, 0, z))
    return m


def climb_frame(pos, out):
    """Frame for a ladder or airlock trigger, on the Mk1 pod's pattern. Blender local Z is Unity's Y and KSP takes that
    as "up the ladder", so it runs up the part; local Y points into the wall. out is the horizontal way off the wall."""
    z = Vector((0, 0, 1))
    y = -Vector(out).normalized()
    m = Matrix((y.cross(z), y, z)).transposed().to_4x4()
    m.translation = Vector(pos)
    return m


def climb_on_cyl(az_deg, z, r):
    a = math.radians(az_deg)
    out = (math.sin(a), -math.cos(a), 0)
    return climb_frame(Vector(out) * r + Vector((0, 0, z)), out)


def frame_axes(origin, z, x=None):
    z = Vector(z).normalized()
    x = Vector(x) if x is not None else (Vector((1, 0, 0)) if abs(z.x) < .9 else Vector((0, 1, 0)))
    x = (x - x.dot(z) * z).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


# ------------------------------------------------------------------ atlas zones
class Zone:
    """Rectangle of an atlas (in pixels, origin at the image's TOP left, as painted)."""

    def __init__(self, x, y, w, h, atlas=2048, ppm=300):
        self.x, self.y, self.w, self.h, self.atlas, self.ppm = x, y, w, h, atlas, ppm

    def uv(self, s, t):
        """s,t in 0..1 across the zone (t=0 at the zone's bottom edge)."""
        px = self.x + 1 + s * (self.w - 2)
        py = self.y + 1 + (1 - t) * (self.h - 2)
        return (px / self.atlas, 1 - py / self.atlas)

    def uv_m(self, a, b, offs=(0, 0)):
        """Metres mapped at ppm, wrapped into the zone."""
        s = ((a * self.ppm + offs[0]) % (self.w - 2)) / (self.w - 2)
        t = ((b * self.ppm + offs[1]) % (self.h - 2)) / (self.h - 2)
        return self.uv(s, t)

    def span_m(self):
        return (self.w - 2) / self.ppm, (self.h - 2) / self.ppm


# ------------------------------------------------------------------ geometry accumulator
class Geo:
    def __init__(self):
        self.v = []      # Vector-like tuples
        self.f = []      # tuple of vertex indices (tri/quad)
        self.uv = []     # per-face tuple of (u,v)
        self.smooth = []

    def face(self, idx, uvs, smooth=True):
        self.f.append(tuple(idx)); self.uv.append(tuple(uvs)); self.smooth.append(smooth)

    def add(self, other, m=None):
        off = len(self.v)
        if m is None:
            self.v.extend(other.v)
        else:
            mm = np.array(m)
            a = np.array(other.v, float)
            if len(a):
                a = (np.c_[a, np.ones(len(a))] @ mm.T)[:, :3]
                if np.linalg.det(mm[:3, :3]) < 0:
                    # mirrored transform: flip winding below
                    self.v.extend(map(tuple, a))
                    for fi, fu, sm in zip(other.f, other.uv, other.smooth):
                        self.f.append(tuple(i + off for i in reversed(fi)))
                        self.uv.append(tuple(reversed(fu))); self.smooth.append(sm)
                    return self
                self.v.extend(map(tuple, a))
        for fi, fu, sm in zip(other.f, other.uv, other.smooth):
            self.f.append(tuple(i + off for i in fi))
            self.uv.append(fu); self.smooth.append(sm)
        return self

    def tris(self):
        return sum(len(f) - 2 for f in self.f)

    def points(self):
        return [Vector(p) for p in self.v]

    def to_mesh(self, name, smooth_angle=38):
        me = bpy.data.meshes.new(name)
        verts = [tuple(p) for p in self.v]
        me.from_pydata(verts, [], [list(f) for f in self.f])
        me.update()
        lay = me.uv_layers.new(name='UVMap')
        li = 0
        data = lay.data
        for poly, uvs in zip(me.polygons, self.uv):
            for k in range(poly.loop_total):
                data[poly.loop_start + k].uv = uvs[k]
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        me.use_auto_smooth = True
        me.auto_smooth_angle = math.radians(smooth_angle)
        me.update()
        return me


# ------------------------------------------------------------------ primitives
def lathe(profile, seg=48, a0=0.0, a1=360.0, zone=None, v_mode='arc', uv_fn=None, flip=False):
    """Revolve a (r,z) polyline about +Z. Faces point outward when the polyline runs upward
    on the outside of a surface (use flip=True otherwise). Azimuth 0 is -Y as in on_cyl.
    uv_fn(az_deg, r, z, arc) overrides the zone mapping."""
    g = Geo()
    n = len(profile)
    arc = [0.0]
    for i in range(1, n):
        arc.append(arc[-1] + math.hypot(profile[i][0] - profile[i - 1][0], profile[i][1] - profile[i - 1][1]))
    tot = arc[-1] or 1
    closed = abs((a1 - a0) - 360) < 1e-6
    for j in range(seg + 1):
        a = math.radians(a0 + (a1 - a0) * j / seg)
        sa, ca = math.sin(a), -math.cos(a)
        for r, z in profile:
            g.v.append((r * sa, r * ca, z))
    for j in range(seg):
        fj0 = j / seg; fj1 = (j + 1) / seg
        for i in range(n - 1):
            a_, b_, c_, d_ = j * n + i, (j + 1) * n + i, (j + 1) * n + i + 1, j * n + i + 1
            if profile[i][0] < 1e-6 and profile[i + 1][0] < 1e-6:
                continue
            if uv_fn:
                az0, az1 = a0 + (a1 - a0) * fj0, a0 + (a1 - a0) * fj1
                uvs = [uv_fn(az0, profile[i][0], profile[i][1], arc[i]), uv_fn(az1, profile[i][0], profile[i][1], arc[i]),
                       uv_fn(az1, profile[i + 1][0], profile[i + 1][1], arc[i + 1]), uv_fn(az0, profile[i + 1][0], profile[i + 1][1], arc[i + 1])]
            elif zone:
                t0, t1 = arc[i] / tot, arc[i + 1] / tot
                uvs = [zone.uv(fj0, t0), zone.uv(fj1, t0), zone.uv(fj1, t1), zone.uv(fj0, t1)]
            else:
                uvs = [(0, 0)] * 4
            idx = [a_, b_, c_, d_]
            if flip:
                idx = idx[::-1]; uvs = uvs[::-1]
            # drop degenerate side at the axis
            if profile[i][0] < 1e-6:
                idx2 = [idx[k] for k in range(4)]
                uv2 = list(uvs)
                keep = [0, 2, 3] if not flip else [0, 1, 2]
                g.face([idx2[k] for k in keep], [uv2[k] for k in keep])
            elif profile[i + 1][0] < 1e-6:
                keep = [0, 1, 2] if not flip else [1, 2, 3]
                g.face([idx[k] for k in keep], [uvs[k] for k in keep])
            else:
                g.face(idx, uvs)
    return g


def box(sx, sy, sz, zone=None, bevel=0.0, center=(0, 0, 0), offs=None):
    """Axis-aligned box with optional chamfered edges. Box-projected UVs from `zone`."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    b = min(bevel, hx * .9, hy * .9, hz * .9)
    g = Geo()
    sgn = (-1, 1)
    corner = {}

    def vid(sx_, sy_, sz_, ax):
        # chamfer-box vertex: inset b on the two axes other than `ax`
        p = [sx_ * (hx - (0 if ax == 0 else b)), sy_ * (hy - (0 if ax == 1 else b)), sz_ * (hz - (0 if ax == 2 else b))]
        k = (sx_, sy_, sz_, ax)
        if k not in corner:
            corner[k] = len(g.v)
            g.v.append((p[0] + center[0], p[1] + center[1], p[2] + center[2]))
        return corner[k]

    of = offs if offs is not None else (np.random.randint(0, 200), np.random.randint(0, 200))

    def uvq(pts, axis):
        out = []
        ids = [i for i in range(3) if i != axis]
        for p in pts:
            if zone:
                c = g.v[p]
                out.append(zone.uv_m(c[ids[0]] - center[ids[0]] + hx * 2, c[ids[1]] - center[ids[1]] + hy * 2, of))
            else:
                out.append((0, 0))
        # keep a face from wrapping across the zone edge: map by bounds instead
        if zone:
            cs = [g.v[p] for p in pts]
            a0 = min(c[ids[0]] for c in cs); a1 = max(c[ids[0]] for c in cs)
            b0 = min(c[ids[1]] for c in cs); b1 = max(c[ids[1]] for c in cs)
            sm, tm = zone.span_m()
            ds = min(1.0, (a1 - a0) / sm); dt = min(1.0, (b1 - b0) / tm)
            s0 = ((of[0] / max(1, zone.w)) % 1) * (1 - ds); t0 = ((of[1] / max(1, zone.h)) % 1) * (1 - dt)
            out = []
            for c in cs:
                fa = (c[ids[0]] - a0) / (a1 - a0 or 1); fb = (c[ids[1]] - b0) / (b1 - b0 or 1)
                out.append(zone.uv(s0 + ds * fa, t0 + dt * fb))
        return out

    # six main faces
    for ax in range(3):
        o = [i for i in range(3) if i != ax]
        for s in sgn:
            q = []
            for a, bb in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                c = [0, 0, 0]; c[ax] = s; c[o[0]] = a; c[o[1]] = bb
                q.append(vid(c[0], c[1], c[2], ax))
            # winding: outward for s>0 on (o0,o1) right-handed with ax
            rh = (o[0], o[1], ax) in ((0, 1, 2), (1, 2, 0), (2, 0, 1))
            if (s > 0) != rh:
                q = q[::-1]
            g.face(q, uvq(q, ax))
    if b > 0:
        # edge chamfers: quads between faces, corner tris
        for ax in range(3):
            o = [i for i in range(3) if i != ax]
            for s0 in sgn:
                for s1 in sgn:
                    def c(sa, ax_near):
                        v = [0, 0, 0]; v[ax] = sa; v[o[0]] = s0; v[o[1]] = s1
                        return vid(v[0], v[1], v[2], ax_near)
                    q = [c(-1, o[0]), c(1, o[0]), c(1, o[1]), c(-1, o[1])]
                    # outward check
                    pts = [Vector(g.v[i]) for i in q]
                    nrm = (pts[1] - pts[0]).cross(pts[3] - pts[0])
                    out = Vector((0, 0, 0)); out[o[0]] = s0; out[o[1]] = s1
                    if nrm.dot(out) < 0:
                        q = q[::-1]
                    g.face(q, uvq(q, o[0]))
        for sx_ in sgn:
            for sy_ in sgn:
                for sz_ in sgn:
                    tri = [vid(sx_, sy_, sz_, 0), vid(sx_, sy_, sz_, 1), vid(sx_, sy_, sz_, 2)]
                    pts = [Vector(g.v[i]) for i in tri]
                    nrm = (pts[1] - pts[0]).cross(pts[2] - pts[0])
                    if nrm.dot(Vector((sx_, sy_, sz_))) < 0:
                        tri = tri[::-1]
                    g.face(tri, uvq(tri, 0))
    return g


def cyl(r, h, seg=12, zone=None, cap_zone=None, bevel=0.0, r2=None, center_z=True, caps=(True, True)):
    """Cylinder along +Z. r2 makes it a frustum. Bevel chamfers both rims."""
    r2 = r if r2 is None else r2
    z0 = -h / 2 if center_z else 0
    z1 = z0 + h
    prof = []
    if caps[0]:
        prof.append((0, z0))
    if bevel > 0:
        if caps[0]:
            prof.append((r - bevel, z0))
        prof += [(r, z0 + bevel), (r2, z1 - bevel)]
        if caps[1]:
            prof.append((r2 - bevel, z1))
    else:
        if caps[0]:
            prof.append((r, z0))
        prof += [(r, z0 + 1e-5), (r2, z1 - 1e-5)]
        if caps[1]:
            prof.append((r2, z1))
    if caps[1]:
        prof.append((0, z1))
    return lathe(prof, seg, zone=zone)


def tube(path, r, sides=6, zone=None, caps=True, r_fn=None, closed=False):
    """Sweep a regular polygon along a polyline with parallel-transport frames."""
    pts = [Vector(p) for p in path]
    if len(pts) < 2:
        return Geo()
    g = Geo()
    n = len(pts)
    tang = []
    for i in range(n):
        if closed:
            d = (pts[(i + 1) % n] - pts[i - 1])
        elif i == 0:
            d = pts[1] - pts[0]
        elif i == n - 1:
            d = pts[-1] - pts[-2]
        else:
            d = (pts[i] - pts[i - 1]).normalized() + (pts[i + 1] - pts[i]).normalized()
        tang.append(d.normalized())
    ref = Vector((0, 0, 1)) if abs(tang[0].z) < .9 else Vector((1, 0, 0))
    u = (ref - ref.dot(tang[0]) * tang[0]).normalized()
    length = 0.0
    rows = []
    for i in range(n):
        if i:
            length += (pts[i] - pts[i - 1]).length
            axis = tang[i - 1].cross(tang[i])
            if axis.length > 1e-6:
                u = Matrix.Rotation(tang[i - 1].angle(tang[i]), 3, axis.normalized()) @ u
            u = (u - u.dot(tang[i]) * tang[i]).normalized()
        w = tang[i].cross(u)
        rr = r_fn(i / (n - 1)) if r_fn else r
        row = []
        for k in range(sides):
            a = TAU * k / sides
            row.append(len(g.v))
            g.v.append(tuple(pts[i] + (u * math.cos(a) + w * math.sin(a)) * rr))
        rows.append((row, length))
    nrows = n if closed else n - 1
    for i in range(nrows):
        ra, la = rows[i]
        rb, lb = rows[(i + 1) % n]
        for k in range(sides):
            k2 = (k + 1) % sides
            if zone:
                s0, s1 = k / sides, (k + 1) / sides
                span = zone.span_m()[1] or 1
                t0 = (la / span) % 1
                t1 = t0 + (lb - la) / span
                if t1 > 1:
                    t0, t1 = 0.0, min(1.0, (lb - la) / span)
                uvs = [zone.uv(s0, t0), zone.uv(s1, t0), zone.uv(s1, t1), zone.uv(s0, t1)]
            else:
                uvs = [(0, 0)] * 4
            g.face([ra[k], ra[k2], rb[k2], rb[k]], uvs)
    if caps and not closed:
        for row, rev in ((rows[0][0], True), (rows[-1][0], False)):
            c = len(g.v)
            p0 = sum((Vector(g.v[i]) for i in row), Vector()) / sides
            g.v.append(tuple(p0))
            for k in range(sides):
                k2 = (k + 1) % sides
                tri = [c, row[k2], row[k]] if rev else [c, row[k], row[k2]]
                u0 = zone.uv(.5, .5) if zone else (0, 0)
                g.face(tri, [u0, u0, u0])
    return g


def arc_path(center, r, a0, a1, n=24, z=0):
    """Arc in a plane at height z (azimuths as on_cyl)."""
    out = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        out.append((center[0] + r * math.sin(a), center[1] - r * math.cos(a), z))
    return out


def curved_panel(r, a0, a1, z0, z1, raise_=0.01, chamfer=0.006, seg=6, uv_fn=None, thickness=0.0):
    """Panel lying on a cylinder of radius r, raised by raise_, with a chamfered rim.
    uv_fn(az, z) -> (u,v). Used for MMOD bumpers, radiators, access panels."""
    g = Geo()
    r_o = r + raise_
    # inner rectangle grid plus outer skirt ring
    da = math.degrees(chamfer / r_o)
    azs = [a0 + da + (a1 - a0 - 2 * da) * i / seg for i in range(seg + 1)]

    def P(az, z, rr):
        a = math.radians(az)
        return (rr * math.sin(a), -rr * math.cos(a), z)
    top = {}
    for i, az in enumerate(azs):
        for j, z in enumerate((z0 + chamfer, z1 - chamfer)):
            top[(i, j)] = len(g.v); g.v.append(P(az, z, r_o))
    uv_ = uv_fn or (lambda a, z: (0, 0))
    for i in range(seg):
        q = [top[(i, 0)], top[(i + 1, 0)], top[(i + 1, 1)], top[(i, 1)]]
        g.face(q, [uv_(azs[i], z0 + chamfer), uv_(azs[i + 1], z0 + chamfer), uv_(azs[i + 1], z1 - chamfer), uv_(azs[i], z1 - chamfer)])
    # skirt: bottom, top, sides (down to base radius r)
    base_azs = [a0 + (a1 - a0) * i / seg for i in range(seg + 1)]
    bot = {}
    for i, az in enumerate(base_azs):
        for j, z in enumerate((z0, z1)):
            bot[(i, j)] = len(g.v); g.v.append(P(az, z, r))
    for i in range(seg):
        # bottom skirt
        q = [bot[(i, 0)], bot[(i + 1, 0)], top[(i + 1, 0)], top[(i, 0)]]
        g.face(q, [uv_(base_azs[i], z0), uv_(base_azs[i + 1], z0), uv_(azs[i + 1], z0 + chamfer), uv_(azs[i], z0 + chamfer)])
        q = [top[(i, 1)], top[(i + 1, 1)], bot[(i + 1, 1)], bot[(i, 1)]]
        g.face(q, [uv_(azs[i], z1 - chamfer), uv_(azs[i + 1], z1 - chamfer), uv_(base_azs[i + 1], z1), uv_(base_azs[i], z1)])
    # left / right skirts
    q = [bot[(0, 1)], bot[(0, 0)], top[(0, 0)], top[(0, 1)]]
    g.face(q, [uv_(base_azs[0], z1), uv_(base_azs[0], z0), uv_(azs[0], z0 + chamfer), uv_(azs[0], z1 - chamfer)])
    q = [top[(seg, 1)], top[(seg, 0)], bot[(seg, 0)], bot[(seg, 1)]]
    g.face(q, [uv_(azs[seg], z1 - chamfer), uv_(azs[seg], z0 + chamfer), uv_(base_azs[seg], z0), uv_(base_azs[seg], z1)])
    return g


def rounded_rect_ring(w, h, rad, thick, height, seg=4, zone=None, base=0.0):
    """Raised rounded-rectangle frame in the local XY plane, facing +Z. Bezels, hatch rims."""
    def outline(ww, hh, rr):
        pts = []
        for cx, cy, a0 in ((ww / 2 - rr, hh / 2 - rr, 0), (-ww / 2 + rr, hh / 2 - rr, 90), (-ww / 2 + rr, -hh / 2 + rr, 180), (ww / 2 - rr, -hh / 2 + rr, 270)):
            for k in range(seg + 1):
                a = math.radians(a0 + 90 * k / seg)
                pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        return pts
    bev = min(thick * .3, height * .4)
    loops = [
        (outline(w, h, rad), base),                                        # outer foot
        (outline(w - bev * 2, h - bev * 2, max(rad - bev, 1e-3)), base + height),       # outer top
        (outline(w - 2 * thick + bev * 2, h - 2 * thick + bev * 2, max(rad - thick + bev, 1e-3)), base + height),  # inner top
        (outline(w - 2 * thick, h - 2 * thick, max(rad - thick, 1e-3)), base),   # inner foot
    ]
    g = Geo()
    m = len(loops[0][0])
    for pts, z in loops:
        for x, y in pts:
            g.v.append((x, y, z))
    for l in range(3):
        for k in range(m):
            k2 = (k + 1) % m
            a, b, c, d = l * m + k, l * m + k2, (l + 1) * m + k2, (l + 1) * m + k
            if zone:
                s0, s1 = k / m, (k + 1) / m
                t0, t1 = l / 3, (l + 1) / 3
                uv = [zone.uv(s0, t0), zone.uv(s1, t0), zone.uv(s1, t1), zone.uv(s0, t1)]
            else:
                uv = [(0, 0)] * 4
            g.face([a, b, c, d], uv)
    return g


def quad_patch(w, h, zone, z=0.0, nx=1, ny=1, curve_r=None):
    """Flat (or cylinder-following) textured sheet in local XY facing +Z, mapped to the
    whole zone. curve_r wraps it around a cylinder whose axis is local Y at radius curve_r."""
    g = Geo()
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = -w / 2 + w * i / nx; y = -h / 2 + h * j / ny
            zz = z
            if curve_r:
                a = x / curve_r
                zz = z + curve_r * (math.cos(a) - 1)
                x = curve_r * math.sin(a)
            g.v.append((x, y, zz))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            g.face([a, a + 1, a + nx + 2, a + nx + 1],
                   [zone.uv(i / nx, j / ny), zone.uv((i + 1) / nx, j / ny), zone.uv((i + 1) / nx, (j + 1) / ny), zone.uv(i / nx, (j + 1) / ny)])
    return g


def hemisphere_uv_polar(zone):
    """UV function for domes and discs: polar projection into a square zone."""
    def fn(az, r, z, arc, rmax=None):
        return None
    return fn


# ------------------------------------------------------------------ part assembly
class Part:
    def __init__(self, name):
        self.name = name
        self.coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(self.coll)
        self.root = self.empty(name)
        self.model = self.empty('model', parent=self.root)
        self.mats = {}
        self.nodes = {}
        self.clips = {}
        self.meta = {}

    def empty(self, name, frame=None, parent=None):
        o = bpy.data.objects.new(name, None)
        o.empty_display_size = .1
        self.coll.objects.link(o)
        self.place(o, frame or Matrix(), parent)
        return o

    def place(self, o, frame, parent):
        o.parent = parent
        o.matrix_parent_inverse = Matrix()
        pw = parent.matrix_world if parent else Matrix()
        o.matrix_basis = pw.inverted() @ frame
        bpy.context.view_layer.update()

    # ---------------------------------------------------------- materials
    def material(self, tex, shader='KSP/Bumped Specular', nrm=None, spec=(1, 1, 1), shininess=.27, emissive=None, name=None):
        """tex: base name so that <tex>_diff.png / <tex>_nrm.png exist in Parts/ (as DDS)."""
        key = name or (tex + '|' + shader)
        if key in self.mats:
            return self.mats[key]
        m = bpy.data.materials.new('sl_' + key.split('|')[0])
        mp = m.mumatprop
        mp.shaderName = shader
        props = [('_MainTex', f'{tex}_diff.png', False)]
        if 'Bumped' in shader:
            props.append(('_BumpMap', f'{nrm or tex}_nrm.png', True))
        if emissive:
            props.append(('_Emissive', f'{emissive}.png', False))
        for nm, t, isn in props:
            it = mp.texture.properties.add(); it.name = nm; it.tex = t; it.type = isn
            it.scale = (1, 1); it.offset = (0, 0)
        cols = [('_Color', (1, 1, 1, 1)), ('_RimColor', (0, 0, 0, 0)), ('_TemperatureColor', (0, 0, 0, 0)), ('_BurnColor', (1, 1, 1, 1))]
        if 'Specular' in shader:
            cols.append(('_SpecColor', (spec[0], spec[1], spec[2], 1)))
        if emissive:
            cols.append(('_EmissiveColor', (0, 0, 0, 1)))
        for nm, v in cols:
            it = mp.color.properties.add(); it.name = nm; it.value = v
        flts = [('_Opacity', 1.0), ('_RimFalloff', .1)]
        if 'Specular' in shader:
            flts.append(('_Shininess', shininess))
        for nm, v in flts:
            it = mp.float3.properties.add(); it.name = nm; it.value = v
        self.mats[key] = m
        return m

    def mesh(self, name, geo, material, parent=None, frame=None, smooth_angle=38):
        """Add a Geo as a mesh object. Geo is in part space; frame relocates the origin."""
        fr = frame or Matrix()
        g = geo
        if frame is not None:
            g = Geo(); g.add(geo, frame.inverted())
        me = g.to_mesh(name, smooth_angle)
        me.materials.append(material)
        o = bpy.data.objects.new(name, me)
        self.coll.objects.link(o)
        self.place(o, fr, parent or self.model)
        self.meta.setdefault('tris', {})[name] = g.tris()
        return o

    # ---------------------------------------------------------- colliders / triggers
    def hull_collider(self, name, points, parent=None, frame=None):
        """Convex mesh collider. KSP's PhysX cooking caps convex hulls at 255 tris; the
        callers pass small point sets so the hull stays well below that."""
        bm = bmesh.new()
        fr = frame or Matrix()
        inv = fr.inverted()
        for p in points:
            bm.verts.new(inv @ Vector(p))
        bmesh.ops.convex_hull(bm, input=bm.verts)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        assert len(me.polygons) <= 255, f'{name}: collider has {len(me.polygons)} tris'
        o = bpy.data.objects.new(name, me)
        self.coll.objects.link(o)
        self.place(o, fr, parent or self.model)
        o.muproperties.collider = 'MU_COL_MESH'
        o.muproperties.isConvex = True
        o.hide_render = True
        return o

    def box_trigger(self, name, frame, size, tag, parent=None):
        """Trigger box: tag 'Airlock' (EVA exit) or 'Ladder' (EVA climb). frame comes from climb_frame or climb_on_cyl;
        size is (across, off the wall, up the climb). Layer 21 is where stock keeps these triggers."""
        o = self.empty(name, frame, parent or self.model)
        mp = o.muproperties
        mp.collider = 'MU_COL_BOX'; mp.isTrigger = True; mp.tag = tag; mp.layer = 21
        mp.size = size; mp.center = (0, 0, 0)
        return o

    def node(self, name, pos, direction, size):
        self.nodes[name] = (Vector(pos), Vector(direction).normalized(), size)

    # ---------------------------------------------------------- animation
    def key(self, clip, obj, frame, **props):
        self.clips.setdefault(clip, {}).setdefault(obj.name, []).append((frame, props))

    def bake_clips(self, rest_frame=0):
        for clip, objs in self.clips.items():
            for oname, keys in objs.items():
                o = bpy.data.objects[oname]
                o.rotation_mode = 'QUATERNION'
                if not o.animation_data:
                    o.animation_data_create()
                act = bpy.data.actions.new(f'{clip}.{oname}')
                o.animation_data.action = act
                for frame, props in sorted(keys, key=lambda k: k[0]):
                    for prop, val in props.items():
                        setattr(o, prop, val)
                        o.keyframe_insert(prop, frame=frame)
                for fc in act.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'BEZIER'
                        kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
                    fc.update()
                o.animation_data.action = None
                tr = o.animation_data.nla_tracks.new()
                tr.name = clip
                tr.strips.new(clip, int(act.frame_range[0]), act)
        sc = bpy.context.scene
        sc.render.fps = FPS
        sc.frame_start = 0
        sc.frame_set(rest_frame)

    def rest_quat(self, o):
        o.rotation_mode = 'QUATERNION'
        return o.rotation_quaternion.copy()

    # ---------------------------------------------------------- export
    def pose_frames(self):
        """Frames to judge visibility in: stowed, plus the end of each clip."""
        ends = set()
        for o in self.coll.objects:
            ad = o.animation_data
            if ad:
                for tr in ad.nla_tracks:
                    for s in tr.strips:
                        ends.add(int(s.frame_end))
        return [0] + sorted(ends)

    def export(self, out_dir):
        from io_object_mu.export_mu.export import export_object
        os.makedirs(out_dir, exist_ok=True)
        if 'IVA' not in self.name:    # interiors face inward on purpose
            from facing import fix_facing
            fix_facing(list(self.coll.objects), self.pose_frames(), variants=getattr(self, 'variants', ()))
        # The exporter folds a lone collider into its parent and drops the transform, unless it is
        # marked separate. Configs look colliders up by name, so every collider keeps its own.
        for o in self.coll.objects:
            if o.muproperties.collider != 'MU_COL_NONE':
                o.muproperties.separate = True
        path = os.path.join(out_dir, self.name + '.mu')
        mu = export_object(self.root, path)
        for m in getattr(mu, 'messages', []):
            print('EXPORT MSG', m)
        total = sum(self.meta.get('tris', {}).values())
        names = [o.name.split('.')[0] for o in self.coll.objects]
        data = dict(name=self.name,
                    nodes={k: dict(pos=[v[0].x, v[0].z, v[0].y], dir=[v[1].x, v[1].z, v[1].y], size=v[2]) for k, v in self.nodes.items()},
                    tris=total, transforms=sorted(set(names)), clips=sorted(self.clips))
        with open(os.path.join(out_dir, self.name + '.json'), 'w') as f:
            json.dump(data, f, indent=1)
        print(f'EXPORT {self.name}: {total} tris, {len(self.coll.objects)} objects, clips={sorted(self.clips)}')
        return path

    def save_blend(self, out_dir):
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, self.name + '.blend'))


def clean_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def add_spot(part, name, origin, beam_dir, parent=None, power=320, angle=70, color=(1, .96, .86), reach=14):
    """Real Unity spotlight for ModuleLight. Name repeats are fine: the exporter strips .001, so
    one lightName drives them all. Blender spots shine along local -Z (the exporter converts)."""
    d = bpy.data.lights.new(name, 'SPOT')
    d.energy = power; d.color = color; d.spot_size = math.radians(angle); d.spot_blend = .35
    d.use_custom_distance = True; d.cutoff_distance = reach
    o = bpy.data.objects.new(name, d)
    part.coll.objects.link(o)
    part.place(o, frame_axes(origin, z=-Vector(beam_dir).normalized()), parent or part.model)
    return o
