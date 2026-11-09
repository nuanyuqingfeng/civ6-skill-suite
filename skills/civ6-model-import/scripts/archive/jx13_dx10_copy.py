import struct
from pathlib import Path

ROOT = Path(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi")
TEX = ROOT / "Jinzhou_Jinhsi" / "Textures"
OUT = ROOT / "workspace" / "tmp" / "texchk"
FILES = [
    "JINHSI_LEADER_OPACITY_CLOTH.dds",
    "JINHSI_BANGS_OPACITY.dds",
    "MI_R2T1JinxiMd10011Hair_Opacity.dds",
]

OUT.mkdir(parents=True, exist_ok=True)
for name in FILES:
    raw = bytearray((TEX / name).read_bytes())
    body = raw[128:]
    hdr = bytearray(raw[:128])
    struct.pack_into("<I", hdr, 80, 0x4)
    hdr[84:88] = b"DX10"
    struct.pack_into("<I", hdr, 88, 0)
    struct.pack_into("<2I", hdr, 108, 0x1000, 0)
    dx10 = struct.pack("<5I", 61, 3, 0, 1, 0)
    (OUT / (name + ".dx10.dds")).write_bytes(bytes(hdr) + dx10 + bytes(body))
    print("WROTE", name + ".dx10.dds", len(hdr) + 20 + len(body))
