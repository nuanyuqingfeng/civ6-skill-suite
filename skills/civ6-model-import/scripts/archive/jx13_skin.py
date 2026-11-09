import numpy as np
from PIL import Image

path = "workspace/gen/reports/ingame13/01_local.png"
img = np.asarray(Image.open(path).convert("RGB")).astype(np.int32)
h, w, _ = img.shape
R, G, B = img[:, :, 0], img[:, :, 1], img[:, :, 2]
skin = (R > 210) & (G > 150) & (G < 215) & (B > 140) & (B < 205) & (R - B > 20)
ys, xs = np.nonzero(skin)
print("SKIN px", len(xs))
if len(xs):
    print("SKIN bbox x", int(xs.min()), int(xs.max()), "y", int(ys.min()), int(ys.max()))
    print("SKIN center", (int(xs.min()) + int(xs.max())) // 2, (int(ys.min()) + int(ys.max())) // 2)
    hist = np.bincount(ys, minlength=h)
    top = np.argsort(hist)[-5:][::-1]
    print("SKIN rows", [(int(t), int(hist[t])) for t in top])
band = slice(int(h * 0.55), int(h * 0.85))
sub = skin[band]
xs2 = np.nonzero(sub.any(axis=0))[0]
print("BAND", int(h * 0.55), int(h * 0.85), "cols", (int(xs2.min()), int(xs2.max())) if len(xs2) else None)

for r0 in range(0, h, 76):
    seg = skin[r0:r0 + 76]
    print("BANDROW", r0, int(seg.sum()))
