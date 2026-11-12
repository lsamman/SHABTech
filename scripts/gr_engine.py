"""Methalox engine family on the shab_engine sheet: a compact Raptor / BE-4-style engine.

engine(p) builds one engine in its own frame: origin at the gimbal pivot, -Z toward the exit, +X toward
the turbopump side. It returns (moving, static, joints):
  moving  Geo on shab_engine: gimballed section (gimbal block, powerhead, chamber, nozzle, ducts)
  static  Geo on shab_details: thrust cone, upper gimbal clevis, TVC actuators, feed flanges
  joints  {'lox', 'fuel'}: points where the vehicle's static feed lines meet the engine's flex joints
Every height and radius comes from the parameter dict, so the lander engine and the SM's smaller sibling
share one design. s scales the powerhead, ducts and frame; the levels place the chamber and nozzle.
"""
import math
from sl import *
from greebles import Z
import engine_layout as EL

E = {k: Zone(*v, atlas=EL.ATLAS, ppm=400) for k, v in EL.ENG.items()}

# Lander descent engine: exit radius .28, pivot to exit .82, deck underside .13 above the pivot.
LANDER = dict(s=1.0, deck=.13, plate=.03, split=0.0, cone_r=.16,
              z_dome=-.045, z_flange=-.115, z_ch1=-.19, z_th=-.275, z_man=-.345, z_exit=-.82,
              r_ch=.082, r_th=.052, r_exit=.262, wall=.012, ring=.286,
              bands=(.42,), seg_bell=28, seg_in=20, seg=16, seg_s=8)
# SM main engine: the same design at 0.4 for the powerhead, a shorter nozzle to fit the aft bay. Pivot at the
# old engine's gimbal, aft bulkhead .105 above it, exit plane .148 below it.
SM = dict(s=.40, deck=.105, plate=.078, split=.058, cone_r=.17,
          z_dome=.040, z_flange=.016, z_ch1=-.004, z_th=-.034, z_man=-.050, z_exit=-.148,
          r_ch=.034, r_th=.024, r_exit=.100, wall=.005, ring=.111,
          bands=(.45,), seg_bell=24, seg_in=16, seg=12, seg_s=8)


def lerp(a, b, t):
    return a + (b - a) * t


def contour(p):
    """Inner wall of the divergent nozzle as (r, z) from the throat to the exit: cubic Bezier, vertical at the
    throat, th_e degrees at the exit, pulled toward the th_n line from the throat."""
    r0, z0, r1, z1 = p['r_th'], p['z_th'], p['r_exit'], p['z_exit']
    a, b = math.tan(math.radians(p.get('th_n', 38))), math.tan(math.radians(p.get('th_e', 5)))
    # corner where the initial expansion line meets the exit tangent
    zc = (r1 - r0 + b * z1 - a * z0) / (b - a)
    rc = r0 + a * (z0 - zc)
    P = [(r0, z0), (r0, z0 - (z0 - zc) * .35), (rc, zc), (r1, z1)]

    def at(t):
        u = 1 - t
        return (u ** 3 * P[0][0] + 3 * u * u * t * P[1][0] + 3 * u * t * t * P[2][0] + t ** 3 * P[3][0],
                u ** 3 * P[0][1] + 3 * u * u * t * P[1][1] + 3 * u * t * t * P[2][1] + t ** 3 * P[3][1])
    # dense table for r(z) lookups
    tab = [at(i / 400) for i in range(401)]
    return at, tab


def r_at(tab, z):
    """Inner radius of the divergent nozzle at height z (z between the throat and the exit)."""
    for (ra, za), (rb, zb) in zip(tab, tab[1:]):
        if zb <= z <= za:
            return lerp(ra, rb, (za - z) / (za - zb or 1))
    return tab[-1][0] if z < tab[-1][1] else tab[0][0]


def r_conv(p, z):
    """Inner radius of the chamber and convergent section at height z (above the throat)."""
    if z >= p['z_ch1']:
        return p['r_ch']
    u = (z - p['z_th']) / (p['z_ch1'] - p['z_th'])
    return p['r_th'] + (p['r_ch'] - p['r_th']) * (1 - math.cos(math.pi * u)) / 2


def copper_uv(p):
    """Copper zone mapped by height: t = 0 at the manifold, T_THROAT at the throat, 1 at the injector flange."""
    def fn(az, r, z, arc):
        s = ((az % 360) / 360.0) if az < 359.999 else 1.0
        if z <= p['z_th']:
            t = EL.T_THROAT * (z - p['z_man']) / (p['z_th'] - p['z_man'])
        else:
            t = EL.T_THROAT + (1 - EL.T_THROAT) * (z - p['z_th']) / (p['z_flange'] - p['z_th'])
        return E['chamber'].uv(s, min(max(t, 0), 1))
    return fn


def chamfer(path, k=.3):
    """Cut every interior corner of a polyline: each corner becomes two points k of the way along its legs."""
    out = [path[0]]
    for i in range(1, len(path) - 1):
        out += [path[i].lerp(path[i - 1], k), path[i].lerp(path[i + 1], k)]
    return out + [path[-1]]


def flex_duct(path, r, sides, zone, s=1.0):
    """Duct with a flex joint on its first leg (path[0] -> path[1]), then softened corners to the end."""
    g = Geo()
    g.add(tube(path[:2], r * 1.15, sides, zone=E['bellows'], caps=False))
    lead = path[1] + (path[1] - path[0]).normalized() * .02 * s
    g.add(tube([path[1]] + chamfer([lead] + path[2:]), r, sides, zone=zone, caps=False))
    return g


def _collar(at, axis, r, h, seg, zone):
    g = lathe([(r, -h / 2), (r, h / 2)], seg, zone=zone)
    return Geo().add(g, frame_axes(at, axis))


def engine(p=LANDER):
    s = p['s']
    mv, st = Geo(), Geo()
    at, tab = contour(p)
    w = p['wall']
    zt, zm, ze, zf = p['z_th'], p['z_man'], p['z_exit'], p['z_flange']
    SB, SI, SG, SS = p['seg_bell'], p['seg_in'], p['seg'], p['seg_s']

    # ---------------------------------------------------------------- nozzle
    # dark regen section: manifold down to the exit ring, profile runs upward so faces point out
    z_ring = ze + .034 * s ** .5
    n = 7
    prof = []
    for i in range(n + 1):
        u = i / n
        z = lerp(z_ring, zm, 1 - (1 - u) ** 1.7)
        prof.append((r_at(tab, z) + w, z))
    mv.add(lathe(prof, SB, zone=E['bell']))
    # exit stiffener ring and lip: from the inner edge out along the exit plane, up the ring, back onto the wall
    ro = r_at(tab, z_ring) + w
    ring = p['ring']
    mv.add(lathe([(p['r_exit'], ze), (ring, ze), (ring, z_ring), (ro, z_ring + .003 * s)], SB, zone=E['band']))
    # hat-band stiffeners
    for f in p['bands']:
        zb = lerp(zm, ze, f)
        hb = .012 * s ** .5
        r_lo, r_hi = r_at(tab, zb - hb) + w, r_at(tab, zb + hb) + w
        mv.add(lathe([(r_lo - .001, zb - hb), ((r_lo + r_hi) / 2 + .011 * s ** .5, zb), (r_hi - .001, zb + hb)], SB, zone=E['band']))
    # inside: exit up to the throat, closed just above it. Its exit ring hides behind the lip.
    pin = [(p['r_exit'] + .006 * s, ze + .002 * s)]
    for i in range(1, 6):
        u = i / 5
        z = lerp(ze, zt, u ** .75)
        pin.append((r_at(tab, z), z))
    pin += [(0, zt + .01 * s)]

    def in_uv(az, r, z, arc):
        sv = ((az % 360) / 360.0) if az < 359.999 else 1.0
        return E['bell_in'].uv(sv, min(max((z - ze) / (zt - ze), 0), 1))
    mv.add(lathe(pin, SI, uv_fn=in_uv, flip=True))
    # regen inlet manifold: a torus round the nozzle just below the throat
    rm = r_at(tab, zm) + w
    hm, dm = .022 * s, .024 * s
    mv.add(lathe([(rm - .002, zm - hm), (rm + dm * .7, zm - hm * .8), (rm + dm, zm), (rm + dm * .7, zm + hm * .8), (rm - .002, zm + hm)], SG, zone=E['duct']))

    # ---------------------------------------------------------------- copper chamber and throat
    cp = []
    zs = [zm + .002, lerp(zm, zt, .5), zt]
    zs += [lerp(zt, p['z_ch1'], u) for u in (.35, .7, 1.0)]
    zs += [zf - .014 * s]
    for z in zs:
        r = (r_at(tab, z) if z < zt else r_conv(p, z)) + w
        cp.append((r, z))
    mv.add(lathe(cp, SG, uv_fn=copper_uv(p)))
    # ---------------------------------------------------------------- injector flange and dome
    rf = p['r_ch'] + w + .016 * s
    mv.add(lathe([(p['r_ch'] + w - .001, zf - .014 * s), (rf, zf - .014 * s), (rf, zf), (rf - .004 * s, zf + .004 * s)], SG, zone=E['flange']))
    zd = p['z_dome']
    dome = [(rf - .004 * s, zf + .004 * s)]
    for i in range(1, 4):
        a = math.pi / 2 * i / 3
        dome.append((lerp(.045 * s, rf - .01 * s, math.cos(a)), zf + .004 * s + (zd - zf) * math.sin(a)))
    mv.add(lathe(dome, SG, zone=E['steel']))
    # lower gimbal block and its trunnion
    sp = p['split']
    mv.add(box(.07 * s, .07 * s, sp - zd + .002, zone=E['dark'], bevel=.004 * s, center=(0, 0, (zd + sp) / 2 - .002)))
    mv.add(cyl(.016 * s, .10 * s, 6, zone=E['steel']), T(0, 0, sp) @ Rx(90))
    # actuator lugs on the flange
    for a in (45, -45):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        mv.add(box(.022 * s, .03 * s, .03 * s, zone=E['dark'], center=(0, 0, 0)), T(ca * (rf + .010 * s), sa * (rf + .010 * s), zf + .005 * s) @ Rz(a))

    # ---------------------------------------------------------------- turbopump with its preburner
    px = .175 * s
    rp = .052 * s
    z_in = p['z_ch1'] - .03 * s          # inlet housing bottom
    z_vo = zf - .025 * s                 # volute
    z_tu = zd - .02 * s                  # turbine
    pump = [(0, z_in - .012 * s), (.030 * s, z_in - .012 * s), (.030 * s, z_in), (.032 * s, z_vo - .035 * s),
            (rp, z_vo - .012 * s), (rp, z_vo + .010 * s), (.034 * s, z_vo + .024 * s)]
    mv.add(lathe(pump, SS, zone=E['steel']), T(px, 0, 0))
    turb = [(.034 * s, z_vo + .024 * s), (.034 * s, z_tu - .014 * s), (.046 * s, z_tu - .010 * s), (.046 * s, z_tu + .014 * s),
            (.028 * s, z_tu + .05 * s), (0, z_tu + .064 * s)]
    mv.add(lathe(turb, SS, zone=E['tint']), T(px, 0, 0))
    # hot-gas duct: turbine exhaust into the injector dome
    zhg = z_tu - .002 * s
    hg0, hg1 = Vector((px - .03 * s, 0, zhg)), Vector((.05 * s, 0, zhg - .012 * s))
    mv.add(tube([hg0, hg1], .024 * s, 8, zone=E['tint'], caps=False))
    mv.add(_collar(hg0.lerp(hg1, .45), hg1 - hg0, .029 * s, .010 * s, 8, E['flange']))
    # pump discharge into the dome on the -Y side
    dis = [Vector((px, -.045 * s, z_vo)), Vector((px - .02 * s, -.085 * s, z_vo + .006 * s)), Vector((.07 * s, -.095 * s, zf + .03 * s)),
           Vector((.03 * s, -.06 * s, zd - .025 * s))]
    mv.add(tube(dis, .015 * s, 6, zone=E['duct'], caps=False))
    # feed ducts: flex joints at the gimbal plane, LOX round the chamber into the pump inlet, CH4 down to the manifold
    jl, jf = Vector((-.085 * s, .085 * s, sp - .002)), Vector((-.085 * s, -.085 * s, sp - .002))
    rd = .019 * s
    lox = [jl, jl + Vector((0, 0, -.035 * s)), Vector((-.07 * s, .125 * s, zf + .01 * s)), Vector((.03 * s, .14 * s, p['z_ch1'] + .02 * s)),
           Vector((px - .02 * s, .075 * s, z_in + .015 * s)), Vector((px, .02 * s, z_in + .015 * s))]
    mv.add(flex_duct(lox, rd, 6, E['duct'], s))
    fuel = [jf, jf + Vector((0, 0, -.035 * s)), Vector((-.115 * s, -.115 * s, zf - .01 * s)), Vector((-.115 * s, -.115 * s, zt + .01 * s)),
            Vector((-(rm + dm * .5) * .707, -(rm + dm * .5) * .707, zm + hm * .7))]
    mv.add(flex_duct(fuel, rd, 6, E['duct'], s))
    # main valves on both feeds
    for path, k in ((lox, 2), (fuel, 2)):
        q = path[k]
        d = (path[k + 1] - path[k - 1]).normalized()
        mv.add(box(.05 * s, .045 * s, .045 * s, zone=E['dark']), frame_axes(q, d))

    # ---------------------------------------------------------------- static: thrust cone, clevis, actuators
    st.add(lathe([(.05 * s, p['plate']), (p['cone_r'], p['deck'] - .012 * s), (p['cone_r'] + .025 * s, p['deck'] - .012 * s),
                  (p['cone_r'] + .025 * s, p['deck'] + .002)], 16, zone=Z.dark))
    st.add(box(.08 * s, .05 * s, p['plate'] - sp + .004, zone=Z.grey, center=(0, 0, (p['plate'] + sp) / 2 - .002)))
    for sy_ in (-1, 1):
        st.add(box(.06 * s, .012 * s, .05 * s, zone=Z.dark, center=(0, sy_ * .056 * s, sp + .004)))
    for a in (45, -45):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        top = Vector((ca * (p['cone_r'] + .005 * s), sa * (p['cone_r'] + .005 * s), p['deck'] - .03 * s))
        bot = Vector((ca * (rf + .010 * s), sa * (rf + .010 * s), zf + .005 * s))
        st.add(box(.04 * s, .03 * s, .02 * s, zone=Z.grey, center=(0, 0, 0)), T(*(top + Vector((0, 0, .012 * s)))) @ Rz(a))
        m = top.lerp(bot, .58)
        st.add(tube([top, m], .019 * s, 6, zone=Z.white))
        st.add(tube([m, bot], .010 * s, 6, zone=Z.steel, caps=False))
    for j in (jl, jf):
        st.add(lathe([(rd * 1.1, j.z), (rd * 1.5, j.z), (rd * 1.5, j.z + .014 * s)], 8, zone=Z.steel), T(j.x, j.y, 0))
    return mv, st, {'lox': jl, 'fuel': jf}
