import numpy as np
from PIL import Image

ROOT = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame12"
IMG = ROOT + "/01_bangs_new.png"
PLATE = ROOT + "/02_plate.png"

a = np.asarray(Image.open(IMG).convert("RGB")).astype(np.int32)
b = np.asarray(Image.open(PLATE).convert("RGB")).astype(np.int32)
d = np.abs(a - b).sum(axis=2)
mask = d > 64
print("MASK", int(mask.sum()))

r, g, bl = a[:, :, 0], a[:, :, 1], a[:, :, 2]
lum = (r * 299 + g * 587 + bl * 114) // 1000
dark = (lum < 40) & mask
print("DARK_IN_MASK", int(dark.sum()))
ys, xs = np.nonzero(dark)
if len(ys):
    print("DARK_BBOX", int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    hist, edges = np.histogram(ys, bins=20)
    print("DARK_ROW_HIST", [(int(edges[i]), int(hist[i])) for i in range(20) if hist[i] > 0])

# 面部窗口：头心列 1289 附近，行 400..700
x0, x1 = 1189, 1389
y0, y1 = 400, 700
sub = mask[y0:y1, x0:x1]
sub_dark = dark[y0:y1, x0:x1]
print("FACE_MASK_PX", int(sub.sum()), "FACE_DARK_PX", int(sub_dark.sum()))
if sub.sum():
    print("FACE_DARK_FRAC", round(float(sub_dark.sum()) / float(sub.sum()), 4))

# 分块亮度
for yy in range(400, 700, 50):
    blk = mask[yy:yy + 50, x0:x1]
    if blk.sum() == 0:
        continue
    v = lum[yy:yy + 50, x0:x1][blk]
    print("BAND", yy, int(blk.sum()), round(float(v.mean()), 2), round(float((v < 40).mean()), 4))
print("DARK_SEAM_DONE")
