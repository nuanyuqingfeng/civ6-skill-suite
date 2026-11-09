import sys

import numpy as np
from PIL import Image
from scipy import ndimage

img = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(np.int32)
h, w, _ = img.shape
R, G, B = img[:, :, 0], img[:, :, 1], img[:, :, 2]
skin = (R > 200) & (G > 150) & (G < 215) & (B > 140) & (B < 205) & (R - B > 20)
labels, count = ndimage.label(skin)
sizes = ndimage.sum(skin, labels, range(1, count + 1))
order = np.argsort(sizes)[::-1][:8]
print("IMG", w, h, "components", count)
for idx in order:
    lab = int(idx) + 1
    ys, xs = np.nonzero(labels == lab)
    print("COMP", lab, "area", int(sizes[idx]),
          "bbox x", int(xs.min()), int(xs.max()), "y", int(ys.min()), int(ys.max()),
          "centroid", int(xs.mean()), int(ys.mean()))
