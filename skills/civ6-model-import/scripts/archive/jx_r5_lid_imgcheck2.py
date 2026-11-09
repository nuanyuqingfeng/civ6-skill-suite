import os

import bpy
import numpy as np

OUT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\reports\r5_vcheck"
W, H = 1200, 600
ORTHO = 10.4
CX, CZ = 0.0, 128.056


def load(name):
    img = bpy.data.images.load(os.path.join(OUT, name), check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(h, w, 4)


a = load("blink_before.png")
b = load("blink_after.png")
d = np.abs(a[:, :, :3] - b[:, :, :3]).mean(axis=2)
mask = d > 0.02
rows, cols = np.nonzero(mask)
def wx(px):
    return round((px + 0.5) / W * ORTHO - ORTHO * 0.5 + CX, 3)
def wz(py):
    return round((py + 0.5) / H * (ORTHO * H / W) - ORTHO * H / W * 0.5 + CZ, 3)
print("DIFF_PX", int(mask.sum()), "world_x", wx(cols.min()), wx(cols.max()),
      "world_z", wz(rows.min()), wz(rows.max()))
print("DIFF_CENTROID_WORLD", wx(float(cols.mean())), wz(float(rows.mean())))
band = np.zeros_like(mask)
for sx in (-2.803, 2.803):
    bx0 = int((sx - 2.2 + ORTHO * 0.5) / ORTHO * W)
    bx1 = int((sx + 2.2 + ORTHO * 0.5) / ORTHO * W)
    bz0 = int((126.3 - (CZ - ORTHO * H / W * 0.5)) / (ORTHO * H / W) * H)
    bz1 = int((128.9 - (CZ - ORTHO * H / W * 0.5)) / (ORTHO * H / W) * H)
    band[max(0, bz0):bz1, max(0, bx0):bx1] = True
print("BAND_SHARE", round(float((mask & band).sum()) / max(1, int(mask.sum())), 4),
      "band_px", int(band.sum()))
for tag, img in (("before", a), ("after", b)):
    lum = img[:, :, :3].mean(axis=2)
    print("LUMA", tag, "band_mean", round(float(lum[band].mean()), 4), "frame_mean", round(float(lum.mean()), 4))
print("IMG2_DONE")
