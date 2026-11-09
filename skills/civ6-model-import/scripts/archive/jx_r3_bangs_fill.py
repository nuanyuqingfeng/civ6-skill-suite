import struct
import numpy as np

SRC = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Textures/JINHSI_BANGS_OPACITY.dds"
DST = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/r3render/bangs_fill.dds"
LIMIT = 96

raw = open(SRC, "rb").read()
header = raw[:128]
w = h = 1024
a = np.frombuffer(raw[128:128 + w * h], dtype=np.uint8).reshape(h, w)
opaque = a > 127
filled = opaque.copy()
for y in range(h):
    row = opaque[y]
    xs = np.where(row)[0]
    if xs.size < 2:
        continue
    for i in range(xs.size - 1):
        x0, x1 = xs[i], xs[i + 1]
        if x1 - x0 > 1 and (x1 - x0 - 1) <= LIMIT:
            filled[y, x0 + 1:x1] = True

levels = []
cur = filled
while True:
    levels.append(cur)
    if cur.shape[0] == 1 and cur.shape[1] == 1:
        break
    hh, ww = cur.shape
    nh, nw = max(1, hh // 2), max(1, ww // 2)
    blocks = cur[: nh * 2, : nw * 2].reshape(nh, 2, nw, 2).astype(np.float32).mean(axis=(1, 3))
    cur = blocks >= 0.5

out = bytearray(header)
for lv in levels:
    out += np.where(lv, 255, 0).astype(np.uint8).tobytes()
open(DST, "wb").write(bytes(out))
print("levels", len(levels), "bytes", len(out), "orig", len(raw))
print("opaque_before", round(float(opaque.mean()), 4), "after", round(float(filled.mean()), 4))
