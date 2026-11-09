import json
import sys

import numpy as np
from PIL import Image

# 立绘与局内图各量一次「头顶到下巴」「下巴到脚」的像素比
PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"
INGAME = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame9/70_jinhsi_face.png"


def skin_mask(rgb):
    r = rgb[:, :, 0].astype(np.int32)
    g = rgb[:, :, 1].astype(np.int32)
    b = rgb[:, :, 2].astype(np.int32)
    # 皮肤：红通道占优、绿介于红蓝之间、亮度足够
    m = (r > 150) & (g > 100) & (b > 80) & (r - b > 25) & (r - b < 120) & (r >= g) & (g >= b - 10)
    return m


def report(name, path):
    im = Image.open(path).convert("RGB")
    rgb = np.asarray(im)
    h, w, _ = rgb.shape
    sk = skin_mask(rgb)
    print("IMG", name, w, h, "skin_px", int(sk.sum()))
    rows = sk.sum(axis=1)
    # 每行皮肤像素数，取整行打印会太长，按 10 行聚合
    band = 10
    agg = [int(rows[i:i + band].sum()) for i in range(0, h, band)]
    print("ROWSKIN", " ".join("%d:%d" % (i * band, v) for i, v in enumerate(agg) if v > 0))
    return w, h, sk


def main():
    for name, path in (("portrait", PORTRAIT), ("ingame", INGAME)):
        report(name, path)


main()