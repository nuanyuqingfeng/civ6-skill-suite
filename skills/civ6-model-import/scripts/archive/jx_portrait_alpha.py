import numpy as np
from PIL import Image

PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"

im = Image.open(PORTRAIT)
print("MODE", im.mode, im.size)
arr = np.asarray(im)
print("SHAPE", arr.shape)
a = arr[:, :, 3]
hist = np.bincount(a.ravel(), minlength=256)
nz = [(i, int(hist[i])) for i in range(256) if hist[i] > 0]
print("ALPHA_UNIQUE", len(nz))
print("ALPHA_HEAD", nz[:6], "TAIL", nz[-6:])
print("ALPHA_ZERO", int(hist[0]), "ALPHA_FULL", int(hist[255]))

rgb = arr[:, :, :3].astype(np.int32)
r = rgb[:, :, 0]
g = rgb[:, :, 1]
b = rgb[:, :, 2]
skin = (r > 150) & (g > 100) & (b > 80) & (r - b > 25) & (r - b < 120) & (r >= g) & (g >= b - 10)
print("SKIN_TOTAL", int(skin.sum()))
rows = skin.sum(axis=1)
top = [y for y in range(120, 700) if rows[y] >= 8]
print("SKIN_HEAD_ROWS", top[0] if top else -1, top[-1] if top else -1)
cols = skin.sum(axis=0)
sub = skin[top[0]:top[-1] + 1, :]
cs = sub.sum(axis=0)
xs = np.nonzero(cs > 0)[0]
print("FACE_COLS", int(xs[0]), int(xs[-1]), "width", int(xs[-1] - xs[0] + 1))
print("FACE_ROWS", top[0], top[-1], "height", top[-1] - top[0] + 1)
