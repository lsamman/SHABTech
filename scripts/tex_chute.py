"""Canopy sheet: white gores with orange bands; u is azimuth, v runs from the skirt to the apex."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from tl import *

c = Canvas(512, 512, albedo=(.90, .89, .86), gloss=.1)
for g in range(8):
    for b in range(5):
        if (g + b) % 2 == 0:
            c.albedo[b * 102:(b + 1) * 102, g * 64:(g + 1) * 64] = (.80, .30, .08)
for g in range(1, 8):
    c.albedo[:, g * 64 - 1:g * 64 + 1] *= .8
c.ao[:] = 1
c.save('shab_chute', nstrength=1.0)
