import numpy as np
from PIL import Image

PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"

rgb = np.asarray(Image.open(PORTRAIT).convert("RGB")).astype(np.int32)
h, w, _ = rgb.shape
lum = (rgb[:, :, 0] * 299 + rgb[:, :, 1] * 587 + rgb[:, :, 2] * 114) // 1000
fg = lum > 45
fg[:3, :] = False
fg[-3:, :] = False
fg[:, :3] = False
fg[:, -3:] = False

r = rgb[:, :, 0]
g = rgb[:, :, 1]
b = rgb[:, :, 2]
skin = (r > 150) & (g > 100) & (b > 80) & (r - b > 25) & (r - b < 120) & (r >= g) & (g >= b - 10)

print("SIZE", w, h)
for y in range(140, 800, 10):
    xs = np.nonzero(fg[y])[0]
    if len(xs) == 0:
        print("ROW", y, "empty")
        continue
    sk = int(skin[y].sum())
    print("ROW", y, "fg", int(len(xs)), "x", int(xs[0]), int(xs[-1]), "skin", sk)

# 亮度数字网格：上半部分
print("GRID")
for y in range(100, 820, 24):
    cells = []
    for x in range(0, w, 40):
        v = int(lum[y:y + 24, x:x + 40].mean())
        cells.append("0123456789abcdefghijklmnopqrstuvwxyz"[min(35, v // 8)])
    print("G%4d" % y, "".join(cells))
