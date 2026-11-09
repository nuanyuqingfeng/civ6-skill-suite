import sys

import numpy as np
from PIL import Image
from scipy import ndimage

path = sys.argv[1]
tag = sys.argv[2] if len(sys.argv) > 2 else path
level = int(sys.argv[3]) if len(sys.argv) > 3 else 140
img = np.asarray(Image.open(path).convert("RGB")).astype(np.int32)
h, w, _ = img.shape
R, G, B = img[:, :, 0], img[:, :, 1], img[:, :, 2]
lum = (R * 299 + G * 587 + B * 114) // 1000
mask = lum > level
mask[: int(h * 0.05)] = False
mask = ndimage.binary_opening(mask, np.ones((3, 3)))
labels, count = ndimage.label(mask)
sizes = ndimage.sum(mask, labels, range(1, count + 1))
big = int(np.argmax(sizes)) + 1
mask = labels == big
ys, xs = np.nonzero(mask)
top, bottom = int(ys.min()), int(ys.max())
left, right = int(xs.min()), int(xs.max())
widths = np.bincount(ys, minlength=h)
peak = int(widths[top : top + (bottom - top) // 3 + 1].max())
skull = top
for y in range(top, top + (bottom - top) // 3 + 1):
    if widths[y] >= peak * 0.4:
        skull = y
        break
print("SIL", tag, "level", level, "size", w, h, "comps", count)
print("SIL", tag, "bbox x", left, right, "y", top, bottom, "height", bottom - top + 1)
print("SIL", tag, "head_peak", peak, "spike_rows", skull - top, "skull_row", skull,
      "max_width", int(widths.max()), "max_width_row", int(np.argmax(widths)))
