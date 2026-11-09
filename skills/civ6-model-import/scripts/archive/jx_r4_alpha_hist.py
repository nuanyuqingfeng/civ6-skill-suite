from pathlib import Path
import numpy as np
from PIL import Image

base = Path(r"G:/Wuwa_3D_Assets/Characters/角色_Jinxi/converted/Client/Content/Aki/Character/Role/FemaleM/Jinxi/R2T1JinxiMd10011/Model")
for name in ("T_R2T1JinxiMd10011Down_D.png", "T_R2T1JinxiMd10011Skirt_D.png", "T_R2T1JinxiMd10011Bangs_D.png"):
    a = np.asarray(Image.open(base / name).convert("RGBA"))[:, :, 3]
    vals, counts = np.unique(a, return_counts=True)
    top = sorted(zip(counts, vals), reverse=True)[:6]
    print(name)
    print("   top alpha values:", [(int(v), round(c / a.size, 4)) for c, v in top])
    print("   ==0: %.4f  ==255: %.4f  <16: %.4f" % ((a == 0).mean(), (a == 255).mean(), (a < 16).mean()))
