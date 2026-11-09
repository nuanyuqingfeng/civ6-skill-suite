# alpha_bind_verdict.py -- 判定一张基色贴图的 alpha 该不该当可见性（绑 Opacity）。
#
# 判据（2026-11-04 秧秧实测确立）：
#   真镂空的 alpha 必然同时具备「完全可见」与「完全不可见」两端：
#     full = frac(alpha >= 0.99)  -- 意图被看见的区域
#     hole = frac(alpha <  0.10)  -- 意图被镂空的区域
#   full >= 0.01 且 hole >= 0.01 -> BIND（绑 Alpha，裁剪阈值 0.3333）
#   其余                          -> SOLID（不绑，实心）
#
# 反面样本：T_R2T1YangyangMd10011Body_D.png 的 alpha 最大值只有 0.565、full=0.0000、
# hole=0.1417，它是一张皮肤明暗蒙版。只看低于阈值的像素占比会把它判成镂空，
# 绑上之后整块皮肤变半透明；本判据要求两端同时存在，因此判为 SOLID。
#
# 用法：
#   python alpha_bind_verdict.py <png|dds> [<png|dds> ...]
#   python alpha_bind_verdict.py --json <out.json> <图...>
#
# 退出码：
#   0 = 全部判为 SOLID
#   3 = 至少一张判为 BIND
#   1 = 参数错误

import json
import sys

import numpy as np
from PIL import Image

FULL_AT = 0.99
HOLE_AT = 0.10
MIN_FULL = 0.01
MIN_HOLE = 0.01


def stats(path):
    alpha = np.asarray(Image.open(path).convert("RGBA"))[:, :, 3]
    a = alpha.astype(np.float32) / 255.0
    return {
        "path": path,
        "max": float(a.max()),
        "mean": float(a.mean()),
        "full": float((a >= FULL_AT).mean()),
        "hole": float((a < HOLE_AT).mean()),
    }


def verdict(s):
    if s["full"] >= MIN_FULL and s["hole"] >= MIN_HOLE:
        return "BIND"
    return "SOLID"


def main(argv):
    out_json = None
    if len(argv) >= 2 and argv[0] == "--json":
        out_json = argv[1]
        argv = argv[2:]
    if not argv:
        print(__doc__)
        return 1
    rows = []
    for p in argv:
        s = stats(p)
        s["verdict"] = verdict(s)
        rows.append(s)
        print("%-52s max=%.3f full=%.4f hole=%.4f -> %s"
              % (p.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
                 s["max"], s["full"], s["hole"], s["verdict"]))
    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
    return 3 if any(r["verdict"] == "BIND" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
