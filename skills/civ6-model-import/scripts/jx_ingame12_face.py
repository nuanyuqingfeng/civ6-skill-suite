
import json
import numpy as np
from PIL import Image

IMG = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame12/01_bangs_new.png"
PLATE = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame12/02_plate.png"

a = np.asarray(Image.open(IMG).convert("RGB")).astype(np.int32)
b = np.asarray(Image.open(PLATE).convert("RGB")).astype(np.int32)
d = np.abs(a - b).sum(axis=2)
mask = d > 64
ys, xs = np.nonzero(mask)
x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
print("MASK", int(mask.sum()), "BBOX", x0, y0, x1, y1)

# 头部中心列窗口
cx = (x0 + x1) // 2
half = 15
win = mask[:, cx - half:cx + half + 1]
rows = win.sum(axis=1)
nz = [(y, int(rows[y])) for y in range(y0, y1 + 1) if rows[y] > 0]
print("CX", cx, "TOP", y0, "BOTTOM", y1)

# 发色像素：R-B <= 12 且亮度 >= 150
r = a[:, :, 0]; g = a[:, :, 1]; bl = a[:, :, 2]
lum = (r * 299 + g * 587 + bl * 114) // 1000
hair = (r - bl <= 12) & (lum >= 150) & mask
hw = hair[:, cx - half:cx + half + 1]
hr = hw.sum(axis=1)
peak = int(hr[y0:y1 + 1].max())
thr = peak * 0.2
print("HAIR_PEAK", peak, "THR", round(thr, 2))
lower = None
for y in range(y0, y1 + 1):
    if hr[y] < thr:
        lower = y
        break
print("BANGS_LOWER_ROW", lower)
seq = [(y, int(hr[y])) for y in range(lower - 8, lower + 8)]
print("SEQ_AROUND", seq)

# 面部区域：掩膜内、头部中心列附近、下缘以下
fx0, fx1 = cx - 50, cx + 50
fy0, fy1 = lower + 2, lower + 120
sub = mask[fy0:fy1, fx0:fx1]
sub_lum = lum[fy0:fy1, fx0:fx1]
vals = sub_lum[sub]
print("FACE_PX", int(vals.size))
print("FACE_LUM_MEAN", round(float(vals.mean()), 2))
print("FACE_RGB", [round(float(a[fy0:fy1, fx0:fx1, i][sub].mean()), 1) for i in range(3)])
print("DARK40", round(float((vals < 40).mean()), 4))
print("DARK120", round(float((vals < 120).mean()), 4))
print("FACE_DONE")
