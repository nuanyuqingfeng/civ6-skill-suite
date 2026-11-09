import json

import numpy as np
from PIL import Image
from scipy import ndimage

D = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame11"
IMG = D + "/01_scale09.png"
PLATE = D + "/02_plate.png"

a = np.asarray(Image.open(IMG).convert("RGB")).astype(np.int32)
b = np.asarray(Image.open(PLATE).convert("RGB")).astype(np.int32)
print("SHAPE", a.shape, b.shape)
d = np.abs(a - b).sum(axis=2)
print("DIFF max", int(d.max()), "px>64", int((d > 64).sum()))
m = d > 64
m = ndimage.binary_opening(m, np.ones((3, 3)))
lab, n = ndimage.label(m)
sizes = ndimage.sum(m, lab, range(1, n + 1))
idx = int(np.argmax(sizes)) + 1
body = lab == idx
ys, xs = np.nonzero(body)
x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
print("BODY px", int(sizes[idx - 1]), "bbox", x0, y0, x1, y1, "h", y1 - y0 + 1, "w", x1 - x0 + 1)

cx = (x0 + x1) // 2
print("CENTER_X", cx)

rgb = a
r = rgb[:, :, 0]
g = rgb[:, :, 1]
bl = rgb[:, :, 2]
lum = (r * 299 + g * 587 + bl * 114) // 1000

half = max(20, (x1 - x0) // 12)
lo, hi = max(0, cx - half), min(rgb.shape[1], cx + half + 1)
hair = (r.astype(np.int32) - bl.astype(np.int32) <= 12) & (lum >= 150)
win = hair[y0:y1 + 1, lo:hi]
rows = win.sum(axis=1)
peak = int(rows.max())
thr = peak * 0.2
first = None
for i, v in enumerate(rows):
    if v < thr:
        first = y0 + i
        break
print("HAIR_WIN", lo, hi, "peak", peak, "thr", round(thr, 1), "first_below_row", first)

# 逐行发色像素序列，供判读下缘
seq = [(y0 + i, int(v)) for i, v in enumerate(rows) if v > 0]
print("HAIR_ROWS", len(seq))
print("HAIR_HEAD", seq[:6])
print("HAIR_TAIL", seq[-24:])

# 面部亮度：头心列向左右各取 50 列，纵向取发色下缘往下 60 行
fy0 = first if first is not None else y0
fy1 = min(y1, fy0 + 60)
flo, fhi = max(0, cx - 50), min(rgb.shape[1], cx + 51)
sub = lum[fy0:fy1, flo:fhi]
smask = body[fy0:fy1, flo:fhi]
vals = sub[smask]
print("FACE_WIN", flo, fhi, fy0, fy1, "px", int(vals.size))
print("FACE_MEAN", round(float(vals.mean()), 2), "dark40", round(float((vals < 40).mean()), 4),
      "dark120", round(float((vals < 120).mean()), 4))

# 毛刺：掩膜外接框内，逐行左边界序列的一阶差分的绝对值统计
lefts = []
rights = []
for y in range(y0, y1 + 1):
    xs_row = np.nonzero(body[y])[0]
    if xs_row.size == 0:
        lefts.append(-1)
        rights.append(-1)
        continue
    lefts.append(int(xs_row[0]))
    rights.append(int(xs_row[-1]))
lv = np.array([v for v in lefts if v >= 0])
rv = np.array([v for v in rights if v >= 0])
dl = np.abs(np.diff(lv))
dr = np.abs(np.diff(rv))
print("LEFT_JUMP max", int(dl.max()), "mean", round(float(dl.mean()), 2), "n>10", int((dl > 10).sum()))
print("RIGHT_JUMP max", int(dr.max()), "mean", round(float(dr.mean()), 2), "n>10", int((dr > 10).sum()))

# 孤立细结构：开运算后消失的像素数（毛刺多为 1~2 像素宽）
op = ndimage.binary_opening(m, np.ones((2, 2)))
lost = int(m.sum() - op.sum())
print("THIN_LOST", lost, "ratio", round(lost / float(m.sum()), 5))

out = {
    "img": IMG, "plate": PLATE,
    "body_px": int(sizes[idx - 1]),
    "bbox": [x0, y0, x1, y1], "h": y1 - y0 + 1, "w": x1 - x0 + 1,
    "center_x": cx,
    "hair_win": [lo, hi], "hair_peak": peak, "hair_first_below": first,
    "face_mean": round(float(vals.mean()), 2),
    "face_dark40": round(float((vals < 40).mean()), 4),
    "face_dark120": round(float((vals < 120).mean()), 4),
    "left_jump_max": int(dl.max()), "right_jump_max": int(dr.max()),
    "thin_lost": lost, "thin_ratio": round(lost / float(m.sum()), 5),
}
with open(D + "/probe11.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print("PROBE11_DONE")
