import numpy as np
from PIL import Image
import sys

path = sys.argv[1]
img = Image.open(path).convert("RGB")
a = np.asarray(img).astype(np.float32)
h, w, _ = a.shape
lum = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
rows, cols = 32, 48
print("SIZE", w, h)
for ry in range(rows):
    y0 = h * ry // rows
    y1 = h * (ry + 1) // rows
    cells = []
    for cx in range(cols):
        x0 = w * cx // cols
        x1 = w * (cx + 1) // cols
        block = lum[y0:y1, x0:x1]
        cells.append(int(block.mean() / 16))
    print("R%02d" % ry, "".join("%X" % min(15, c) for c in cells))
