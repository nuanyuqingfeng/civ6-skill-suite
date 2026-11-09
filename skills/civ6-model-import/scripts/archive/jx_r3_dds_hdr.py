import struct

def hdr(p):
    raw = open(p, "rb").read()
    h = struct.unpack("<31I", raw[4:128])
    return dict(size=len(raw), height=h[2], width=h[3], mips=h[6], pf=h[19:27], caps=h[27:31])

base = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Textures/"
for n in ("MI_R2T1JinxiMd10011Hair_Opacity.dds", "JINHSI_BANGS_OPACITY.dds", "JINHSI_LEADER_OPACITY_CLOTH.dds"):
    d = hdr(base + n)
    print(n, d["size"], d["width"], d["height"], "mips", d["mips"], "pf", d["pf"], "caps", d["caps"])
