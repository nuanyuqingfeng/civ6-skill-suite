import struct
from pathlib import Path

tex = Path(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Textures")
for name in ("MI_R2T1JinxiMd10011Down_BaseColor.dds", "MI_R2T1JinxiMd10011Skirt_BaseColor.dds", "MI_R2T1JinxiMd10011Eye_BaseColor.dds"):
    raw = (tex / name).read_bytes()
    h = raw[:128]
    height = struct.unpack_from("<I", h, 12)[0]
    width = struct.unpack_from("<I", h, 16)[0]
    mips = struct.unpack_from("<I", h, 28)[0]
    fourcc = h[84:88]
    bits = struct.unpack_from("<I", h, 88)[0]
    print("%-48s %dx%d mips=%d fourcc=%r bits=%d bytes=%d" % (name, width, height, mips, fourcc, bits, len(raw)))
