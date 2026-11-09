import numpy as np
from PIL import Image

P = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"
im = Image.open(P).convert("RGB")
a = np.asarray(im).astype(np.int16)
h, w, _ = a.shape
print("SIZE", w, h)
gy, gx = 40, 40
print("GRID mean rgb")
for by in range(0, h, h // gy):
    row = []
    for bx in range(0, w, w // gx):
        blk = a[by:by + h // gy, bx:bx + w // gx]
        row.append("%3d,%3d,%3d" % (blk[:, :, 0].mean(), blk[:, :, 1].mean(), blk[:, :, 2].mean()))
    print("%4d " % by + " | ".join(row))
