import numpy as np
from PIL import Image
from scipy import ndimage

IMG = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame11/01_scale09.png"
PLATE = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame11/02_plate.png"


def skin(rgb):
    r = rgb[:, :, 0].astype(np.int32)
    g = rgb[:, :, 1].astype(np.int32)
    b = rgb[:, :, 2].astype(np.int32)
    return (r > 150) & (g > 100) & (b > 80) & (r - b > 25) & (r - b < 120) & (r >= g) & (g >= b - 10)


a = np.asarray(Image.open(IMG).convert("RGB")).astype(np.int32)
b = np.asarray(Image.open(PLATE).convert("RGB")).astype(np.int32)
h, w, _ = a.shape
d = np.abs(a - b).sum(axis=2)
m = d > 64
print("MASK", int(m.sum()))
ys, xs = np.nonzero(m)
print("BBOX", int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()),
      "H", int(ys.max() - ys.min() + 1), "W", int(xs.max() - xs.min() + 1))

lum = (a[:, :, 0] * 299 + a[:, :, 1] * 587 + a[:, :, 2] * 114) // 1000
sk = skin(a.astype(np.uint8))
print("SKIN_PX", int(sk.sum()))

face_rows = sk.sum(axis=1)
cand = [(y, int(face_rows[y])) for y in range(h) if face_rows[y] > 300]
print("FACE_ROW_CAND", cand[:6], cand[-6:] if cand else [])

# 头部窗口：用掩膜在 y 前 45% 的横向中位定位
head = m.copy()
head[int(h * 0.45):, :] = False
ys2, xs2 = np.nonzero(head)
if len(xs2) > 0:
    print("HEAD_BBOX", int(xs2.min()), int(ys2.min()), int(xs2.max()), int(ys2.max()))

# 面部亮度：取肤色最大连通域外接框内、掩膜内部的像素
lab, n = ndimage.label(sk)
sizes = ndimage.sum(sk, lab, range(1, n + 1))
oi = int(np.argmax(sizes))
comp = lab == (oi + 1)
ys3, xs3 = np.nonzero(comp)
x0, x1, y0, y1 = int(xs3.min()), int(xs3.max()), int(ys3.min()), int(ys3.max())
print("FACE_BLOB", int(sizes[oi]), x0, x1, y0, y1)
sub_l = lum[y0:y1 + 1, x0:x1 + 1]
sub_m = m[y0:y1 + 1, x0:x1 + 1]
vals = sub_l[sub_m]
print("FACE_LUM mean", round(float(vals.mean()), 2),
      "dark40", round(float((vals < 40).mean()), 4),
      "dark120", round(float((vals < 120).mean()), 4))
print("PROBE_DONE")
