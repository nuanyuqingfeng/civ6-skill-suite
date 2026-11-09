from pathlib import Path

TEX = Path(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Textures")
NAMES = ("MI_R2T1JinxiMd10011Down_BaseColor.dds",
         "MI_R2T1JinxiMd10011Skirt_BaseColor.dds",
         "MI_R2T1JinxiMd10011Eye_BaseColor.dds")

for name in NAMES:
    p = TEX / name
    raw = bytearray(p.read_bytes())
    body = raw[128:]
    changed = 0
    for i in range(3, len(body), 4):
        if body[i] != 255:
            body[i] = 255
            changed += 1
    raw[128:] = body
    p.write_bytes(bytes(raw))
    print("ALPHA_BAKED %-46s bytes=%d changed=%d" % (name, len(raw), changed))
