import numpy as np
from PIL import Image
from scipy import ndimage

PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"


def skin(rgb):
    r = rgb[:, :, 0].astype(np.int32)
    g = rgb[:, :, 1].astype(np.int32)
    b = rgb[:, :, 2].astype(np.int32)
    return (r > 150) & (g > 100) & (b > 80) & (r - b > 25) & (r - b < 120) & (r >= g) & (g >= b - 10)


def fgmask(rgb):
    r = rgb[:, :, 0].astype(np.int32)
    g = rgb[:, :, 1].astype(np.int32)
    b = rgb[:, :, 2].astype(np.int32)
    lum = (r * 299 + g * 587 + b * 114) // 1000
    sat = rgb.max(axis=2).astype(np.int32) - rgb.min(axis=2).astype(np.int32)
    return (lum > 42) | (sat > 26)


rgb = np.asarray(Image.open(PORTRAIT).convert("RGB"))
h, w, _ = rgb.shape
fg = fgmask(rgb)
fg[:4, :] = False
fg[-4:, :] = False
fg[:, :4] = False
fg[:, -4:] = False
sk = skin(rgb)
print("SIZE", w, h, "fg", int(fg.sum()), "skin", int(sk.sum()))

for y in range(150, 620, 10):
    xs = np.nonzero(fg[y])[0]
    ss = int(sk[y].sum())
    if len(xs) == 0:
        print("Y", y, "fg 0")
        continue
    print("Y", y, "fg", len(xs), "x", int(xs[0]), int(xs[-1]), "skin", ss)
