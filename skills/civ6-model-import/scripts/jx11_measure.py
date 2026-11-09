import json
import numpy as np
from PIL import Image

D = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame11"
A = D + "/01_scale09.png"
B = D + "/02_plate.png"

a = np.asarray(Image.open(A).convert("RGB")).astype(np.int32)
b = np.asarray(Image.open(B).convert("RGB")).astype(np.int32)
d = np.abs(a - b).sum(axis=2)
m = d > 64
ys, xs = np.nonzero(m)
print("MASK px", int(m.sum()), "bbox", int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
print("HEIGHT", int(ys.max()) - int(ys.min()) + 1, "WIDTH", int(xs.max()) - int(xs.min()) + 1)

r = a[:, :, 0]
g = a[:, :, 1]
bl = a[:, :, 2]
hair = (r - bl <= 12) & (r >= 150)
rows = (hair & m).sum(axis=1)
peak = int(rows.max())
thr = peak * 0.2
first = None
for y in range(0, a.shape[0]):
    if rows[y] >= thr:
        first = y
        break
print("HAIR peak", peak, "thr", round(thr, 2), "first_row", first)

lum = (a[:, :, 0] * 299 + a[:, :, 1] * 587 + a[:, :, 2] * 114) // 1000
face = m.copy()
face[:440, :] = False
face[700:, :] = False
face[:, :1150] = False
face[:, 1450:] = False
if face.sum() > 0:
    v = lum[face]
    print("FACE px", int(face.sum()), "mean", round(float(v.mean()), 2),
          "dark40", round(float((v < 40).mean()), 4), "dark120", round(float((v < 120).mean()), 4))
print("MEASURE_DONE")
