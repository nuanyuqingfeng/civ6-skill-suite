import numpy as np
from PIL import Image
from scipy import ndimage

TEX = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Textures/"
ROOT = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame12"


def dds_level0(path):
    with open(path, "rb") as f:
        raw = f.read()
    hdr = raw[:128]
    h, w = int.from_bytes(hdr[12:16], "little"), int.from_bytes(hdr[16:20], "little")
    bits = int.from_bytes(hdr[88:92], "little")
    bpp = bits // 8
    n = w * h * bpp
    a = np.frombuffer(raw[128:128 + n], dtype=np.uint8).reshape(h, w, bpp)
    return w, h, bpp, a


w, h, bpp, cloth = dds_level0(TEX + "JINHSI_LEADER_OPACITY_CLOTH.dds")
v = cloth[:, :, 0].astype(np.int32)
uniq = len(np.unique(v))
mid = int(((v > 8) & (v < 247)).sum())
print("CLOTH", w, h, "bpp", bpp, "uniq", uniq, "mid_frac", round(mid / float(v.size), 4))
edges = ndimage.sobel(v.astype(np.float32), axis=0)
print("CLOTH_STEP_MAX", int(np.abs(edges).max()))

img = np.asarray(Image.open(ROOT + "/01_bangs_new.png").convert("RGB")).astype(np.int32)
plate = np.asarray(Image.open(ROOT + "/02_plate.png").convert("RGB")).astype(np.int32)
diff = np.abs(img - plate).sum(axis=2)
mask = diff > 64
# 背景板本身像素值（无领袖处的场景色）作为“背景色”
bg_rows = plate[900:959, 1000:1100].reshape(-1, 3)
bg = bg_rows.mean(axis=0)
print("BG_MEAN", [round(float(x), 1) for x in bg])
d2 = np.abs(img - bg.reshape(1, 1, 3)).sum(axis=2)
bleed = (d2 < 20) & mask
print("BLEED_PX", int(bleed.sum()))
ys, xs = np.nonzero(bleed)
if len(ys):
    print("BLEED_BBOX", int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
print("SEAM_DONE")
