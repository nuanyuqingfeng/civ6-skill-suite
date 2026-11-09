import numpy as np
from PIL import Image

P = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/portrait.png"
rgb = np.asarray(Image.open(P).convert("RGB")).astype(np.int32)
h, w, _ = rgb.shape
lum = (rgb[:, :, 0] * 299 + rgb[:, :, 1] * 587 + rgb[:, :, 2] * 114) // 1000
r = rgb[:, :, 0]
g = rgb[:, :, 1]
b = rgb[:, :, 2]
skin = (r > 140) & (g > 95) & (b > 75) & (r - b > 20) & (r - b < 130) & (r >= g) & (g >= b - 15)

print("SIZE", w, h)
for t in (80, 100, 120, 140, 160, 180):
    m = lum > t
    ys, xs = np.nonzero(m)
    print("THR", t, "px", int(m.sum()), "y", int(ys.min()), int(ys.max()), "x", int(xs.min()), int(xs.max()))

m = lum > 120
print("ROWPROF thr120")
for y in range(150, 1201, 10):
    xs = np.nonzero(m[y])[0]
    sk = int(skin[y].sum())
    if len(xs) == 0:
        print("  R", y, "0", "-", "-", "sk", sk)
    else:
        print("  R", y, len(xs), int(xs.min()), int(xs.max()), "sk", sk)
