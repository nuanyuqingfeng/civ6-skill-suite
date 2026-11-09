import json
import numpy as np
from PIL import Image

PORTRAIT = r"D:/desktop/606fc927-6f6b-42b7-acb7-df73483b28f6.png"
INGAME = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/ingame9/70_jinhsi_face.png"
OUT = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/jx_hbr.json"


def luma(rgb):
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def rowcounts(mask):
    return mask.sum(axis=1)


def runs(vals, thresh):
    out = []
    start = None
    for i, v in enumerate(vals):
        if v >= thresh and start is None:
            start = i
        elif v < thresh and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(vals) - 1))
    return out


def profile(path, thresh, label):
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    m = luma(rgb) >= thresh
    rc = rowcounts(m)
    cols = m.sum(axis=0)
    nz = np.nonzero(rc)[0]
    print(label, "size", rgb.shape[1], rgb.shape[0], "thr", thresh,
          "rows", int(nz[0]), int(nz[-1]), "cols", int(np.nonzero(cols)[0][0]), int(np.nonzero(cols)[0][-1]))
    print(label, "runs>=8px", runs(rc, 8)[:12])
    return rc, m


def head_region(rc, label, lo, hi, step):
    parts = []
    for y in range(lo, hi, step):
        parts.append("%d:%d" % (y, int(rc[y])))
    print(label, "rows", " ".join(parts))


def main():
    rc_p, m_p = profile(PORTRAIT, 60, "PORTRAIT60")
    head_region(rc_p, "PORTRAIT60", 180, 340, 4)
    head_region(rc_p, "PORTRAIT60", 340, 480, 4)
    rc_i, m_i = profile(INGAME, 60, "INGAME60")
    head_region(rc_i, "INGAME60", 140, 320, 4)
    head_region(rc_i, "INGAME60", 320, 520, 4)


main()
