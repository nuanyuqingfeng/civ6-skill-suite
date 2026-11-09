import struct

import numpy as np

TEX = "Jinzhou_Jinhsi/Textures/"


def read_level0(path):
    with open(path, "rb") as f:
        data = f.read()
    h = data[:128]
    height = struct.unpack_from("<I", h, 12)[0]
    width = struct.unpack_from("<I", h, 16)[0]
    pf = struct.unpack_from("<I", h, 88)[0]
    bits = pf & 0xFF
    bpp = bits // 8
    n = width * height * bpp
    arr = np.frombuffer(data[128:128 + n], dtype=np.uint8)
    return width, height, bpp, arr.reshape(height, width, bpp)


def stat(name, path):
    w, h, bpp, a = read_level0(path)
    v = a[:, :, 0] if bpp == 1 else a[:, :, 3]
    total = v.size
    zero = int((v == 0).sum())
    full = int((v == 255).sum())
    mid = int(((v > 0) & (v < 255)).sum())
    print(name, "size", w, h, "bpp", bpp, "uniq", len(np.unique(v)),
          "zero", round(zero / total, 4), "full", round(full / total, 4),
          "mid", round(mid / total, 4), "mean", round(float(v.mean()), 2))


stat("SKIRT_SRC", TEX + "MI_R2T1JinxiMd10011Skirt_Opacity.dds")
stat("CLOTH_NOW", TEX + "JINHSI_LEADER_OPACITY_CLOTH.dds")
stat("BANGS_OP", TEX + "JINHSI_BANGS_OPACITY.dds")
