import numpy as np
from PIL import Image

ROOT = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame12"
a = np.asarray(Image.open(ROOT + "/01_bangs_new.png").convert("RGB")).astype(np.int32)
b = np.asarray(Image.open(ROOT + "/02_plate.png").convert("RGB")).astype(np.int32)
mask = (np.abs(a - b).sum(axis=2) > 64)

r, g, bl = a[:, :, 0], a[:, :, 1], a[:, :, 2]
lum = (r * 299 + g * 587 + bl * 114) // 1000
skin = (r > 150) & (g > 100) & (bl > 80) & (r - bl > 25) & (r - bl < 120) & (r >= g) & (g >= bl - 10) & mask

ys, xs = np.nonzero(skin)
print("SKIN_PX", len(ys))
print("SKIN_BBOX", int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))

# 逐行皮肤像素数，找出脸部主体行段
rows = skin.sum(axis=1)
seg = [(y, int(rows[y])) for y in range(400, 720, 10) if rows[y] > 0]
print("SKIN_ROWS", seg)

# 取皮肤像素最多的连续 80 行作为面部窗口
best_y, best_n = 0, -1
for y in range(400, 640):
    n = int(rows[y:y + 80].sum())
    if n > best_n:
        best_n, best_y = n, y
print("FACE_WINDOW", best_y, best_y + 80, "skin_px", best_n)

win = skin[best_y:best_y + 80, :]
v = lum[best_y:best_y + 80, :][win]
print("FACE_PX", int(win.sum()))
print("FACE_LUM_MEAN", round(float(v.mean()), 2))
print("FACE_RGB", [round(float(a[:, :, i][best_y:best_y + 80, :][win].mean()), 1) for i in range(3)])
print("DARK40", round(float((v < 40).mean()), 4))
print("DARK120", round(float((v < 120).mean()), 4))
print("FACE2_DONE")
