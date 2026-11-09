import json

import numpy as np
from PIL import Image
from scipy import ndimage

PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"
INGAME = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame9/70_jinhsi_face.png"
PLATE = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame9/72_no_leader_plate.png"


def skin_mask(rgb):
    r = rgb[:, :, 0].astype(np.int32)
    g = rgb[:, :, 1].astype(np.int32)
    b = rgb[:, :, 2].astype(np.int32)
    return (r > 150) & (g > 100) & (b > 80) & (r - b > 25) & (r - b < 120) & (r >= g) & (g >= b - 10)


def biggest(mask, min_px):
    lab, n = ndimage.label(mask)
    if n == 0:
        return None, 0, 0
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    idx = int(np.argmax(sizes)) + 1
    comp = lab == idx
    return comp, int(sizes[idx - 1]), n


def face_comp(rgb):
    sk = skin_mask(rgb)
    lab, n = ndimage.label(sk)
    sizes = ndimage.sum(sk, lab, range(1, n + 1))
    order = np.argsort(sizes)[::-1]
    rows = []
    for oi in order[:8]:
        comp = lab == (oi + 1)
        ys, xs = np.nonzero(comp)
        rows.append({
            "px": int(sizes[oi]),
            "y0": int(ys.min()), "y1": int(ys.max()),
            "x0": int(xs.min()), "x1": int(xs.max()),
        })
    return rows


def portrait():
    im = Image.open(PORTRAIT).convert("RGB")
    rgb = np.asarray(im)
    h, w, _ = rgb.shape
    lum = (rgb[:, :, 0].astype(np.int32) * 299 + rgb[:, :, 1].astype(np.int32) * 587 + rgb[:, :, 2].astype(np.int32) * 114) // 1000
    fg = lum > 45
    # 去掉四边各 3 像素的边框
    fg[:3, :] = False
    fg[-3:, :] = False
    fg[:, :3] = False
    fg[:, -3:] = False
    comp, px, n = biggest(fg, 0)
    ys, xs = np.nonzero(comp)
    print("PORTRAIT size", w, h, "comps", n, "biggest_px", px)
    print("PORTRAIT bbox", int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    faces = face_comp(rgb)
    print("PORTRAIT skin comps top8")
    for f in faces:
        print("  ", f)
    return rgb, comp, faces


def ingame():
    a = np.asarray(Image.open(INGAME).convert("RGB")).astype(np.int32)
    b = np.asarray(Image.open(PLATE).convert("RGB")).astype(np.int32)
    d = np.abs(a - b).sum(axis=2)
    m = d > 64
    print("INGAME diff px", int(m.sum()))
    ys, xs = np.nonzero(m)
    print("INGAME model bbox", int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    faces = face_comp(a.astype(np.uint8))
    print("INGAME skin comps top8")
    for f in faces:
        print("  ", f)
    return a, m, faces


portrait()
ingame()
