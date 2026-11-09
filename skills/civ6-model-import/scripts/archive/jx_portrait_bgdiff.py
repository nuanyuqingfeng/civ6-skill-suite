import numpy as np
from PIL import Image

PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"

im = Image.open(PORTRAIT).convert("RGB")
rgb = np.asarray(im).astype(np.int32)
h, w, _ = rgb.shape

# 背景模型：取左右各 30 列的逐行中位色，人物不进入这两条边带
left = np.median(rgb[:, :30, :], axis=1)
right = np.median(rgb[:, w - 30:, :], axis=1)
bg = (left + right) / 2.0

d = np.abs(rgb - bg[:, None, :]).sum(axis=2)
mask = d > 90

# 去掉两条边带自身，避免模型误差
mask[:, :30] = False
mask[:, w - 30:] = False

rows = mask.sum(axis=1)
nz = np.nonzero(rows > 0)[0]
print("SIZE", w, h, "px", int(mask.sum()), "row_range", int(nz[0]), int(nz[-1]))

print("WIDTH per 8 rows")
out = []
for y in range(0, h, 8):
    xs = np.nonzero(mask[y])[0]
    if len(xs) == 0:
        out.append("%d:-" % y)
    else:
        out.append("%d:%d,%d,%d" % (y, int(xs[0]), int(xs[-1]), len(xs)))
print(" ".join(out))

# 皮肤：在背景差分掩膜内找肤色
r_ = rgb[:, :, 0]
g_ = rgb[:, :, 1]
b_ = rgb[:, :, 2]
skin = mask & (r_ > 150) & (g_ > 100) & (b_ > 80) & (r_ - b_ > 25) & (r_ - b_ < 120) & (r_ >= g_) & (g_ >= b_ - 10)
sr = skin.sum(axis=1)
print("SKIN_ROWS", " ".join("%d:%d" % (y, int(sr[y])) for y in range(0, h, 8) if sr[y] > 0))
print("SKIN_TOTAL", int(skin.sum()))
