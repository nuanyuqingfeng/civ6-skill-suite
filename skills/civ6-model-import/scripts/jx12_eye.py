import numpy as np
from PIL import Image

ROOT = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame12"
a = np.asarray(Image.open(ROOT + "/01_bangs_new.png").convert("RGB")).astype(np.int32)
b = np.asarray(Image.open(ROOT + "/02_plate.png").convert("RGB")).astype(np.int32)
mask = np.abs(a - b).sum(axis=2) > 64

lum = (a[:, :, 0] * 299 + a[:, :, 1] * 587 + a[:, :, 2] * 114) // 1000

# 头部窗口：掩膜顶部向下 300 行，头心列 1180..1400
ys, xs = np.nonzero(mask)
top = int(ys.min())
head = mask[top:top + 320, 1180:1400]
print("HEAD_TOP", top, "HEAD_PX", int(head.sum()))

# 眼睛上沿：头部窗口里发色像素（暗色，亮度 < 110）逐行计数，找第一个峰值
for name, lo, hi in (("DARK", 0, 90), ("MID", 90, 150)):
    cnt = []
    for y in range(top, top + 320):
        row = mask[y, 1180:1400] & (lum[y, 1180:1400] >= lo) & (lum[y, 1180:1400] < hi)
        cnt.append(int(row.sum()))
    arr = np.asarray(cnt)
    if arr.max() > 0:
        peak = int(arr.argmax())
        print(name, "PEAK_ROW", top + peak, "PEAK", int(arr[peak]), "MEAN", round(float(arr.mean()), 2))

# 面部亮度：刘海下缘 515 到下巴之间，头心列
FACE_Y0, FACE_Y1 = 515, 760
FACE_X0, FACE_X1 = 1180, 1400
sub = mask[FACE_Y0:FACE_Y1, FACE_X0:FACE_X1]
v = lum[FACE_Y0:FACE_Y1, FACE_X0:FACE_X1][sub]
print("FACE_PX", int(sub.sum()))
print("FACE_LUM_MEAN", round(float(v.mean()), 2))
print("FACE_DARK40", round(float((v < 40).mean()), 4))
print("FACE_DARK120", round(float((v < 120).mean()), 4))
print("EYE_DONE")
