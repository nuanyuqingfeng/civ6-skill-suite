import json

import numpy as np
from PIL import Image
from scipy import ndimage

PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"


def skin(rgb):
    r = rgb[:, :, 0].astype(np.int32)
    g = rgb[:, :, 1].astype(np.int32)
    b = rgb[:, :, 2].astype(np.int32)
    return (r > 150) & (g > 100) & (b > 80) & (r - b > 25) & (r - b < 130) & (r >= g) & (g >= b - 12)


im = Image.open(PORTRAIT).convert("RGB")
rgb = np.asarray(im)
h, w, _ = rgb.shape
lum = rgb[:, :, 0].astype(np.int32) * 299 + rgb[:, :, 1].astype(np.int32) * 587 + rgb[:, :, 2].astype(np.int32) * 114
lum //= 1000

body = lum > 100
body[:, :200] = False
body[:, 2470:] = False
lab, n = ndimage.label(body)
sizes = ndimage.sum(body, lab, range(1, n + 1))
idx = int(np.argmax(sizes)) + 1
comp = lab == idx
ys, xs = np.nonzero(comp)
top, bot = int(ys.min()), int(ys.max())
print("SIZE", w, h, "comps", n, "body_px", int(sizes[idx - 1]))
print("BODY_BBOX", int(xs.min()), top, int(xs.max()), bot, "h", bot - top + 1)

sk = skin(rgb) & comp
slab, sn = ndimage.label(sk)
ssizes = ndimage.sum(sk, slab, range(1, sn + 1))
order = np.argsort(ssizes)[::-1]
upper = top + int(0.45 * (bot - top))
best = None
for oi in order[:20]:
    c = slab == (oi + 1)
    yy, xx = np.nonzero(c)
    y0, y1 = int(yy.min()), int(yy.max())
    if y0 < upper:
        info = {"px": int(ssizes[oi]), "y0": y0, "y1": y1, "x0": int(xx.min()), "x1": int(xx.max())}
        print("SKIN_UP", info)
        if best is None or info["px"] > best["px"]:
            best = info
print("FACE", best)
if best is not None:
    head = best["y1"] - top + 1
    full = bot - top + 1
    print("HEAD_PX", head, "FULL_PX", full, "RATIO", round(head / full, 6), "HEADS", round(full / head, 4))
out = {"size": [w, h], "body_bbox": [int(xs.min()), top, int(xs.max()), bot], "face": best}
with open(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/portrait_head_body.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("PROBE_DONE")
