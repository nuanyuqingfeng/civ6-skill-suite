import numpy as np
from PIL import Image

P = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/portrait.png"
rgb = np.asarray(Image.open(P).convert("RGB")).astype(np.int32)
h, w, _ = rgb.shape
lum = (rgb[:, :, 0] * 299 + rgb[:, :, 1] * 587 + rgb[:, :, 2] * 114) // 1000
print("SIZE", w, h)

step_y = 40
step_x = 80
xs = list(range(0, w, step_x))
print("COLS", " ".join(str(x) for x in xs))
for y in range(0, h, step_y):
    row = [int(lum[y, x]) // 10 for x in xs]
    print("L%4d" % y, " ".join("%02d" % v for v in row))
