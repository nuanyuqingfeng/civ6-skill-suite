#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""源图 alpha 通道语义审计：判断它到底是不是「透明度」。

鸣潮角色基色贴图（今汐 Skirt / Down / Bangs）的 alpha 常是材质 / 描线 mask，而非透明度：
没有 alpha=255、大量连续灰度值，alpha==0 的黑色区域在 RGB 通道里正是深色轮廓纹样。
若误当成「透明空白区」做补色 / 置零，会把纹路抹亮成碎裂蚀空。

用法：
  python alpha_semantic_audit.py <png> [<png> ...]

退出码：
  0 = alpha-like，可继续走常规落色流程
  2 = 判定为非透明度 mask（禁止对 alpha==0 做任何 RGB 改动）
  1 = 参数错误
"""
import sys
import numpy as np
from PIL import Image


def audit(path):
    a = np.asarray(Image.open(path).convert("RGBA"))[:, :, 3]
    zero = float((a == 0).mean())
    full = float((a == 255).mean())
    mid = float(((a > 0) & (a < 255)).mean())
    uniq = int(len(np.unique(a)))
    median = int(np.median(a))
    # 判据：完全没有（或极少）完全不透明像素 + alpha 呈连续灰度（唯一值多）
    mask_like = (full < 0.005) and (uniq > 50)
    print("%-58s zero=%.4f full=%.4f mid=%.4f uniq=%4d median=%3d -> %s" %
          (path, zero, full, mid, uniq, median,
           "NON-ALPHA MASK (禁止补色/置零)" if mask_like else "alpha-like"))
    return mask_like


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    flags = [audit(p) for p in sys.argv[1:]]
    sys.exit(2 if any(flags) else 0)
