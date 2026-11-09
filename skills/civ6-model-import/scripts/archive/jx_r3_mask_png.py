import numpy as np
from PIL import Image
p = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi\Textures\JINHSI_BANGS_OPACITY.dds"
raw = open(p, "rb").read()
w = h = 1024
a = np.frombuffer(raw[128:128 + w * h], dtype=np.uint8).reshape(h, w)
Image.fromarray(np.where(a > 127, 255, 0).astype(np.uint8)).save(r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\tmp\bangs_mask.png")
print("saved", a.shape, (a > 127).mean())
