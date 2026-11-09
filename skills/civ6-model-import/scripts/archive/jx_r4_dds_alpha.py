from pathlib import Path
import numpy as np
from PIL import Image

tex = Path(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Textures")
for p in sorted(tex.glob("MI_R2T1JinxiMd10011Down*.dds")) + sorted(tex.glob("MI_R2T1JinxiMd10011Skirt*.dds")):
    im = Image.open(p)
    a = np.asarray(im.convert("RGBA"))[:, :, 3]
    print("%-55s %s %dx%d alpha min=%d mean=%.1f frac<250=%.3f" % (
        p.name, im.mode, im.size[0], im.size[1], int(a.min()), float(a.mean()), float((a < 250).mean())))
