import numpy as np
from PIL import Image

P = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/portrait.png"
im = Image.open(P).convert("RGB")
a = np.asarray(im).astype(np.int32)
h, w, _ = a.shape
print("SIZE", w, h)

BX, BY = 56, 56
nx = w // BX
ny = h // BY
print("GRID", nx, ny)
for by in range(ny):
    line = []
    for bx in range(nx):
        blk = a[by*BY:(by+1)*BY, bx*BX:(bx+1)*BX]
        r_ = blk[:, :, 0].mean()
        g_ = blk[:, :, 1].mean()
        b_ = blk[:, :, 2].mean()
        lum = 0.299*r_ + 0.587*g_ + 0.114*b_
        if lum < 25:
            c = "."
        elif r_ > g_ + 25 and r_ > b_ + 35 and lum > 90:
            c = "S"
        elif r_ > g_ + 15 and r_ > b_ + 15:
            c = "s"
        elif b_ > r_ + 25 and lum > 70:
            c = "B"
        elif lum > 200:
            c = "#"
        elif lum > 130:
            c = "o"
        elif lum > 70:
            c = "-"
        else:
            c = ","
        line.append(c)
    print("%4d %s" % (by*BY, "".join(line)))
