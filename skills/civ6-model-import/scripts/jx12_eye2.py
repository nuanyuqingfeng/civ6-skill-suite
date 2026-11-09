import numpy as np
from PIL import Image

ROOT = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame12"
IMG = ROOT + "/01_bangs_new.png"
PLATE = ROOT + "/02_plate.png"

a = np.asarray(Image.open(IMG).convert("RGB")).astype(np.int32)
b = np.asarray(Image.open(PLATE).convert("RGB")).astype(np.int32)
d = np.abs(a - b).sum(axis=2)
mask = d > 64

r, g, bl = a[:, :, 0], a[:, :, 1], a[:, :, 2]
lum = (r * 299 + g * 587 + bl * 114) // 1000

# 眼部：面部窗口内按行统计"暗像素"（眼线/瞳孔），找出眼睛上沿
X0, X1 = 1189, 1389
print("ROW_EYE_SCAN")
for y in range(495, 580, 2):
    band = mask[y, X0:X1]
    if band.sum() == 0:
        continue
    v = lum[y, X0:X1][band]
    dark = int((v < 90).sum())
    print("  R", y, "n", int(band.sum()), "mean", round(float(v.mean()), 2), "dark90", dark)

# 眼白/虹膜列分布：找眼睛的水平跨度
print("EYE_COLS")
for y in [512, 516, 520, 524, 528, 532, 536, 540]:
    row = mask[y, X0:X1]
    xs = np.nonzero(row)[0]
    if len(xs) == 0:
        print("  R", y, "-")
        continue
    v = lum[y, X0:X1][row]
    darkxs = np.nonzero((v < 90))[0]
    print("  R", y, "span", int(xs.min()) + X0, int(xs.max()) + X0, "dark_n", len(darkxs))
print("EYE2_DONE")
