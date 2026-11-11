"""Part-list tab icons for Community Category Kit: a lander-and-habitat silhouette, white and dark.
usage: python3 -I scripts/make_icon.py <out dir>"""
import os, sys
from PIL import Image, ImageDraw
out = sys.argv[1]
S = 8           # draw large, then shrink for clean edges
N = 32


def icon(rgb):
    im = Image.new('RGBA', (N * S, N * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = rgb + (255,)
    d.rounded_rectangle([12 * S, 4 * S, 20 * S, 19 * S], radius=3 * S, fill=c)      # habitat
    d.rectangle([6 * S, 19 * S, 26 * S, 23 * S], fill=c)                            # deck
    d.rectangle([2 * S, 23 * S, 30 * S, 25 * S], fill=c)                            # stowed HIAD
    for x0, x1 in ((7, 3), (25, 29)):                                               # legs
        d.line([x0 * S, 25 * S, x1 * S, 30 * S], fill=c, width=int(1.6 * S))
    return im.resize((N, N), Image.LANCZOS)


icon((255, 255, 255)).save(os.path.join(out, 'shab_icon_inverse.png'))
icon((30, 30, 30)).save(os.path.join(out, 'shab_icon.png'))
