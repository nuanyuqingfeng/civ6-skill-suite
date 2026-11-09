import struct
from pathlib import Path

import numpy as np

DEN = Path(r"D:/desktop/mods-CIV6/others/Denia_Pack/Denia_Pack/Textures")
FILES = [
    "MI_R2T1DaniyaMd10011Cloth_Opacity.dds",
    "MI_R2T1DaniyaMd10011Down1_Opacity.dds",
    "MI_R2T1DaniyaMd10011Up01_Opacity.dds",
    "MI_R2T1DaniyaMd10011Hair01_Opacity.dds",
    "MI_R2T1DaniyaMd10011Bangs1_Opacity.dds",
]


def decode(path):
    raw = path.read_bytes()
    w = struct.unpack_from("<I", raw, 16)[0]
    h = struct.unpack_from("<I", raw, 12)[0]
    mips = struct.unpack_from("<I", raw, 28)[0]
    bits = struct.unpack_from("<I", raw, 88)[0]
    off = 128
    if raw[84:88] == b"DX10":
        off = 148
    bpp = bits // 8
    levels = []
    cw, ch = w, h
    for _ in range(mips):
        n = cw * ch * bpp
        a = np.frombuffer(raw[off:off + n], dtype=np.uint8)
        levels.append(a.reshape(ch, cw) if bpp == 1 else a.reshape(ch, cw, bpp))
        off += n
        cw = max(1, cw // 2)
        ch = max(1, ch // 2)
    return w, h, mips, bpp, levels, len(raw) - off


for name in FILES:
    w, h, mips, bpp, levels, tail = decode(DEN / name)
    v = levels[0].astype(np.uint8)
    n = v.size
    mids = [round(float((((m > 0) & (m < 255)).sum()) / m.size), 5) for m in levels]
    print(name, str(w) + "x" + str(h), "mips", mips, "bpp", bpp, "tail", tail,
          "| mean", round(float(v.mean()), 3), "uniq", len(np.unique(v)),
          "zero", round(float((v == 0).mean()), 4), "full", round(float((v == 255).mean()), 4),
          "mid", round(float(((v > 0) & (v < 255)).mean()), 4))
    print("   mip_mid", mids[:6])
