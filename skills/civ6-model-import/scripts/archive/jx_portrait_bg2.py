import numpy as np
from PIL import Image

P = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/portrait.png"

rgb = np.asarray(Image.open(P).convert("RGB")).astype(np.int32)
h, w, _ = rgb.shape
lum = (rgb[:, :, 0] * 299 + rgb[:, :, 1] * 587 + rgb[:, :, 2] * 114) // 1000

# 逐行背景模型：取左右各 60 列的中位色
side = np.concatenate([rgb[:, :60, :], rgb[:, -60:, :]], axis=1)
bg = np.median(side, axis=1).astype(np.int32)
d = np.abs(rgb - bg[:, None, :]).sum(axis=2)
print("BG_ROW_SAMPLE", [(y, tuple(bg[y])) for y in range(0, h, 150)])

for thr in (60, 90, 120):
    m = d > thr
    m[:4, :] = False
    m[-4:, :] = False
    m[:, :4] = False
    m[:, -4:] = False
    rows = m.sum(axis=1)
    nz = np.nonzero(rows > 8)[0]
    print("THR", thr, "px", int(m.sum()), "rows", int(nz[0]), int(nz[-1]))
    if thr == 90:
        prof = []
        for y in range(0, h, 8):
            xs = np.nonzero(m[y])[0]
            if len(xs) == 0:
                prof.append((y, 0, -1, -1))
            else:
                prof.append((y, int(len(xs)), int(xs[0]), int(xs[-1])))
        for t in prof:
            if t[1] > 0:
                print("P", t[0], t[1], t[2], t[3])
