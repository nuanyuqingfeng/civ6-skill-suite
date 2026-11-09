import sys

import numpy as np
from PIL import Image

path = sys.argv[1]
x0 = int(sys.argv[2])
level = int(sys.argv[3]) if len(sys.argv) > 3 else 120
img = np.asarray(Image.open(path).convert("RGB")).astype(np.int32)
lum = (img[:, :, 0] * 299 + img[:, :, 1] * 587 + img[:, :, 2] * 114) // 1000
h, w = lum.shape
sub = lum[:, x0:w] > level
row_counts = sub.sum(axis=1)
first = None
for y in range(int(h * 0.05), h):
    if row_counts[y] >= 30:
        first = y
        break
print("TOP", path.split("/")[-1], "x0", x0, "level", level, "first_row", first)
for y in range(max(0, first - 6), min(h, first + 60), 4):
    print("ROW", y, int(row_counts[y]))
