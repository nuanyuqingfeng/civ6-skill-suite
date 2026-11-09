"""鸣潮星芒 / 声痕贴花审计：三重门判定 + 处置验收。

只有三重门**全部**命中才判为鸣潮特例（`WUWA_SPECIAL=hit`），此时要求成品 RGB 全置 0；
任一门不满足 → `WUWA_SPECIAL=skip`，走通用贴花行，**可见区 RGB 必须保留原色**。
这是「非鸣潮主题不触发」的硬守卫，别跳过它自行判断。

用法（普通 python 即可，需要 PIL + numpy，不必开 Blender）：

    python scripts/probes/wuwa_star_decal_audit.py --src <源图.png> \
        [--dds <成品.dds>] [--mtl <材质.mtl>] [--slot <槽名>] [--wuwa]

参数：
  --src   源图（带 alpha 的 png），必需
  --dds   成品基色 dds（未压缩 RGBA8），给了才做验收
  --mtl   材质文件，给了才判材质门
  --slot  槽名（如 MI_6XingStar），用于主题门的星芒族匹配
  --wuwa  显式声明源图来自鸣潮解包产物

输出四段：源图画像 → 三重门逐门判定 → 验收（命中时）→ 末行结论。
末行 `WUWA_SPECIAL=hit|skip` 与 `AUDIT_OK` / `AUDIT_FAIL`，退出码同步。

判据来源：references/wuwa-notes.md §9、references/texture-rules-matrix.md §三。
"""
import argparse
import os
import re
import struct
import sys

import numpy as np
from PIL import Image

# ── 三重门阈值（改这里前先看 wuwa-notes.md §9.2）──────────────────
ALPHA0_MIN_PCT = 20.0      # 门二：alpha=0 占比下限（%）
ALPHA255_MAX_PCT = 50.0    # 门二：alpha=255 占比上限（%），超过说明不是稀疏贴花
SAT_MAX_VAL = 255          # 门二：占位色必须顶到 255
SAT_RANGE_MIN = 200        # 门二：通道极差下限，纯红/品红/纯绿都远超，灰色系远低于
ALPHA_PCT_TOL = 1.0        # 验收：成品与源图 alpha=0 占比允许差（百分点）

# 门一：星芒 / 声痕命名族
STAR_SLOT_RE = re.compile(r"(xing\s*star|xingstar|^star|声痕|共鸣纹|gongming|xing)", re.I)


def read_png_rgba(path):
    im = Image.open(path).convert("RGBA")
    return np.array(im)


def read_dds_rgba(path):
    """读未压缩 RGBA8 的 dds 首层 mip。"""
    d = open(path, "rb").read()
    if d[:4] != b"DDS ":
        raise ValueError("不是 dds: %s" % path)
    h = struct.unpack_from("<I", d, 12)[0]
    w = struct.unpack_from("<I", d, 16)[0]
    bpp = struct.unpack_from("<I", d, 88)[0] // 8
    if bpp != 4:
        raise ValueError("需要 RGBA8 未压缩（当前 %d 字节/像素）: %s" % (bpp, path))
    return np.frombuffer(d[128:128 + w * h * 4], dtype=np.uint8).reshape(h, w, 4), w, h


def read_dds_l8_frac0(path):
    """读单通道 L8 的 opacity dds，返回 =0 占比（%）。"""
    d = open(path, "rb").read()
    h = struct.unpack_from("<I", d, 12)[0]
    w = struct.unpack_from("<I", d, 16)[0]
    a = np.frombuffer(d[128:128 + w * h], dtype=np.uint8).reshape(h, w)
    return 100.0 * float((a == 0).mean())


def pct(mask):
    return 100.0 * float(mask.mean())


def main():
    ap = argparse.ArgumentParser(description="鸣潮星芒 / 声痕贴花审计")
    ap.add_argument("--src", required=True, help="源图（带 alpha 的 png）")
    ap.add_argument("--dds", help="成品基色 dds（未压缩 RGBA8）")
    ap.add_argument("--mtl", help="材质文件 .mtl，用于材质门")
    ap.add_argument("--slot", default="", help="槽名，用于主题门")
    ap.add_argument("--wuwa", action="store_true", help="显式声明源图来自鸣潮解包")
    ap.add_argument("--opacity-dds", help="Opacity 槽 dds，可选，只报数")
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    src = read_png_rgba(a.src)
    al = src[:, :, 3]
    rgb = src[:, :, :3].astype(np.int16)

    m0 = al == 0
    m255 = al == 255
    mid = (~m0) & (~m255)

    print("== 源图画像 ==")
    print("  文件        %s" % os.path.basename(a.src))
    print("  尺寸        %dx%d" % (src.shape[1], src.shape[0]))
    print("  alpha=0     %.2f%%" % pct(m0))
    print("  alpha=255   %.2f%%" % pct(m255))
    print("  中间值      %.2f%%" % pct(mid))
    if m0.any():
        c = np.median(rgb[m0], axis=0).astype(int)
        rng = int(rgb[m0].max(axis=1).max() - rgb[m0].min(axis=1).min())
        print("  alpha=0 区 RGB 中位  (%d,%d,%d)  通道极差 %d" % (c[0], c[1], c[2], rng))
    if m255.any():
        c = np.median(rgb[m255], axis=0).astype(int)
        print("  alpha=255 区 RGB 中位 (%d,%d,%d)" % (c[0], c[1], c[2]))

    # ── 门一：主题 ────────────────────────────────────────────
    slot_hit = bool(a.slot) and bool(STAR_SLOT_RE.search(a.slot))
    gate1 = a.wuwa or slot_hit
    print("\n== 三重门 ==")
    if a.wuwa:
        print("  门一 主题      PASS（--wuwa 显式声明）")
    elif slot_hit:
        print("  门一 主题      PASS（槽名 %s 命中星芒族）" % a.slot)
    else:
        print("  门一 主题      FAIL（未声明鸣潮来源，槽名 %r 也不在星芒族；补 --wuwa 或 --slot）" % a.slot)

    # ── 门二：mask 语义 ───────────────────────────────────────
    p0, p255 = pct(m0), pct(m255)
    c0_ok = False
    rng0 = 0
    if m0.any():
        rgbm = rgb[m0]
        rng0 = int(rgbm.max() - rgbm.min())
        c0_ok = bool(rgbm.max() >= SAT_MAX_VAL and rng0 >= SAT_RANGE_MIN)
    cond_a = p0 > ALPHA0_MIN_PCT
    cond_b = p255 < ALPHA255_MAX_PCT
    gate2 = cond_a and cond_b and c0_ok
    print("  门二 mask语义  %s（alpha=0 %.2f%% >%.0f? %s；alpha=255 %.2f%% <%.0f? %s；"
          "占位色极差 %d ≥%d 且顶到255? %s）"
          % ("PASS" if gate2 else "FAIL", p0, ALPHA0_MIN_PCT, cond_a,
             p255, ALPHA255_MAX_PCT, cond_b, rng0, SAT_RANGE_MIN, c0_ok))

    # ── 门三：材质双槽 ────────────────────────────────────────
    if not a.mtl:
        gate3 = False
        print("  门三 材质      FAIL（未给 --mtl，无法确认 BaseColor+Opacity 双槽）")
    else:
        txt = open(a.mtl, encoding="utf-8", errors="replace").read()
        has_base = re.search(r'<m_ParamName text="BaseColor"\s*/>', txt) is not None
        has_opac = re.search(r'<m_ParamName text="Opacity"\s*/>', txt) is not None
        gate3 = has_base and has_opac
        print("  门三 材质      %s（BaseColor %s / Opacity %s）"
              % ("PASS" if gate3 else "FAIL", has_base, has_opac))

    hit = gate1 and gate2 and gate3

    # ── 验收 ─────────────────────────────────────────────────
    ok = True
    decal_like = p0 > ALPHA0_MIN_PCT          # 源图够稀疏才像是贴花槽
    if not hit:
        print("\n== 验收 ==")
        if decal_like:
            print("  跳过（三重门未全命中 → 通用贴花行，蒙版须保留、可见区 RGB 须保留原色）")
        else:
            print("  跳过（源图 alpha=0 仅 %.2f%% ≤%.0f%%，非贴花槽，本探针不适用；走领袖基色行）"
                  % (p0, ALPHA0_MIN_PCT))
        if a.dds and decal_like:
            out, w, h = read_dds_rgba(a.dds)
            oal = out[:, :, 3]
            orgb = out[:, :, :3]
            d0 = abs(pct(oal == 0) - p0)
            print("  成品 alpha=0 %.2f%%（与源图差 %.2fpp，阈值 ≤%.1fpp）%s"
                  % (pct(oal == 0), d0, ALPHA_PCT_TOL, "OK" if d0 <= ALPHA_PCT_TOL else "FAIL"))
            ok = ok and d0 <= ALPHA_PCT_TOL
            vis = oal >= 230
            if vis.any():
                print("  可见区 RGB 中位 (%s)  —— 非鸣潮应保留原色，不应全 0"
                      % ",".join(str(int(v)) for v in np.median(orgb[vis], axis=0)))
            else:
                print("  无可见区（alpha≥230），请检查蒙版是否被压平")
                ok = False
        elif a.dds:
            print("  不做蒙版检查：非贴花槽的 alpha 本就该压平，此项不适用")
    else:
        if not a.dds:
            print("\n== 验收 ==")
            print("  跳过（未给 --dds）")
        else:
            out, w, h = read_dds_rgba(a.dds)
            oal = out[:, :, 3]
            orgb = out[:, :, :3]
            print("\n== 验收（鸣潮特例） ==")
            print("  成品 %dx%d" % (w, h))
            d0 = abs(pct(oal == 0) - p0)
            print("  [1] alpha=0 占比 %.2f%% vs 源图 %.2f%%（差 %.2fpp，阈值 ≤%.1fpp）%s"
                  % (pct(oal == 0), p0, d0, ALPHA_PCT_TOL, "OK" if d0 <= ALPHA_PCT_TOL else "FAIL"))
            ok = ok and d0 <= ALPHA_PCT_TOL
            mx = int(orgb.max())
            print("  [2] RGB 最大值 %d（特例要求 =0）%s" % (mx, "OK" if mx == 0 else "FAIL"))
            ok = ok and mx == 0
            if a.opacity_dds:
                try:
                    f0 = read_dds_l8_frac0(a.opacity_dds)
                    print("  [3] Opacity 槽 =0 占比 %.2f%%（应与修改前一致）" % f0)
                except Exception as e:
                    print("  [3] Opacity 槽读取失败：%s" % e)
                    ok = False

    print("\nWUWA_SPECIAL=%s" % ("hit" if hit else "skip"))
    print("AUDIT_OK" if ok else "AUDIT_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
