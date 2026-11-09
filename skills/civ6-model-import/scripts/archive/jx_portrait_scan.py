import numpy as np
from PIL import Image
import sys

P = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"

im = Image.open(P).convert("RGB")
a = np.asarray(im).astype(np.int16)
h, w, _ = a.shape
print("SIZE", w, h)

r = a[:, :, 0]
g = a[:, :, 1]
b = a[:, :, 2]
mx = a.max(axis=2)
mn = a.min(axis=2)
lum = (r * 299 + g * 587 + b * 114) // 1000

fg = lum > 45
print("FG_PX", int(fg.sum()))
rows = fg.sum(axis=1)
cols = fg.sum(axis=0)
print("ROW_RANGE", int(np.argmax(rows > 3)), int(h - 1 - np.argmax(rows[::-1] > 3)))
print("COL_RANGE", int(np.argmax(cols > 3)), int(w - 1 - np.argmax(cols[::-1] > 3)))

skin = (r > 150) & (g > 105) & (b > 85) & (r > g + 18) & (g > b + 8) & (mx - mn > 20)
print("SKIN_PX", int(skin.sum()))
srows = skin.sum(axis=1)
print("SKIN_ROW_RANGE", int(np.argmax(srows > 5)), int(h - 1 - np.argmax(srows[::-1] > 5)))

step = 25
out = []
for y in range(0, h, step):
    out.append("%d:fg%d:sk%d" % (y, int(rows[y]), int(srows[y])))
print("PROFILE", " ".join(out))
