import numpy as np
from PIL import Image
from scipy import ndimage

PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"
INGAME = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame9/70_jinhsi_face.png"
PLATE = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame9/72_no_leader_plate.png"


def load(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.int32)


def skin(rgb, rmin, rb_min):
    r = rgb[:, :, 0]
    g = rgb[:, :, 1]
    b = rgb[:, :, 2]
    return (r > rmin) & (g > 0.72 * r) & (b > 0.60 * r) & (r - b > rb_min) & (r - b < 130) & (r >= g) & (g >= b - 12)


def largest(mask):
    lab, n = ndimage.label(mask)
    if n == 0:
        return None
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    return lab == (int(np.argmax(sizes)) + 1)


def portrait():
    rgb = load(PORTRAIT)
    h, w, _ = rgb.shape
    ring = np.concatenate([rgb[0:6].reshape(-1, 3), rgb[-6:].reshape(-1, 3),
                           rgb[:, 0:6].reshape(-1, 3), rgb[:, -6:].reshape(-1, 3)])
    bg = np.median(ring, axis=0)
    dist = np.abs(rgb - bg).sum(axis=2)
    fg = dist > 90
    comp = largest(fg)
    ys, xs = np.nonzero(comp)
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    print("PORTRAIT bg", bg.astype(int).tolist(), "bbox", x0, y0, x1, y1, "h", y1 - y0)
    for thr in (0.60, 0.72, 0.80):
        for rb in (12, 20, 30):
            sk = skin(rgb, 150, rb) & comp
            rows = sk.sum(axis=1)
            band = np.nonzero(rows > 0)[0]
            if len(band) == 0:
                continue
            print("  skin thr=%.2f rb=%d px=%d rows %d..%d" % (thr, rb, int(sk.sum()), int(band[0]), int(band[-1])))
    # 头部区域逐行宽度，找颈部收窄
    print("  ROWWIDTH (largest comp)")
    for y in range(y0, min(y0 + 420, y1), 10):
        xs2 = np.nonzero(comp[y])[0]
        print("   y%4d w%4d x %4d..%4d" % (y, len(xs2), xs2.min(), xs2.max()))


def ingame():
    a = load(INGAME)
    b = load(PLATE)
    diff = np.abs(a - b).sum(axis=2) > 64
    ys, xs = np.nonzero(diff)
    print("INGAME model bbox", int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    for rmin, rb in ((150, 12), (170, 20), (190, 20)):
        sk = skin(a, rmin, rb) & diff
        rows = sk.sum(axis=1)
        print("INGAME skin rmin=%d rb=%d px=%d" % (rmin, rb, int(sk.sum())))
        for y in range(140, 520, 10):
            if rows[y] > 0:
                xs2 = np.nonzero(sk[y])[0]
                print("   y%4d n%4d x %4d..%4d" % (y, int(rows[y]), int(xs2.min()), int(xs2.max())))


portrait()
ingame()
