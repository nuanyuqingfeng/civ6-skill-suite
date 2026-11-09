from pathlib import Path

import numpy as np
from PIL import Image

SRC = Path(r"G:/Wuwa_3D_Assets/Characters/角色_Jinxi/converted/Client/Content/Aki/Character/Role/FemaleM/Jinxi/R2T1JinxiMd10011/Model")
FILES = [
    "T_R2T1JinxiMd10011Skirt_D.png",
    "T_R2T1JinxiMd10011Bangs_D.png",
    "T_R2T1JinxiMd10011Hair_D.png",
    "T_R2T1JinxiMd10011Down_D.png",
]

for name in FILES:
    im = Image.open(SRC / name)
    a = np.asarray(im.convert("RGBA"))
    al = a[:, :, 3]
    n = al.size
    print(name, im.mode, im.size, "| alpha mean", round(float(al.mean()), 3),
          "uniq", len(np.unique(al)), "min", int(al.min()), "max", int(al.max()),
          "zero", round(float((al == 0).mean()), 4), "full", round(float((al == 255).mean()), 4),
          "mid", round(float(((al > 0) & (al < 255)).mean()), 4))
