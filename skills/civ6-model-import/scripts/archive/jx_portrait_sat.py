import numpy as np
from PIL import Image
from scipy import ndimage

PATH = "workspace/tmp/portrait.png"

im = Image.open(PATH).convert("RGB")
rgb = np.asarray(im).astype(np.int32)
h, w, _ = rgb.shape
mx = rgb.max(axis=2)
mn = rgb.min(axis=2)
chroma = mx - mn
mask = (chroma > 40) & (mx > 50)
print("SIZE", w, h, "chroma_px", int(mask.sum()))

lab, n = ndimage.label(mask)
sizes = ndimage.sum(mask, lab, range(1, n + 1))
order = np.argsort(sizes)[::-1]
for oi in order[:5]:
    comp = lab == (oi + 1)
    ys, xs = np.nonzero(comp)
    print("COMP", int(sizes[oi]), "x", int(xs.min()), int(xs.max()), "y", int(ys.min()), int(ys.max()))

idx = int(order[0]) + 1
comp = lab == idx
ys, xs = np.nonzero(comp)
y0, y1 = int(ys.min()), int(ys.max())
x0, x1 = int(xs.min()), int(xs.max())
print("BODY bbox", x0, y0, x1, y1, "h", y1 - y0 + 1, "w", x1 - x0 + 1)

prof = comp.sum(axis=1)
for y in range(y0, y1 + 1, 10):
    print("PROF", y, int(prof[y]))

skin = (rgb[:, :, 0] > 150) & (rgb[:, :, 1] > 100) & (rgb[:, :, 2] > 80)
skin &= (rgb[:, :, 0] - rgb[:, :, 2] > 25) & (rgb[:, :, 0] - rgb[:, :, 2] < 120)
skin &= (rgb[:, :, 0] >= rgb[:, :, 1]) & (rgb[:, :, 1] >= rgb[:, :, 2] - 10)
skin &= comp
lab2, n2 = ndimage.label(skin)
sizes2 = ndimage.sum(skin, lab2, range(1, n2 + 1))
order2 = np.argsort(sizes2)[::-1]
print("SKIN comps", n2)
for oi in order2[:10]:
    c = lab2 == (oi + 1)
    yy, xx = np.nonzero(c)
    ww = int(xx.max() - xx.min() + 1)
    hh = int(yy.max() - yy.min() + 1)
    print("  SK", int(sizes2[oi]), "x", int(xx.min()), int(xx.max()), "y", int(yy.min()), int(yy.max()),
          "w", ww, "h", hh, "fill", round(float(sizes2[oi]) / (ww * hh), 3))
