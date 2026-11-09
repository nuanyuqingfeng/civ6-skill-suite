import sys

import numpy as np
from PIL import Image
from scipy import ndimage

path = sys.argv[1]
tag = sys.argv[2]
img = np.asarray(Image.open(path).convert("RGB")).astype(np.int32)
h, w, _ = img.shape
lum = (img[:, :, 0] * 299 + img[:, :, 1] * 587 + img[:, :, 2] * 114) // 1000
mask = lum > 90
mask[: int(h * 0.06)] = False
mask[:, : int(w * 0.45)] = False
mask = ndimage.binary_closing(mask, np.ones((5, 5)))
labels, count = ndimage.label(mask)
sizes = ndimage.sum(mask, labels, range(1, count + 1))
order = np.argsort(sizes)[::-1][:3]
for idx in order:
    lab = int(idx) + 1
    ys, xs = np.nonzero(labels == lab)
    print("FIG", tag, "comp", lab, "area", int(sizes[idx]),
          "x", int(xs.min()), int(xs.max()), "y", int(ys.min()), int(ys.max()),
          "h", int(ys.max() - ys.min() + 1))
