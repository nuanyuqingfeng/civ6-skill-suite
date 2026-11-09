from pathlib import Path

import numpy as np
from PIL import Image

TEX = Path(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Textures")
for name in ["JINHSI_LEADER_OPACITY_OPAQUE.dds", "JINHSI_LEADER_OPACITY_FAINT.dds"]:
    im = Image.open(TEX / name)
    a = np.asarray(im.convert("L"))
    print(name, im.mode, im.size, "| mean", round(float(a.mean()), 3), "uniq", len(np.unique(a)),
          "min", int(a.min()), "max", int(a.max()))
