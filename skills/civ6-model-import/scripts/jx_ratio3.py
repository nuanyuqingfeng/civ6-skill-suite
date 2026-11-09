import numpy as np
from PIL import Image

PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"
INGAME = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame3/09_jinhsi_same_camera.png"
PLATE = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame3/09_jinhsi_background_plate.png"


def lum(rgb):
    r = rgb[:, :, 0].astype(np.int32)
    g = rgb[:, :, 1].astype(np.int32)
    b = rgb[:, :, 2].astype(np.int32)
    return (r * 299 + g * 587 + b * 114) // 1000


def structure(counts, thr_frac, tag):
    n = len(counts)
    mx = int(counts.max())
    live = counts > thr_frac * mx
    ys = np.nonzero(live)[0]
    top = int(ys[0])
    bot = int(ys[-1])
    # 肩线：头顶下方首个宽度达到最大值 45% 的行
    shoulder = None
    for y in range(top + 5, bot):
        if counts[y] > 0.45 * mx:
            shoulder = y
            break
    print(tag, "max_width", mx, "top", top, "bottom", bot, "span", bot - top, "shoulder", shoulder)
    return mx, top, bot, shoulder, live


def portrait():
    rgb = np.asarray(Image.open(PORTRAIT).convert("RGB"))
    l = lum(rgb)
    for thr in (70, 90, 110, 130, 150):
        m = l > thr
        counts = m.sum(axis=1)
        mx, top, bot, sh, live = structure(counts, 0.05, "PORTRAIT thr%d" % thr)
        if sh is None:
            continue
        head = sh - top
        chin = sh - int(round(0.08 * head))
        body = bot - chin
        print("  head", head, "chin", chin, "body", body, "ratio_h2b", round(head / body, 4),
              "heads", round((bot - top) / head, 3))
    # 逐行宽度在头部区间的原始值，便于核对肩线位置
    m = l > 110
    counts = m.sum(axis=1)
    print("PORTRAIT WIDTH 110 y:count", " ".join("%d:%d" % (y, int(counts[y])) for y in range(150, 560, 20)))


def ingame():
    a = np.asarray(Image.open(INGAME).convert("RGB")).astype(np.int32)
    b = np.asarray(Image.open(PLATE).convert("RGB")).astype(np.int32)
    d = np.abs(a - b).sum(axis=2)
    m = d > 64
    m[:, :900] = False
    counts = m.sum(axis=1)
    mx, top, bot, sh, live = structure(counts, 0.05, "INGAME mask")
    head = sh - top
    chin = sh - int(round(0.08 * head))
    body = bot - chin
    print("  head", head, "chin", chin, "body", body, "ratio_h2b", round(head / body, 4),
          "heads", round((bot - top) / head, 3))
    print("INGAME WIDTH y:count", " ".join("%d:%d" % (y, int(counts[y])) for y in range(60, 400, 10)))


portrait()
ingame()