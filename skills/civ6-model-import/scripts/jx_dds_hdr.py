import struct
import sys

FILES = [
    "Jinzhou_Jinhsi/Textures/JINHSI_LEADER_OPACITY_CLOTH.dds",
    "Jinzhou_Jinhsi/Textures/JINHSI_BANGS_OPACITY.dds",
    "Jinzhou_Jinhsi/Textures/MI_R2T1JinxiMd10011Bangs_Opacity.dds",
    "Jinzhou_Jinhsi/Textures/MI_R2T1JinxiMd10011Bangs_BaseColor.dds",
    "Jinzhou_Jinhsi/Textures/MI_R2T1JinxiMd10011Skirt_Opacity.dds",
]

for path in FILES:
    d = open(path, "rb").read()
    magic = d[0:4]
    size, flags, h, w, pitch, depth, mips = struct.unpack("<7I", d[4:32])
    pfsize, pfflags, fourcc, rgbbits, rmask, gmask, bmask, amask = struct.unpack("<2I4s5I", d[76:108])
    caps, caps2 = struct.unpack("<2I", d[108:116])
    print(path.split("/")[-1])
    print("  magic", magic, "size", size, "flags", hex(flags), "w", w, "h", h, "pitch", pitch, "depth", depth, "mips", mips)
    print("  pf", pfsize, hex(pfflags), fourcc, "bits", rgbbits,
          "masks", hex(rmask), hex(gmask), hex(bmask), hex(amask), "caps", hex(caps), hex(caps2))
    print("  bytes", len(d))
    if fourcc == b"DX10":
        dxgi, dim, misc, arr, misc2 = struct.unpack("<5I", d[128:148])
        print("  DX10 dxgi", dxgi, "dim", dim, "misc", hex(misc), "array", arr, "misc2", hex(misc2))
