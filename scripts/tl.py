"""SHABTech texture library: procedural PBR-ish maps painted with numpy.

The KSP shader reads RGB = diffuse, A = gloss. Normal maps are DXT5nm (R=1, G=Y, B=Y, A=X).
Every map is authored top-left origin, as viewed. to_dds() flips V for KSP's DDS loader.

Workflow for a sheet:
    c = Canvas(2048, 2048)
    c.albedo[...]   float RGB 0..1 (display-referred)
    c.gloss[...]    float 0..1
    c.height[...]   float, in millimetres of relief at the sheet's px/m
    c.save('name', mm_per_px=...)   writes name_diff.dds + name_nrm.dds + _png previews
"""
import os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
OUT = os.environ.get('SHAB_TEX', os.path.join(os.path.dirname(__file__), '..', 'build', 'tex'))
PNG = os.path.join(OUT, '_png')
FONT_BOLD = None
for p in ('/usr/share/fonts/TTF/DejaVuSansCondensed-Bold.ttf', '/usr/share/fonts/dejavu/DejaVuSansCondensed-Bold.ttf',
          '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf', '/usr/share/fonts/liberation/LiberationSans-Bold.ttf',
          '/usr/share/fonts/noto/NotoSans-Bold.ttf'):
    if os.path.exists(p):
        FONT_BOLD = p; break


# House style follows HabTech2 and Benjee10's Orion: brand-new, flat colour, crisp lines. Measured on their
# sheets, about 85% of the normal map is perfectly flat, and relief exists only on real features. So the
# noise sources below stay in place for the painters to call but contribute nothing while CLEAN is on.
# Their surface variation lives in the gloss channel instead, which is what gloss_grunge() is for.
CLEAN = True


def rng(seed):
    return np.random.default_rng(seed)


# ------------------------------------------------------------------ filters
def blur(a, sigma, wrap=True):
    """Gaussian blur via FFT (periodic). sigma in pixels."""
    if sigma <= 0:
        return a
    h, w = a.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy))
    if a.ndim == 2:
        return np.fft.irfft2(np.fft.rfft2(a) * g, s=a.shape).astype(np.float32)
    return np.dstack([np.fft.irfft2(np.fft.rfft2(a[..., i]) * g, s=a.shape[:2]) for i in range(a.shape[2])]).astype(np.float32)


def fbm(h, w, seed=0, base=4, octaves=6, gain=.5):
    """Tileable fractal noise, about -1..1. base = features across the image at octave 0."""
    if CLEAN:
        return np.zeros((h, w), np.float32)
    return _fbm(h, w, seed, base, octaves, gain)


def _fbm(h, w, seed=0, base=4, octaves=6, gain=.5):
    r = rng(seed)
    fy = np.fft.fftfreq(h)[:, None] * h; fx = np.fft.rfftfreq(w)[None, :] * w
    f = np.sqrt(fx * fx + fy * fy)
    out = np.zeros((h, w), np.float32)
    amp = 1.0
    for o in range(octaves):
        fc = base * 2 ** o
        band = np.exp(-((np.log2(np.maximum(f, 1e-6)) - np.log2(fc)) ** 2) / (2 * .55 ** 2))
        n = np.fft.rfft2(r.standard_normal((h, w)))
        s = np.fft.irfft2(n * band, s=(h, w))
        s /= (s.std() + 1e-9)
        out += (amp * s).astype(np.float32)
        amp *= gain
    return out / (out.std() * 2.5 + 1e-9)


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def grid(h, w):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    return x + .5, y + .5


def sd_rrect(x, y, cx, cy, hw, hh, r=0.0):
    """Signed distance to a rounded rectangle: negative inside (pixels)."""
    qx = np.abs(x - cx) - (hw - r); qy = np.abs(y - cy) - (hh - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def sd_circle(x, y, cx, cy, r):
    return np.hypot(x - cx, y - cy) - r


def fill(sd, aa=.8):
    """Coverage mask from a signed distance."""
    return np.clip(.5 - sd / (2 * aa), 0, 1).astype(np.float32)


def bevel(sd, width):
    """Height profile: 0 outside, ramps to 1 at `width` px inside."""
    return np.clip(-sd / max(width, 1e-3), 0, 1).astype(np.float32)


# ------------------------------------------------------------------ material fields
def crinkle(h, w, seed=0, scale=64, sharp=2.2):
    """Crumpled-foil height: ridged multifractal with crease lines. ~0..1"""
    if CLEAN:
        return np.full((h, w), .55, np.float32)
    n = np.zeros((h, w), np.float32)
    amp = 1.0; tot = 0
    for o, s in enumerate((1, 2, 4, 8)):
        f = fbm(h, w, seed + o * 13, base=max(2, int(max(h, w) / scale * s)), octaves=2, gain=.4)
        n += amp * (1 - np.abs(np.clip(f * 1.6, -1, 1))) ** sharp
        tot += amp; amp *= .55
    return n / tot


def weave(x, y, period=3.0, seed=0):
    """Beta-cloth / woven silica weave height. ~0..1"""
    if CLEAN:
        return np.full(np.shape(x), .5, np.float32)
    a = np.sin(x * np.pi * 2 / period) * .5 + .5
    b = np.sin(y * np.pi * 2 / period) * .5 + .5
    chk = (np.floor(x / period) + np.floor(y / period)) % 2
    return np.where(chk > 0, a, b).astype(np.float32)


def scratches(h, w, seed=0, n=240, length=(10, 90), bright=1.0):
    """Sparse fine scratches and scuffs, 0..1 mask."""
    if CLEAN:
        return np.zeros((h, w), np.float32)
    return _scratches(h, w, seed, n, length, bright)


def _scratches(h, w, seed=0, n=240, length=(10, 90), bright=1.0):
    r = rng(seed)
    im = Image.new('L', (w, h), 0); d = ImageDraw.Draw(im)
    for _ in range(n):
        x0, y0 = r.uniform(0, w), r.uniform(0, h)
        a = r.uniform(0, np.pi * 2); l = r.uniform(*length)
        v = int(r.uniform(.25, 1) * 255 * bright)
        d.line((x0, y0, x0 + np.cos(a) * l, y0 + np.sin(a) * l), fill=v, width=1)
    return blur(np.asarray(im).astype(np.float32) / 255, .5)


def gloss_grunge(h, w, seed=0, base=7):
    """Variation for the gloss channel only: soft clouding, fine speckle, hairline scratches. Colour stays clean,
    so a part looks new in flat light and only breaks up as a highlight crosses it. About -1..1, mean 0."""
    cloud = _fbm(h, w, seed, base=base, octaves=6, gain=.62)
    speck = _fbm(h, w, seed + 1, base=h // 3, octaves=1)
    hair = np.clip(_scratches(h, w, seed + 2, n=int(h * h / 7000), length=(12, 110)), 0, 1)
    g = cloud * .85 + speck * .22 - hair * .9
    return np.clip(g - g.mean(), -1, 1).astype(np.float32)


def grime(h, w, seed=0, base=5):
    """Soft large-scale mottling, 0..1"""
    return np.clip(fbm(h, w, seed, base=base, octaves=5) * .5 + .5, 0, 1)


# ------------------------------------------------------------------ canvas
class Canvas:
    def __init__(self, w, h=None, albedo=(.6, .6, .62), gloss=.3):
        self.w = w; self.h = h or w
        self.albedo = np.ones((self.h, self.w, 3), np.float32) * np.array(albedo, np.float32)
        self.gloss = np.full((self.h, self.w), gloss, np.float32)
        self.height = np.zeros((self.h, self.w), np.float32)     # relief, in px-equivalent units
        self.ao = np.ones((self.h, self.w), np.float32)
        self.x, self.y = grid(self.h, self.w)

    def mask_rect(self, x0, y0, w, h):
        return (slice(int(y0), int(y0 + h)), slice(int(x0), int(x0 + w)))

    def tint(self, mask, rgb, opacity=1.0):
        m = (mask * opacity)[..., None]
        self.albedo[:] = self.albedo * (1 - m) + np.array(rgb, np.float32) * m

    def mul(self, mask, factor):
        m = mask[..., None] if mask.ndim == 2 else mask
        self.albedo[:] = self.albedo * (1 - m + m * factor)

    def add_text(self, text, x, y, size, rgb=(.05, .05, .05), opacity=.9, rotate=0, anchor='lt', tracking=0, relief=0.0):
        """Stencil text. x,y pixels, size pixels."""
        font = ImageFont.truetype(FONT_BOLD, int(size))
        tmp = Image.new('L', (self.w, self.h), 0); d = ImageDraw.Draw(tmp)
        if tracking:
            cx = x
            for ch in text:
                d.text((cx, y), ch, fill=255, font=font, anchor=anchor)
                cx += d.textlength(ch, font=font) + tracking
        else:
            d.text((x, y), text, fill=255, font=font, anchor=anchor)
        if rotate:
            tmp = tmp.rotate(rotate, center=(x, y), resample=Image.BICUBIC)
        m = np.asarray(tmp).astype(np.float32) / 255
        self.tint(m, rgb, opacity)
        if relief:
            self.height += m * relief

    def cavity_from_height(self, strength=1.0, r1=1.5, r2=5.0):
        """Darken creases and lighten crests from the relief."""
        h = self.height
        c = (h - blur(h, r1)) * .6 + (h - blur(h, r2)) * .4
        s = c.std() + 1e-6
        c = np.clip(c / (s * 3), -1, 1)
        shade = 1 + strength * np.where(c < 0, c * .45, c * .30)   # dark in the groove, bright on the edge
        self.albedo *= shade[..., None]

    def apply_ao(self):
        ao = 1 - (1 - self.ao) * .65       # contact shadows stay, but stay soft
        if ao.shape != self.albedo.shape[:2]:       # bake_ao always writes 2048 px; small sheets resample it
            ao = np.asarray(Image.fromarray(ao).resize((self.w, self.h), Image.BILINEAR)).astype(np.float32)
        self.albedo *= ao[..., None]

    def normal(self, strength=1.0):
        """Tangent-space normals from relief. Returns nx, ny (OpenGL Y-up, as painted)."""
        h = self.height
        # periodic central differences; image Y grows downward, tangent Y grows upward
        dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * .5
        dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * .5
        nx = -dx * strength; ny = dy * strength
        l = np.sqrt(nx * nx + ny * ny + 1)
        return nx / l, ny / l

    def save(self, name, nstrength=1.0, cavity=0.0, target_p90=None):
        os.makedirs(PNG, exist_ok=True)
        if cavity:
            self.cavity_from_height(cavity)
        self.apply_ao()
        rgb = np.clip(self.albedo, 0, 1)
        if target_p90:
            rgb = np.clip(rgb * (target_p90 / np.percentile(rgb.mean(-1), 90)), 0, 1)
        diff = np.dstack([rgb, np.clip(self.gloss, 0, 1)])
        write_dds((diff * 255 + .5).astype(np.uint8), f'{name}_diff')
        nx, ny = self.normal(nstrength)
        n = np.empty((self.h, self.w, 4), np.float32)
        n[..., 0] = 1; n[..., 1] = ny * .5 + .5; n[..., 2] = n[..., 1]; n[..., 3] = nx * .5 + .5
        write_dds((n * 255 + .5).astype(np.uint8), f'{name}_nrm')
        nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
        Image.fromarray((np.dstack([nx * .5 + .5, ny * .5 + .5, nz]) * 255).astype(np.uint8)).save(os.path.join(PNG, f'{name}_nrm_view.png'))
        print(f'{name}: p50 {np.percentile(rgb.mean(-1), 50):.2f} p90 {np.percentile(rgb.mean(-1), 90):.2f} gloss {self.gloss.mean():.2f}')


def write_dds(arr, name):
    os.makedirs(PNG, exist_ok=True)
    png = os.path.join(PNG, name + '.png')
    Image.fromarray(arr, 'RGBA').save(png, compress_level=1)
    subprocess.run(['magick', png, '-flip', '-define', 'dds:compression=dxt5', '-define', 'dds:cluster-fit=false',
                    '-define', 'dds:mipmaps=fromlist' if False else 'dds:weight-by-alpha=false',
                    os.path.join(OUT, name + '.dds')], check=True)


def write_emissive(arr, name):
    """RGB emissive map (DXT1-like coverage kept simple as DXT5)."""
    a = np.dstack([arr, np.full(arr.shape[:2], 255, np.uint8)]) if arr.shape[2] == 3 else arr
    write_dds(a, name)


def facet_foil(h, w, seed=0, cells=70):
    """Foil facets, reduced in clean style to a gentle stylised crease. Returns (shade, height, edges)."""
    sh, ht, ed = _facet_foil(h, w, seed, cells)
    if CLEAN:
        return .5 + (sh - .5) * .22, ht * .18, ed * .15
    return sh, ht, ed


def _facet_foil(h, w, seed=0, cells=70):
    """Crumpled metallic foil: Worley facets, each a tilted plane. Returns (shade 0..1, height)."""
    r = rng(seed)
    n = int(cells)
    px = r.uniform(0, w, n * n // 2); py = r.uniform(0, h, n * n // 2)
    tx, ty = r.normal(0, 1, len(px)), r.normal(0, 1, len(px))
    # nearest seed on a coarse bin grid, with wrap
    bs = max(w, h) / n
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    best = np.full((h, w), 1e12, np.float32); idx = np.zeros((h, w), np.int32)
    second = np.full((h, w), 1e12, np.float32)
    for i in range(len(px)):
        x0, x1 = int(px[i] - bs * 3), int(px[i] + bs * 3)
        y0, y1 = int(py[i] - bs * 3), int(py[i] + bs * 3)
        xs = np.arange(x0, x1) % w; ys = np.arange(y0, y1) % h
        gx = np.arange(x0, x1) - px[i]; gy = np.arange(y0, y1) - py[i]
        d = gx[None, :] ** 2 + gy[:, None] ** 2
        ix = np.ix_(ys, xs)
        b = best[ix]; s = second[ix]; id_ = idx[ix]
        closer = d < b
        s = np.where(closer, b, np.minimum(s, d))
        id_ = np.where(closer, i, id_)
        b = np.where(closer, d, b)
        best[ix] = b; second[ix] = s; idx[ix] = id_
    edge = np.sqrt(second) - np.sqrt(best)
    tilt = tx[idx] * .7 + ty[idx] * .3
    shade = np.clip(.5 + tilt * .28, 0, 1).astype(np.float32)
    height = ((x - px[idx]) * tx[idx] + (y - py[idx]) * ty[idx]).astype(np.float32) * .35
    height -= np.exp(-edge / 1.2) * 1.5
    return shade, height, np.exp(-edge / 1.2).astype(np.float32)
