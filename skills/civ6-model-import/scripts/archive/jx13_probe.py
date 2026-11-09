import numpy as np
from PIL import Image

path = "workspace/gen/reports/ingame13/01_local.png"
img = np.asarray(Image.open(path).convert("RGB")).astype(np.int32)
h, w, _ = img.shape
lum = (img[:, :, 0] * 299 + img[:, :, 1] * 587 + img[:, :, 2] * 114) // 1000
print("IMG", w, h, "LUM_MEAN", round(float(lum.mean()), 2))

col = lum.mean(axis=0)
row = lum.mean(axis=1)
print("COL_MAX", int(col.argmax()), round(float(col.max()), 2))
print("ROW_MAX", int(row.argmax()), round(float(row.max()), 2))

bright = lum > 150
ys, xs = np.nonzero(bright)
print("BRIGHT px", len(xs))
if len(xs):
    print("BRIGHT bbox x", int(xs.min()), int(xs.max()), "y", int(ys.min()), int(ys.max()))
    print("BRIGHT center", (int(xs.min()) + int(xs.max())) // 2, (int(ys.min()) + int(ys.max())) // 2)

mid = lum > 90
ys2, xs2 = np.nonzero(mid)
print("MID px", len(xs2))
if len(xs2):
    print("MID bbox x", int(xs2.min()), int(xs2.max()), "y", int(ys2.min()), int(ys2.max()))
