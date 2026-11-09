from PIL import Image
import numpy as np

FILES = [
    "Jinzhou_Jinhsi/Textures/MI_R2T1JinxiMd10011Bangs_BaseColor.dds",
    "Jinzhou_Jinhsi/Textures/MI_R2T1JinxiMd10011Bangs_Opacity.dds",
    "Jinzhou_Jinhsi/Textures/JINHSI_BANGS_OPACITY.dds",
    "Jinzhou_Jinhsi/Textures/JINHSI_LEADER_OPACITY_CLOTH.dds",
    "Jinzhou_Jinhsi/Textures/MI_R2T1JinxiMd10011Skirt_Opacity.dds",
]
for f in FILES:
    im = Image.open(f)
    print(f.split("/")[-1], im.mode, im.size, im.format)
    a = np.asarray(im.convert("RGBA"))
    print("   alpha uniq", np.unique(a[:, :, 3])[:8], "n", len(np.unique(a[:, :, 3])))
    print("   rgb mean", a[:, :, :3].mean(axis=(0, 1)).round(2))
