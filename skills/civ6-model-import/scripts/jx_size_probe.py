import json

import numpy as np
from PIL import Image
from scipy import ndimage

PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"
INGAME = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame9/70_jinhsi_face.png"
PLATE = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame9/72_no_leader_plate.png"
OUT = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/size_probe.json"


def skin_mask(rgb):
    r = rgb[:, :, 0].astype(np.int32)
    g = rgb[:, :, 1].astype(np.int32)
    b = rgb[:, :, 2].astype(np.int32)
    return (r > 150) & (g > 100) & (b > 80) & (r - b > 25) & (r - b < 130) & (r >= g - 5) & (g >= b - 15)


def largest(mask):
    lab, n = ndimage.label(mask)
    if n == 0:
        return None, 0
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    idx = int(np.argmax(sizes)) + 1
    return lab == idx, int(sizes[idx - 1])


def row_extent(mask, ys):
    out = []
    for y in ys:
        xs = np.nonzero(mask[y])[0]
        if len(xs) == 0:
            out.append((int(y), None, None, 0))
        else:
            out.append((int(y), int(xs[0]), int(xs[-1]), int(len(xs))))
    return out


def portrait():
    rgb = np.asarray(Image.open(PORTRAIT).convert("RGB"))
    h, w, _ = rgb.shape
    img = rgb.astype(np.int32)
    left = img[:, 0:24, :].mean(axis=1)
    right = img[:, w - 24:w, :].mean(axis=1)
    bg = 0.5 * (left + right)
    diff = np.abs(img - bg[:, None, :]).max(axis=2)
    fg = diff > 40
    fg = ndimage.binary_opening(fg, np.ones((5, 5)))
    fg = ndimage.binary_closing(fg, np.ones((9, 9)))
    comp, px = largest(fg)
    ys, xs = np.nonzero(comp)
    res = {
        "size": [w, h],
        "fg_px": int(px),
        "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
    }
    rows = np.nonzero(comp.sum(axis=1) > 0)[0]
    res["row_range"] = [int(rows[0]), int(rows[-1])]
    res["row_extent"] = row_extent(comp, list(range(int(rows[0]), int(rows[-1]) + 1, 40)))
    sk = skin_mask(rgb) & comp
    lab, n = ndimage.label(sk)
    sizes = ndimage.sum(sk, lab, range(1, n + 1))
    order = np.argsort(sizes)[::-1][:12]
    faces = []
    for oi in order:
        c = lab == (oi + 1)
        yy, xx = np.nonzero(c)
        faces.append({
            "px": int(sizes[oi]),
            "y0": int(yy.min()), "y1": int(yy.max()),
            "x0": int(xx.min()), "x1": int(xx.max()),
            "w": int(xx.max() - xx.min() + 1), "h": int(yy.max() - yy.min() + 1),
            "fill": round(float(sizes[oi]) / float((xx.max() - xx.min() + 1) * (yy.max() - yy.min() + 1)), 3),
        })
    res["skin_comps"] = faces
    return res


def ingame():
    a = np.asarray(Image.open(INGAME).convert("RGB")).astype(np.int32)
    b = np.asarray(Image.open(PLATE).convert("RGB")).astype(np.int32)
    d = np.abs(a - b).max(axis=2)
    m = d > 40
    m = ndimage.binary_opening(m, np.ones((3, 3)))
    comp, px = largest(m)
    ys, xs = np.nonzero(comp)
    res = {
        "size": [int(a.shape[1]), int(a.shape[0])],
        "fg_px": int(px),
        "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
    }
    rows = np.nonzero(comp.sum(axis=1) > 0)[0]
    res["row_range"] = [int(rows[0]), int(rows[-1])]
    res["row_extent"] = row_extent(comp, list(range(int(rows[0]), int(rows[-1]) + 1, 40)))
    sk = skin_mask(a.astype(np.uint8)) & comp
    lab, n = ndimage.label(sk)
    sizes = ndimage.sum(sk, lab, range(1, n + 1))
    order = np.argsort(sizes)[::-1][:12]
    faces = []
    for oi in order:
        c = lab == (oi + 1)
        yy, xx = np.nonzero(c)
        faces.append({
            "px": int(sizes[oi]),
            "y0": int(yy.min()), "y1": int(yy.max()),
            "x0": int(xx.min()), "x1": int(xx.max()),
            "w": int(xx.max() - xx.min() + 1), "h": int(yy.max() - yy.min() + 1),
        })
    res["skin_comps"] = faces
    return res


out = {"portrait": portrait(), "ingame": ingame()}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

p = out["portrait"]
print("PORTRAIT size", p["size"], "fg_px", p["fg_px"], "bbox", p["bbox"], "rows", p["row_range"])
print("PORTRAIT row_extent")
for r in p["row_extent"]:
    print("  ", r)
print("PORTRAIT skin comps")
for f in p["skin_comps"]:
    print("  ", f)
g = out["ingame"]
print("INGAME size", g["size"], "fg_px", g["fg_px"], "bbox", g["bbox"], "rows", g["row_range"])
print("INGAME row_extent")
for r in g["row_extent"]:
    print("  ", r)
print("INGAME skin comps")
for f in g["skin_comps"]:
    print("  ", f)
print("PROBE_DONE", OUT)
