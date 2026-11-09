import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

TEX = Path(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Textures")
TARGETS = ("JINHSI_BANGS_OPACITY.dds", "JINHSI_LEADER_OPACITY_CLOTH.dds")
RADIUS = 1.6


def load(path):
    raw = path.read_bytes()
    header = raw[:128]
    w = struct.unpack_from("<I", header, 16)[0]
    h = struct.unpack_from("<I", header, 12)[0]
    mips = struct.unpack_from("<I", header, 28)[0]
    body = raw[128:]
    level = np.frombuffer(body[: w * h], dtype=np.uint8).reshape(h, w)
    return header, level, mips, len(body)


for name in TARGETS:
    p = TEX / name
    header, lvl0, mips, total = load(p)
    mask = (lvl0 > 127).astype(np.float32)
    soft = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(RADIUS)), dtype=np.float32) / 255.0
    core = mask > 0.5
    feathered = np.where(core, np.maximum(soft, 0.55), soft * 0.85)
    feathered = np.clip(feathered, 0.0, 1.0)

    levels = [(feathered * 255).astype(np.uint8)]
    cur = feathered
    while len(levels) < mips:
        hh, ww = cur.shape
        nh, nw = max(1, hh // 2), max(1, ww // 2)
        blocks = cur[: nh * 2, : nw * 2].reshape(nh, 2, nw, 2).mean(axis=(1, 3))
        cur = blocks
        levels.append((cur * 255).astype(np.uint8))

    out = bytearray(header)
    for lv in levels:
        out += lv.tobytes()
    p.write_bytes(bytes(out))
    soft_frac = float(((levels[0] > 8) & (levels[0] < 247)).mean())
    print("FEATHERED %-34s bytes=%d levels=%d soft_px=%.4f" % (name, len(out), len(levels), soft_frac))
