import bpy
import os
import numpy as np

TEXDIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi\Textures"

def stats(name):
    path = os.path.join(TEXDIR, name)
    img = bpy.data.images.load(path)
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    arr = buf.reshape(h, w, 4)
    a = arr[:, :, 3]
    soft = float(((a > 0.05) & (a < 0.95)).mean())
    print("MASK", name, "size", w, h, "min", round(float(a.min()), 4), "mean", round(float(a.mean()), 4),
          "max", round(float(a.max()), 4), "frac_zero", round(float((a < 0.05).mean()), 4),
          "frac_soft", round(soft, 4), "frac_full", round(float((a > 0.95).mean()), 4))
    bpy.data.images.remove(img)

for n in ["JINHSI_LEADER_OPACITY_CLOTH.dds", "JINHSI_BANGS_OPACITY.dds",
          "MI_R2T1JinxiMd10011Hair_Opacity.dds", "MI_6XingStar_Opacity.dds",
          "MI_R2T1JinxiMd10011Skirt_Opacity.dds"]:
    stats(n)
print("MASK_OK")
