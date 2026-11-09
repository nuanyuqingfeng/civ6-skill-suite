import sys

import numpy as np
from PIL import Image
from scipy import ndimage

a = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(np.int32)
b = np.asarray(Image.open(sys.argv[2]).convert("RGB")).astype(np.int32)
tag = sys.argv[3]
h, w, _ = a.shape
diff = np.abs(a - b).sum(axis=2)
mask = diff > 24
mask[: int(h * 0.06)] = False
mask = ndimage.binary_closing(mask, np.ones((9, 9)))
mask = ndimage.binary_opening(mask, np.ones((3, 3)))
labels, count = ndimage.label(mask)
if count == 0:
    print("MOTION", tag, "none")
    raise SystemExit
sizes = ndimage.sum(mask, labels, range(1, count + 1))
idx = int(np.argmax(sizes)) + 1
ys, xs = np.nonzero(labels == idx)
print("MOTION", tag, "comps", count, "area", int(sizes[idx - 1]),
      "x", int(xs.min()), int(xs.max()), "y", int(ys.min()), int(ys.max()),
      "h", int(ys.max() - ys.min() + 1), "w", int(xs.max() - xs.min() + 1))
