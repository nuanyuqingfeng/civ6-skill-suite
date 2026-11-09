import numpy as np
from PIL import Image

P = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/portrait.png"

im = Image.open(P).convert("RGB")
rgb = np.asarray(im).astype(np.int32)
h, w, _ = rgb.shape
r = rgb[:, :, 0]
g = rgb[:, :, 1]
b = rgb[:, :, 2]
lum = (r * 299 + g * 587 + b * 114) // 1000
mx = rgb.max(axis=2)
mn = rgb.min(axis=2)
sat = mx - mn

X0, X1 = 1250, 2250
sub = slice(X0, X1)
hair = (lum > 185) & (sat < 45)
skin = (r > 150) & (g > 105) & (b > 95) & (r - b > 20) & (r >= g) & (g >= b)
dark = (lum > 60) & (lum <= 185)

print("SIZE", w, h)
hc = hair[:, sub].sum(axis=1)
sc = skin[:, sub].sum(axis=1)
dc = dark[:, sub].sum(axis=1)
print("ROW hair skin dark  (x window %d..%d)" % (X0, X1))
for y in range(180, 1230, 12):
    print("R %4d %5d %5d %5d" % (y, hc[y], sc[y], dc[y]))
