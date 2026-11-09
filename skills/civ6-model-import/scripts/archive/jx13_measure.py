import sys

import numpy as np
from PIL import Image
from scipy import ndimage


def load(path):
    img = np.asarray(Image.open(path).convert("RGB")).astype(np.int32)
    lum = (img[:, :, 0] * 299 + img[:, :, 1] * 587 + img[:, :, 2] * 114) // 1000
    return img, lum


def skin_mask(img):
    R, G, B = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    return (R > 200) & (G > 150) & (G < 215) & (B > 140) & (B < 205) & (R - B > 20)


def main(path):
    img, lum = load(path)
    h, w, _ = img.shape
    skin = skin_mask(img)
    skin[:, : int(w * 0.35)] = False
    skin[: int(h * 0.05)] = False
    print("IMG", w, h)
    print("LUM_MEAN", round(float(lum.mean()), 2))
    print("SKIN_PX", int(skin.sum()))

    labels, count = ndimage.label(skin)
    if count == 0:
        print("NO_SKIN")
        return
    sizes = ndimage.sum(skin, labels, range(1, count + 1))
    tops = ndimage.minimum(np.arange(h)[:, None] * np.ones((1, w), dtype=int), labels, range(1, count + 1))
    candidates = [i + 1 for i in range(count) if sizes[i] >= 40]
    if not candidates:
        print("NO_SKIN_BLOB")
        return
    biggest = min(candidates, key=lambda lab: tops[lab - 1])
    area = int(sizes[biggest - 1])
    skin = labels == biggest
    print("SKIN_MAIN px", area, "of", count, "components", "topmost_of", len(candidates))
    ys, xs = np.nonzero(skin)
    if len(xs) == 0:
        print("NO_SKIN")
        return

    col_hist = np.bincount(xs, minlength=w)
    center = int(col_hist.argmax())
    lo, hi = max(0, center - 15), min(w, center + 16)
    print("HEAD_COL_CENTER", center, "COLS", lo, hi)

    band = skin[:, lo:hi]
    rows = np.nonzero(band.any(axis=1))[0]
    face_top, face_bot = int(rows.min()), int(rows.max())
    print("FACE_ROWS", face_top, face_bot)

    head_h = face_bot - face_top + 1
    eye_zone = slice(face_top, face_top + max(1, head_h // 3))
    dark = lum < 90
    eye_rows = np.nonzero(dark[eye_zone, lo:hi].sum(axis=1) >= 3)[0]
    if len(eye_rows):
        eye_top = int(face_top + eye_rows.min())
        print("EYE_BAND", int(face_top + eye_rows.min()), int(face_top + eye_rows.max()))
    else:
        eye_top = None
        print("EYE_BAND none")

    hair_zone = slice(max(0, face_top - 40), face_top)
    hair = (lum > 170) & (img[:, :, 0] > 190) & (img[:, :, 2] > 170)
    hair_rows = np.nonzero(hair[hair_zone, lo:hi].sum(axis=1) >= 3)[0]
    if len(hair_rows):
        bangs_bot = int(max(0, face_top - 40) + hair_rows.max())
        print("BANGS_BOTTOM", bangs_bot)
    else:
        bangs_bot = None
        print("BANGS_BOTTOM none")

    if bangs_bot is not None and eye_top is not None:
        print("BANGS_MINUS_EYE", bangs_bot - eye_top)

    top = face_top + 1
    left = max(0, center - 25)
    win = lum[top:top + 50, left:left + 50]
    print("FACE50", "top", top, "left", left, "px", int(win.size),
          "mean", round(float(win.mean()), 2),
          "dark40", round(float((win < 40).mean()), 4),
          "dark120", round(float((win < 120).mean()), 4))

    face_win = lum[face_top:face_bot + 1, lo:hi]
    print("FACE_REGION px", int(face_win.size),
          "mean", round(float(face_win.mean()), 2),
          "dark40", round(float((face_win < 40).mean()), 4))


if __name__ == "__main__":
    main(sys.argv[1])
