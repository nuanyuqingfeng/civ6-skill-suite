from pathlib import Path
import numpy as np
from PIL import Image

base = Path(r"G:/Wuwa_3D_Assets/Characters/角色_Jinxi/converted/Client/Content/Aki/Character/Role/FemaleM/Jinxi/R2T1JinxiMd10011/Model")
for p in sorted(base.glob("*Switch_D.png")) + sorted(base.glob("*_D.png")):
    im = Image.open(p)
    a = np.asarray(im.convert("RGBA"))[:, :, 3]
    print("%-45s mode=%-6s size=%dx%d alpha min=%3d mean=%6.1f frac<250=%.3f" % (
        p.name, im.mode, im.size[0], im.size[1], int(a.min()), float(a.mean()), float((a < 250).mean())))
