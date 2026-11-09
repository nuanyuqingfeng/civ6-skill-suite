"""领袖基色镂空落色审计：按三态判据检查"补色有没有把别的面料颜色灌进来"。

用法（需要 Blender，因为要读 PNG 的 alpha）：

    "<Blender>" -b --python scripts/probes/hole_fill_audit.py -- \
        --src <源图.png> --dds <成品.dds> [--tol 25] [--stats-only]

输出四段：
  1. 三个态的面积占比：pad（足迹外近似）、岛内洞、实心；
  2. 每个岛内洞一行：面积、最长邻块色、次长邻块色、当前落色、偏差、判定；
  3. 汇总：跨色洞数、超差洞数；
  4. 末行 `AUDIT_OK` / `AUDIT_FAIL`（退出码同步）。

判据来源：references/leader-pipeline.md §5.4、references/texture-rules-matrix.md。
"""
import argparse
import struct
import sys
from collections import deque

import bpy
import numpy as np

MIN_AREA = 100          # 小于此面积的洞不参与判定（多为抗锯齿碎点）
CROSS_DELTA = 60.0      # 最长/次长邻块亮度差超过此值 → 跨色洞，禁单色
DARK_RING = 70.0        # 外环中位亮度低于此值 → 暗壳
DARK_CAP = 20.0         # 暗壳落色亮度上限 = 外环中位 + 此值


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(description="领袖基色镂空落色审计")
    p.add_argument("--src", required=True, help="源图（带 alpha 的 png）")
    p.add_argument("--dds", required=True, help="成品基色 dds（未压缩 RGBA8）")
    p.add_argument("--tol", type=float, default=25.0, help="落色与最长邻块色的允许偏差")
    p.add_argument("--expect", choices=("filled", "kept", "auto"), default="auto",
                   help="filled=本轮做过补色，偏差超限即失败；kept=保留源值，只报数；auto=默认")
    p.add_argument("--stats-only", action="store_true", help="只打印三态占比")
    return p.parse_args(argv)


def load_alpha(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    arr = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    return arr[::-1, :, 3]           # Blender 像素自下而上，翻成自上而下


def load_src_rgb(path):
    """源图 RGB，按线性值返回（0-255）。E3 产物把线性值写进 DDS，比色要在同一空间。

    预乘源在 alpha=0 处 RGB≈0，用来识别"未补色、保留源值"的洞。
    """
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    arr = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(img)
    return np.clip(arr, 0.0, 1.0) * 255.0


def load_dds(path):
    data = open(path, "rb").read()
    if data[:4] != b"DDS ":
        raise SystemExit("不是 DDS：%s" % path)
    h, w = struct.unpack_from("<II", data, 12)
    fourcc = struct.unpack_from("<I", data, 84)[0]
    if fourcc:
        raise SystemExit("DDS 是压缩格式（fourCC=0x%x），本探针只认未压缩 RGBA8" % fourcc)
    px = np.frombuffer(data[128:128 + w * h * 4], dtype=np.uint8).reshape(h, w, 4)
    return px.astype(np.float32)


def two_means(cols, iters=10):
    """把洞边界上的面料色分成两簇（与补色脚本同口径）。"""
    if len(cols) < 8:
        m = np.median(cols, axis=0)
        return m, m, 1.0
    lum = cols.mean(axis=1)
    c = np.stack([cols[lum.argmin()], cols[lum.argmax()]]).astype(np.float32)
    lab = np.zeros(len(cols), np.int32)
    for _ in range(iters):
        d = ((cols[:, None, :] - c[None, :, :]) ** 2).sum(axis=2)
        new = d.argmin(axis=1)
        if (new == lab).all():
            break
        lab = new
        for k in (0, 1):
            if (lab == k).any():
                c[k] = cols[lab == k].mean(axis=0)
    f0 = float((lab == 0).mean())
    a, b = np.median(cols[lab == 0], axis=0), np.median(cols[lab == 1], axis=0)
    return (a, b, f0) if f0 >= 0.5 else (b, a, 1.0 - f0)


def border_flood(hole):
    """从图像四边灌水，标出与边界连通的镂空（padding 的近似）。"""
    h, w = hole.shape
    seen = np.zeros((h, w), bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if hole[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if hole[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and hole[yy, xx] and not seen[yy, xx]:
                seen[yy, xx] = True
                dq.append((yy, xx))
    return seen


def components(mask):
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    comps = []
    n = 0
    ys, xs = np.nonzero(mask)
    for sy, sx in zip(ys, xs):
        if lab[sy, sx]:
            continue
        n += 1
        dq = deque([(sy, sx)])
        lab[sy, sx] = n
        cells = []
        while dq:
            y, x = dq.popleft()
            cells.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and lab[yy, xx] == 0:
                    lab[yy, xx] = n
                    dq.append((yy, xx))
        comps.append(cells)
    return comps


def main():
    a = parse_args()
    alpha = load_alpha(a.src)
    dds = load_dds(a.dds)
    src_rgb = load_src_rgb(a.src)
    if alpha.shape != dds.shape[:2]:
        raise SystemExit("源图与 dds 尺寸不一致：%s vs %s" % (alpha.shape, dds.shape[:2]))

    hole = alpha < 0.05
    pad = border_flood(hole)
    enc = hole & ~pad
    total = hole.size
    print("STATS hole=%.2f%% pad=%.2f%% enclosed=%.2f%% solid=%.2f%%"
          % (100.0 * hole.mean(), 100.0 * pad.mean(), 100.0 * enc.mean(),
             100.0 * (~hole).mean()))
    if a.stats_only:
        print("AUDIT_OK")
        return

    comps = [c for c in components(enc) if len(c) >= MIN_AREA]
    comps.sort(key=len, reverse=True)
    print("洞数(>=%dpx)=%d" % (MIN_AREA, len(comps)))
    print("%8s %12s %12s %12s %7s  %s" % ("area", "最长邻块", "次长邻块", "当前落色", "偏差", "判定"))

    cross = 0
    bad = 0
    for cells in comps:
        adj = {}
        for (y, x) in cells:
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < alpha.shape[0] and 0 <= xx < alpha.shape[1] and not hole[yy, xx]:
                    key = (yy, xx)
                    adj[key] = adj.get(key, 0) + 1
        # 边界色按颜色聚成两簇：相邻像素在洞周围连成一圈，按连通性分组只会得到一块
        keys = list(adj.keys())
        if not keys:
            continue
        cols_arr = np.array([dds[y, x, :3] for (y, x) in keys], dtype=np.float32)
        main_c, second_c, frac = two_means(cols_arr)
        cy = np.array([c[0] for c in cells])
        cx = np.array([c[1] for c in cells])
        fill = np.median(dds[cy, cx, :3], axis=0)
        src_c = np.median(src_rgb[cy, cx, :3], axis=0)
        dev = float(np.abs(fill - main_c).max())
        dark = float(main_c.mean()) < DARK_RING
        over_cap = dark and float(fill.mean()) > float(main_c.mean()) + DARK_CAP
        is_cross = abs(float(main_c.mean()) - float(second_c.mean())) > CROSS_DELTA and frac > 0.15
        near_source = float(np.abs(fill - src_c).max()) <= 8.0
        if near_source:
            tag = "近源值"
        elif float(fill.max()) < 90.0:
            tag = "暗值"
        else:
            tag = "已补色"
        if is_cross:
            tag += " 跨色洞"
        if over_cap:
            tag += " 破暗壳上限"
        # 保留源值（本轮没有补这一块）不算失败：落色与源值一致即豁免
        exempt = float(np.abs(fill - src_c).max()) <= a.tol
        if a.expect == "filled":
            bad_now = (not exempt) and (dev > a.tol or over_cap)
            bad += 1 if bad_now else 0
            verdict = "KEEP" if exempt else ("FAIL" if bad_now else "OK")
        else:
            verdict = "偏差%.0f" % dev
        print("%8d (%3.0f,%3.0f,%3.0f) (%3.0f,%3.0f,%3.0f) (%3.0f,%3.0f,%3.0f) %7.1f  %-8s %s"
              % (len(cells), *main_c, *second_c, *fill, dev, verdict, tag))
        if is_cross:
            cross += 1

    print("SUMMARY cross=%d bad=%d expect=%s tol=%.0f" % (cross, bad, a.expect, a.tol))
    ok = (bad == 0) if a.expect == "filled" else True   # 其余模式只报数，成败由人判
    print("AUDIT_OK" if ok else "AUDIT_FAIL")
    if not ok:
        sys.exit(1)


main()
