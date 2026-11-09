import numpy as np
from PIL import Image

p = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"
im = Image.open(p).convert("RGB")
a = np.asarray(im).astype(np.float32)
lum = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
h, w = lum.shape
print("SIZE", w, h)

mask = lum > 60
print("MASK_PX", int(mask.sum()))
rows = np.where(mask.any(axis=1))[0]
print("ROW_RANGE", int(rows.min()), int(rows.max()))

for y in range(int(rows.min()), int(rows.max()) + 1, 8):
    xs = np.where(mask[y])[0]
    if xs.size == 0:
        print("R", y, 0, -1, -1)
        continue
    print("R", y, int(xs.size), int(xs.min()), int(xs.max()))
