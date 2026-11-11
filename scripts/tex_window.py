"""Small window sheet + lamp emissive."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from tl import *
c = Canvas(512, 512, albedo=(.04, .07, .11), gloss=.95)
X, Y = c.x, c.y
# reflection streaks plus a soft interior rack silhouette
c.albedo += fbm(512, 512, 301, base=3, octaves=3)[..., None] * .01
sd = sd_rrect(X, Y, 256, 256, 240, 240, 50)
c.albedo *= (1 - np.exp(-np.abs(sd) / 10)[..., None] * .6)
c.height += -bevel(sd, 6) * 2
c.save('shab_window', nstrength=1.0)
e = np.zeros((512, 512, 3), np.uint8)
# warm cabin light: racks, a deck rail and a kerbal-sized bright core
glow = np.exp(-((X - 256) ** 2 + (Y - 300) ** 2) / (2 * 170 ** 2))
racks = (np.abs(((X + 256) % 128) - 64) > 8).astype(np.float32)
sky = glow * racks
e[..., 0] = np.clip(sky * 255, 0, 255); e[..., 1] = np.clip(sky * 228, 0, 255); e[..., 2] = np.clip(sky * 170, 0, 255)
write_emissive(e, 'shab_window_emit')
# lamp emissive covers the whole details atlas layout, black except the lamp zone (kept tiny)
from layout import DET
ex = np.zeros((2048, 2048, 3), np.uint8)
x, y, w, h = DET['lamp']
ex[y:y + h, x:x + w] = (255, 245, 210)
write_emissive(ex, 'shab_lamp_emit')
