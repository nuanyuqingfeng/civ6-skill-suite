import json

import numpy as np
from PIL import Image
from scipy import ndimage

PORTRAIT = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/portrait.png"


def skin(rgb):
    r = rgb[:, :, 0].astype(np.int32)
    g = rgb[:, :, 1].astype(np.int32)
    b = rgb[:, :, 2].astype(np.int32)
    return (r > 140) & (g > 95) & (b > 75) & (r - b > 22) & (r - b < 125) & (r >= g) & (g >= b - 12)


rgb = np.asarray(Image.open(PORTRAIT).convert("RGB"))
h, w, _ = rgb.shape
f = rgb.astype(np.float64)
bg = np.median(f[:, w - 60:w, :], axis=1)
diff = np.abs(f - bg[:, None, :]).sum(axis=2)
fg = diff > 42
fg[:, :1500] = False
fg[:, 2450:] = False
print("SIZE", w, h, "fg", int(fg.sum()))
rows = fg.sum(axis=1)
for y in range(0, h, 8):
    xs = np.nonzero(fg[y])[0]
    if len(xs) == 0:
        continue
    print("R", y, int(rows[y]), int(xs[0]), int(xs[-1]))

sk = skin(rgb)
sk[:, :1500] = False
lab, n = ndimage.label(sk)
sizes = ndimage.sum(sk, lab, range(1, n + 1))
order = np.argsort(sizes)[::-1]
print("SKIN_N", n)
for oi in order[:6]:
    comp = lab == (oi + 1)
    ys, xs = np.nonzero(comp)
    bw = int(xs.max() - xs.min() + 1)
    bh = int(ys.max() - ys.min() + 1)
    print("SK", int(sizes[oi]), int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()),
          "w", bw, "h", bh, "ar", round(bw / bh, 3))

json.dump({"w": w, "h": h}, open(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/hb3_meta.json", "w", encoding="utf-8"))
print("HB3_DONE")
