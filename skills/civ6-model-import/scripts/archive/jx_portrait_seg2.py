import numpy as np
from PIL import Image

PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"

im = Image.open(PORTRAIT).convert("RGB")
rgb = np.asarray(im).astype(np.int32)
h, w, _ = rgb.shape

# 边框 40 像素排除，背景按行取左侧参考色
FRAME = 40
ref = rgb[:, FRAME + 2, :][:, None, :]
d = np.abs(rgb - ref).sum(axis=2)
mask = d > 60
mask[:FRAME, :] = False
mask[-FRAME:, :] = False
mask[:, :FRAME] = False
mask[:, -FRAME:] = False

rows = mask.sum(axis=1)
print("SIZE", w, h)
nz = np.nonzero(rows > 3)[0]
print("ROW_NZ", int(nz[0]), int(nz[-1]))

for y in range(int(nz[0]), int(nz[-1]) + 1, 8):
    xs = np.nonzero(mask[y])[0]
    if len(xs) == 0:
        print("R", y, 0, "-", "-")
        continue
    print("R", y, len(xs), int(xs[0]), int(xs[-1]))
