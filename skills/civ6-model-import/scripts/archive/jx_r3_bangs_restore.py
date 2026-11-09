import numpy as np
from PIL import Image

dds = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi\Textures\JINHSI_BANGS_OPACITY.dds"
png = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\tmp\bangs_mask.png"
raw = open(dds, "rb").read()
header = raw[:128]
mask = (np.asarray(Image.open(png).convert("L")) > 127)
print("mask", mask.shape, mask.mean())
levels = []
cur = mask
while True:
    levels.append(cur)
    if cur.shape[0] == 1 and cur.shape[1] == 1:
        break
    h, w = cur.shape
    nh, nw = max(1, h // 2), max(1, w // 2)
    blocks = cur[: nh * 2, : nw * 2].reshape(nh, 2, nw, 2).astype(np.float32).mean(axis=(1, 3))
    cur = blocks >= 0.5
out = bytearray(header)
for lv in levels:
    out += np.where(lv, 255, 0).astype(np.uint8).tobytes()
print("levels", len(levels), "bytes", len(out), "orig", len(raw))
assert len(out) == len(raw), (len(out), len(raw))
open(dds, "wb").write(bytes(out))
print("mip0 opaque", float((levels[0] > 0).mean()))
