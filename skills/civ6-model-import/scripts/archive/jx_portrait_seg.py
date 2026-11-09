import json
import sys

import numpy as np
from PIL import Image

PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"

im = Image.open(PORTRAIT).convert("RGB")
rgb = np.asarray(im).astype(np.int32)
h, w, _ = rgb.shape
lum = (rgb[:, :, 0] * 299 + rgb[:, :, 1] * 587 + rgb[:, :, 2] * 114) // 1000

fg = lum > 55
print("SIZE", w, h, "fg_px", int(fg.sum()))

rows = fg.sum(axis=1)
cols = fg.sum(axis=0)
nz_rows = np.nonzero(rows > 0)[0]
nz_cols = np.nonzero(cols > 0)[0]
print("FG_ROW", int(nz_rows[0]), int(nz_rows[-1]))
print("FG_COL", int(nz_cols[0]), int(nz_cols[-1]))

band = 16
agg = [int(rows[i:i + band].sum()) for i in range(0, h, band)]
print("ROWBAND", " ".join("%d:%d" % (i * band, v) for i, v in enumerate(agg)))

colband = 32
agc = [int(cols[i:i + colband].sum()) for i in range(0, w, colband)]
print("COLBAND", " ".join("%d:%d" % (i * colband, v) for i, v in enumerate(agc)))

# 逐行前景的左右边界，用来判断头、肩、腰、脚的结构变化
def edges(y):
    xs = np.nonzero(fg[y])[0]
    if len(xs) == 0:
        return None
    return int(xs[0]), int(xs[-1]), len(xs)

for y in range(0, h, 25):
    e = edges(y)
    if e is not None:
        print("EDGE", y, e[0], e[1], e[2])
