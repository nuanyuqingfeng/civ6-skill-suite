import json

import numpy as np
from PIL import Image
from scipy import ndimage

PORTRAIT = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/portrait.png"
INGAME = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame9/70_jinhsi_face.png"
INGAME_PLATE = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame9/72_no_leader_plate.png"
INGAME3 = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame3/09_jinhsi_same_camera.png"
INGAME3_PLATE = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame3/09_jinhsi_background_plate.png"


def skin_mask(rgb):
    r = rgb[:, :, 0].astype(np.int32)
    g = rgb[:, :, 1].astype(np.int32)
    b = rgb[:, :, 2].astype(np.int32)
    return (r > 140) & (g > 95) & (b > 75) & (r - b > 22) & (r - b < 130) & (r >= g) & (g >= b - 12)


def largest(mask):
    lab, n = ndimage.label(mask)
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    idx = int(np.argmax(sizes)) + 1
    return lab == idx, int(sizes[idx - 1])


def face_blob(rgb, y_lo, y_hi):
    sk = skin_mask(rgb)
    sk[:y_lo, :] = False
    sk[y_hi:, :] = False
    sk = ndimage.binary_opening(sk, np.ones((5, 5)))
    lab, n = ndimage.label(sk)
    if n == 0:
        return None
    sizes = ndimage.sum(sk, lab, range(1, n + 1))
    idx = int(np.argmax(sizes)) + 1
    ys, xs = np.nonzero(lab == idx)
    return {
        "px": int(sizes[idx - 1]),
        "y0": int(ys.min()), "y1": int(ys.max()),
        "x0": int(xs.min()), "x1": int(xs.max()),
        "cx": int(round(xs.mean())),
    }


def portrait():
    rgb = np.asarray(Image.open(PORTRAIT).convert("RGB")).astype(np.int32)
    h, w, _ = rgb.shape
    bg = np.median(np.concatenate([rgb[:, 0:30, :], rgb[:, w - 30:w, :]], axis=1), axis=1)
    d = np.sqrt(((rgb - bg[:, None, :]) ** 2).sum(axis=2))
    fg = d > 40
    comp, px = largest(fg)
    ys, xs = np.nonzero(comp)
    top, bottom = int(ys.min()), int(ys.max())
    face = face_blob(rgb, top, top + int((bottom - top) * 0.45))
    return {"img": "portrait", "w": w, "h": h, "mask_px": px,
            "top": top, "bottom": bottom, "span": bottom - top,
            "x0": int(xs.min()), "x1": int(xs.max()), "face": face}


def ingame(name, img_path, plate_path):
    a = np.asarray(Image.open(img_path).convert("RGB")).astype(np.int32)
    b = np.asarray(Image.open(plate_path).convert("RGB")).astype(np.int32)
    h, w, _ = a.shape
    d = np.abs(a - b).sum(axis=2)
    comp, px = largest(d > 64)
    ys, xs = np.nonzero(comp)
    top, bottom = int(ys.min()), int(ys.max())
    face = face_blob(a, top, top + int((bottom - top) * 0.45))
    return {"img": name, "w": w, "h": h, "mask_px": px,
            "top": top, "bottom": bottom, "span": bottom - top,
            "x0": int(xs.min()), "x1": int(xs.max()), "face": face}


out = [portrait(), ingame("ingame9_70", INGAME, INGAME_PLATE), ingame("ingame3_09", INGAME3, INGAME3_PLATE)]
for r in out:
    print("IMG", r["img"], r["w"], r["h"], "mask", r["mask_px"])
    print("  body top", r["top"], "bottom", r["bottom"], "span", r["span"], "x", r["x0"], r["x1"])
    f = r["face"]
    print("  face", f)
    if f is not None:
        head = f["y1"] - r["top"]
        body = r["bottom"] - f["y1"]
        print("  head_px", head, "body_px", body, "ratio body/head", round(body / head, 4),
              "heads_total", round(r["span"] / head, 4))
with open(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/hb_ratio.json", "w", encoding="utf-8") as fp:
    json.dump(out, fp, ensure_ascii=False, indent=1)
print("HB_DONE")
