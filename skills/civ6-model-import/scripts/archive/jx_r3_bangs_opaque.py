import hashlib

p = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi\Textures\JINHSI_BANGS_OPACITY.dds"
raw = bytearray(open(p, "rb").read())
head = raw[:128]
print("before", len(raw), hashlib.sha256(raw).hexdigest()[:16])
for i in range(128, len(raw)):
    raw[i] = 255
open(p, "wb").write(bytes(raw))
print("after", len(raw), hashlib.sha256(raw).hexdigest()[:16])
