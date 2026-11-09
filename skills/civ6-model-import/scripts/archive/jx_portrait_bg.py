import numpy as np
from PIL import Image
from scipy import ndimage

PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"

im = Image.open(PORTRAIT).convert("RGB")
rgb = np.asarray(im).astype(np.int32)
h, w, _ = rgb.shape

# 量化到 16 级，统计边框上出现的颜色，作为背景候选
q = (rgb // 16).astype(np.int32)
code = q[:, :, 0] * 256 + q[:, :, 1] * 16 + q[:, :, 2]
border = np.concatenate([code[0:6, :].ravel(), code[-6:, :].ravel(),
                         code[:, 0:6].ravel(), code[:, -6:].ravel()])
bgcodes = np.unique(border)
print("SIZE", w, h, "border_codes", len(bgcodes))

bg = np.isin(code, bgcodes)
subj = ~bg
# 去掉零散小点：只保留最大连通块
lab, n = ndimage.label(subj)
sizes = ndimage.sum(subj, lab, range(1, n + 1))
order = np.argsort(sizes)[::-1]
print("COMPS", n, "top", [int(sizes[o]) for o in order[:5]])
comp = lab == (order[0] + 1)
ys, xs = np.nonzero(comp)
print("SUBJ_BBOX", int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()), int(comp.sum()))

rows = comp.sum(axis=1)
nz = np.nonzero(rows > 0)[0]
print("SUBJ_ROWS", int(nz[0]), int(nz[-1]))
for y in range(int(nz[0]), int(nz[-1]) + 1, 12):
    xx = np.nonzero(comp[y])[0]
    if len(xx) == 0:
        print("R", y, 0)
        continue
    print("R", y, len(xx), int(xx[0]), int(xx[-1]))
