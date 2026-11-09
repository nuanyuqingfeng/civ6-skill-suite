import json
import sys

import numpy as np
from PIL import Image
from scipy import ndimage


def skin(rgb):
    r = rgb[:, :, 0].astype(np.int32)
    g = rgb[:, :, 1].astype(np.int32)
    b = rgb[:, :, 2].astype(np.int32)
    return (r > 150) & (g > 100) & (b > 80) & (r - b > 25) & (r - b < 120) & (r >= g) & (g >= b - 10)


def face_blob(rgb):
    sk = skin(rgb)
    lab, n = ndimage.label(sk)
    sizes = ndimage.sum(sk, lab, range(1, n + 1))
    best = None
    for i in range(n):
        if sizes[i] < 3000:
            continue
        comp = lab == (i + 1)
        ys, xs = np.nonzero(comp)
        w = xs.max() - xs.min() + 1
        h = ys.max() - ys.min() + 1
        if w < 80 or h < 80:
            continue
        ar = w / h
        if ar < 0.65 or ar > 1.55:
            continue
        score = sizes[i] * (1.0 - abs(ar - 1.0))
        if best is None or score > best[0]:
            best = (score, int(sizes[i]), int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))
    return best


def rowbg_fg(rgb):
    f = rgb.astype(np.float64)
    lum = (f[:, :, 0] * 299.0 + f[:, :, 1] * 587.0 + f[:, :, 2] * 114.0) / 1000.0
    bg = np.median(f[:, 0:120, :], axis=1)
    diff = np.abs(f - bg[:, None, :]).sum(axis=2)
    fg = diff > 45
    return fg, lum


def measure(name, path):
    rgb = np.asarray(Image.open(path).convert("RGB"))
    h, w, _ = rgb.shape
    fb = face_blob(rgb)
    fg, lum = rowbg_fg(rgb)
    print("IMG", name, w, h, "face", fb)
    if fb is None:
        return None
    _, px, x0, x1, y0, y1 = fb
    cx = (x0 + x1) // 2
    half = max(60, int((x1 - x0) * 0.9))
    a = max(0, cx - half)
    b = min(w, cx + half + 1)
    win = fg[:, a:b]
    rows = win.sum(axis=1)
    top = None
    for y in range(h):
        if rows[y] >= 3:
            top = y
            break
    bottom = None
    for y in range(h - 1, -1, -1):
        if rows[y] >= 3:
            bottom = y
            break
    print("WINDOW", a, b, "top", top, "chin", y1, "bottom", bottom)
    print("HEAD_TOP_TO_CHIN", y1 - top, "CHIN_TO_FOOT", bottom - y1, "TOTAL", bottom - top)
    print("HEADS_TOTAL", round((bottom - top) / (y1 - top), 4))
    print("HEADS_FACE_ONLY", round((bottom - top) / (y1 - y0 + 1), 4))
    return {
        "name": name, "w": w, "h": h,
        "face": [x0, x1, y0, y1],
        "top": int(top), "chin": int(y1), "bottom": int(bottom),
        "head_px": int(y1 - top), "body_px": int(bottom - y1),
        "heads": round((bottom - top) / (y1 - top), 4),
    }


out = []
for name, path in (
    ("portrait", r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/portrait.png"),
    ("ingame3_09", r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame3/09_jinhsi_same_camera.png"),
    ("ingame9_70", r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame9/70_jinhsi_face.png"),
):
    r = measure(name, path)
    if r is not None:
        out.append(r)

with open(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/hb2.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("HB2_DONE")
