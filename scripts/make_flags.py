"""SHABTech flag and agency logo. Drawn with Pillow; written as PNG for KSP's flag loader."""
import os, math, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
F = '/usr/share/fonts/TTF/DejaVuSansCondensed-Bold.ttf'
for p in (F, '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf', '/usr/share/fonts/noto/NotoSans-Bold.ttf', '/usr/share/fonts/liberation/LiberationSans-Bold.ttf'):
    if os.path.exists(p):
        F = p; break
W, H = 256 * 4, 160 * 4
im = Image.new('RGB', (W, H), (10, 14, 28))
d = ImageDraw.Draw(im)
# stars
import random
random.seed(7)
for _ in range(240):
    x, y = random.randrange(W), random.randrange(H)
    v = random.randrange(90, 255); r = random.choice((1, 1, 2))
    d.ellipse((x - r, y - r, x + r, y + r), fill=(v, v, v))
# Mars limb
cx, cy, R = W * .5, H * 1.62, H * 1.18
for k in range(90):
    t = k / 89
    rr = R * (1 - t * .0)
    col = (int(196 - 70 * t), int(92 - 50 * t), int(48 - 26 * t))
    d.ellipse((cx - rr + k * 4, cy - rr + k * 6, cx + rr - k * 4, cy + rr - k * 2), fill=col)
# SHAB silhouette: PCM, deck, HIAD arc
col = (236, 236, 228)
bx = W * .5
d.rounded_rectangle((bx - 66, H * .26, bx + 66, H * .60), 14, fill=col)
d.polygon([(bx - 66, H * .27), (bx - 40, H * .18), (bx + 40, H * .18), (bx + 66, H * .27)], fill=col)
d.rectangle((bx - 40, H * .15, bx + 40, H * .18), fill=(170, 170, 172))
for y_ in (.35, .43, .51):
    d.line((bx - 66, H * y_, bx + 66, H * y_), fill=(150, 150, 150), width=3)
d.rectangle((bx - 20, H * .47, bx + 20, H * .58), fill=(70, 74, 86))
d.rounded_rectangle((bx + 26, H * .32, bx + 50, H * .40), 4, fill=(24, 40, 70))
d.rectangle((bx - 150, H * .60, bx + 150, H * .66), fill=(200, 200, 196))
d.polygon([(bx - 120, H * .66), (bx - 150, H * .75), (bx - 118, H * .75)], fill=(160, 160, 160))
d.polygon([(bx + 120, H * .66), (bx + 150, H * .75), (bx + 118, H * .75)], fill=(160, 160, 160))
for s in range(-3, 4):
    if s:
        d.polygon([(bx + s * 32 - 10, H * .66), (bx + s * 32 + 10, H * .66), (bx + s * 32 + 14, H * .72), (bx + s * 32 - 14, H * .72)], fill=(70, 70, 76))
f1 = ImageFont.truetype(F, 74)
d.text((W * .04, H * .04), 'SHAB', font=f1, fill=(240, 240, 232))
f2 = ImageFont.truetype(F, 30)
d.text((W * .04, H * .17), 'ONE WAY, WELL FURNISHED', font=f2, fill=(216, 150, 90))
im = im.resize((256, 160), Image.LANCZOS)
im.save(os.path.join(out, 'SHABTech.png'))
im.resize((128, 80), Image.LANCZOS).save(os.path.join(out, 'SHABTech_scaled.png'))
