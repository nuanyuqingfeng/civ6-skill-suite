import numpy as np
from PIL import Image
from scipy import ndimage

P = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"
im = Image.open(P).convert("RGB")
rgb = np.asarray(im).astype(np.int32)
h, w, _ = rgb.shape
r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
lum = (r * 299 + g * 587 + b * 114) // 1000

def comps(mask, top, tag):
    lab, n = ndimage.label(mask)
    if n == 0:
        print(tag, "none")
        return
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    order = np.argsort(sizes)[::-1]
    print(tag, "n", n)
    for oi in order[:top]:
        ys, xs = np.nonzero(lab == (oi + 1))
        print("  px %d y %d..%d x %d..%d" % (int(sizes[oi]), ys.min(), ys.max(), xs.min(), xs.max()))

# 宽松肤色：红略高于绿、绿略高于蓝、亮度高
skin = (r > 165) & (g > 130) & (b > 115) & (r >= g) & (g >= b - 8) & (r - b >= 8) & (r - b <= 110) & (lum > 150)
print("SKIN_BROAD px", int(skin.sum()))
comps(skin, 6, "SKIN_BROAD_COMPS")

# 头发：暗而低饱和？先看整体色调分布
print("LUM_MEAN", float(lum.mean()))
for lo in range(0, 260, 20):
    m = (lum >= lo) & (lum < lo + 20)
    print("LUMBAND %d %d" % (lo, int(m.sum())))
