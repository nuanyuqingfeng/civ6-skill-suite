import struct
from pathlib import Path

TEX = Path(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Textures")
ref = TEX / "JINHSI_LEADER_OPACITY_CLOTH.dds"
raw = ref.read_bytes()
h = raw[:128]
print("REF size=%d w=%d h=%d mips=%d flags=0x%08x pf_flags=0x%08x fourcc=%r bits=%d masks=%s" % (
    len(raw), struct.unpack_from("<I", h, 16)[0], struct.unpack_from("<I", h, 12)[0],
    struct.unpack_from("<I", h, 28)[0], struct.unpack_from("<I", h, 8)[0],
    struct.unpack_from("<I", h, 80)[0], h[84:88], struct.unpack_from("<I", h, 88)[0],
    [hex(struct.unpack_from("<I", h, o)[0]) for o in (92, 96, 100, 104)]))
print("HEADER_HEX", h.hex())
