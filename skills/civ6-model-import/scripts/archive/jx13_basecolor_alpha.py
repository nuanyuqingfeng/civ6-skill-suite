from pathlib import Path

import numpy as np
from PIL import Image

TEX = Path(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Textures")
FILES = [
    "MI_R2T1JinxiMd10011Down_BaseColor.dds",
    "MI_R2T1JinxiMd10011Face_BaseColor.dds",
    "MI_R2T1JinxiMd10011Skirt_BaseColor.dds",
    "MI_R2T1JinxiMd10011Bangs_BaseColor.dds",
    "MI_R2T1JinxiMd10011Hair_BaseColor.dds",
    "MI_R2T1JinxiMd10011Eye_BaseColor.dds",
]

for name in FILES:
    im = Image.open(TEX / name)
    a = np.asarray(im.convert("RGBA"))
    al = a[:, :, 3]
    rgb = a[:, :, :3].astype(np.int32)
    lum = (rgb[:, :, 0] * 299 + rgb[:, :, 1] * 587 + rgb[:, :, 2] * 114) // 1000
    print(name, "| alpha mean", round(float(al.mean()), 3), "uniq", len(np.unique(al)),
          "min", int(al.min()), "max", int(al.max()), "zero", round(float((al == 0).mean()), 4),
          "full", round(float((al == 255).mean()), 4), "mid", round(float(((al > 0) & (al < 255)).mean()), 4),
          "| lum mean", round(float(lum.mean()), 2), "near_black", int(((rgb < 30).all(axis=2)).sum()))
