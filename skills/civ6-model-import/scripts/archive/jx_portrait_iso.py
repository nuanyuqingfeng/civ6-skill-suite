import numpy as np
from PIL import Image
from scipy import ndimage

P = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/portrait.png"
im = Image.open(P).convert("RGB")
a = np.asarray(im).astype(np.float64)
lum = a[:, :, 0] * 0.299 + a[:, :, 1] * 0.587 + a[:, :, 2] * 0.114
print("SIZE", a.shape[1], a.shape[0])

k = 9
m1 = ndimage.uniform_filter(lum, k)
m2 = ndimage.uniform_filter(lum * lum, k)
std = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
print("STD_PCT", [round(float(np.percentile(std, q)), 3) for q in (50, 75, 90, 95, 99)])

for thr in (10.0, 14.0, 18.0):
    m = std > thr
    m = ndimage.binary_closing(m, np.ones((5, 5)))
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    idx = int(np.argmax(sizes)) + 1
    c = lab == idx
    ys, xs = np.nonzero(c)
    print("THR", thr, "comps", n, "big", int(sizes[idx - 1]),
          "bbox", int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    rows = c.sum(axis=1)
    nz = np.nonzero(rows)[0]
    print("  rows", int(nz[0]), int(nz[-1]))
    prof = [(int(y), int(rows[y])) for y in range(int(nz[0]), int(nz[-1]) + 1, 25)]
    print("  prof", prof)
