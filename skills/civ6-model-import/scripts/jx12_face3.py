import numpy as np
from PIL import Image

ROOT = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame12"
a = np.asarray(Image.open(ROOT + "/01_bangs_new.png").convert("RGB")).astype(np.int32)
b = np.asarray(Image.open(ROOT + "/02_plate.png").convert("RGB")).astype(np.int32)
mask = (np.abs(a - b).sum(axis=2) > 64)
lum = (a[:, :, 0] * 299 + a[:, :, 1] * 587 + a[:, :, 2] * 114) // 1000

# 头心列与头顶点（已知：BBOX 968 348 1611 959，头心列 1289）
CX, TOP, BANGS_ROW = 1289, 348, 515

def stat(y0, y1, x0, x1, tag):
    m = mask[y0:y1, x0:x1]
    v = lum[y0:y1, x0:x1]
    if m.sum() == 0:
        print(tag, "EMPTY")
        return
    vv = v[m]
    print(tag, "px", int(m.sum()), "mean", round(float(vv.mean()), 2),
          "rgb", [round(float(a[y0:y1, x0:x1, c][m].mean()), 1) for c in range(3)],
          "dark40", round(float((vv < 40).mean()), 4),
          "dark120", round(float((vv < 120).mean()), 4))

# ingame9 口径换算：50x50 窗口，起点为刘海下缘下方 1 行
stat(BANGS_ROW + 1, BANGS_ROW + 51, CX - 25, CX + 25, "FACE50x50")
# 再给一个 100x100 看稳定性
stat(BANGS_ROW + 1, BANGS_ROW + 101, CX - 50, CX + 50, "FACE100x100")
# 眼睛/下半脸（不含颈）
for y in range(510, 700, 20):
    stat(y, y + 20, CX - 50, CX + 50, "ROW%d" % y)
print("DONE")
