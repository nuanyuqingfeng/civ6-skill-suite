import numpy as np
from PIL import Image
from scipy import ndimage

IMG = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame12/01_bangs_new.png"
PLATE = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame12/02_plate.png"

a = np.asarray(Image.open(IMG).convert("RGB")).astype(np.int32)
b = np.asarray(Image.open(PLATE).convert("RGB")).astype(np.int32)
m = (np.abs(a - b).sum(axis=2) > 64)
ys, xs = np.nonzero(m)
y0, y1 = int(ys.min()), int(ys.max())
x0, x1 = int(xs.min()), int(xs.max())
print("MASK", int(m.sum()), "BBOX", x0, y0, x1, y1)

r = a[:, :, 0]; g = a[:, :, 1]; bl = a[:, :, 2]
lum = (r * 299 + g * 587 + bl * 114) // 1000

# 头心列 285..315 沿用 ingame9 口径，但本轮模型横向位置不同，取掩膜上部中心
cx = (x0 + x1) // 2
cols = range(cx - 15, cx + 16)
hair = (r - bl <= 12) & (lum >= 150) & m
rows = hair[:, list(cols)].sum(axis=1)
peak = int(rows.max())
thr = peak * 0.2
print("HAIR_PEAK", peak, "THR", thr)
first = None
for y in range(y0, y1 + 1):
    if rows[y] < thr and first is None and y > y0 + 40:
        first = y
        break
print("BANGS_LOWER_ROW", first, "CX", cx)
seq = [(y, int(rows[y])) for y in range(y0, min(y1, y0 + 400), 4)]
print("SEQ", seq)
print("IMG_DONE")
