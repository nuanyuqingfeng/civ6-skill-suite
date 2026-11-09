import argparse
import json
import sys

import numpy as np
from PIL import Image


def audit(path, level, stride):
    im = Image.open(path).convert("RGBA")
    arr = np.array(im)[::stride, ::stride]
    alpha = arr[:, :, 3]
    rgb = arr[:, :, :3].astype(np.int32)
    transparent = alpha <= level
    n = int(transparent.sum())
    if n == 0:
        return {"path": path, "transparent": 0, "colored": 0}
    sub = rgb[transparent]
    colored = int((sub.max(axis=1) > 0).sum())
    return {"path": path, "transparent": n, "colored": colored,
            "max_rgb": [int(x) for x in sub.max(axis=0)],
            "mean_rgb": [round(float(x), 1) for x in sub.mean(axis=0)]}


def main():
    parser = argparse.ArgumentParser(
        description="统计全透明像素里仍然带颜色的个数。引擎会照 RGB 绘制这些像素，"
                    "表现为贴片四周出现红边、黑边或亮色毛边。")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--level", type=int, default=0, help="视为透明的 alpha 上限，默认 0")
    parser.add_argument("--stride", type=int, default=1, help="采样步长，默认 1 即全量")
    parser.add_argument("--json")
    args = parser.parse_args()

    rows = []
    bad = []
    for path in args.paths:
        r = audit(path, args.level, args.stride)
        rows.append(r)
        if r["transparent"] == 0:
            print("%s 没有全透明像素" % path)
            continue
        print("%s 透明=%d 带色=%d 最大RGB=%s 均值RGB=%s" % (
            path, r["transparent"], r["colored"], r["max_rgb"], r["mean_rgb"]))
        if r["colored"] > 0:
            bad.append(path)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"rows": rows, "bad": bad, "ok": not bad}, fh, ensure_ascii=False, indent=1)
        print("JSON %s" % args.json)
    print("ALPHA_RGB_%s" % ("CLEAN" if not bad else "DIRTY"))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
