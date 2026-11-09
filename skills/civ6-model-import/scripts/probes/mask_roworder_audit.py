# mask_roworder_audit.py -- 判定一张 alpha 掩膜是按「row = (1-v)·H」还是「row = v·H」写的。
#
# 为什么需要这个工具（2026-11-07 长离 n=3 事故）：
#   把 UV 三角栅格化成掩膜时，行序写反是**纯静默失败**——不报错、不过界、DDS 头合法、
#   Blender 预览正常，只有实机会偏浅或出现色差。当时靠人肉比对亮度才发现，
#   代价是三轮返工。本脚本把「掩膜内容与 UV 岛是否对齐」变成一个可复算的读数。
#
# 判据（两种行序各栅格化一次，比覆盖）：
#   cover = 岛内 alpha>=thr 的像素占岛面积的比例      —— 越大越对
#   leak  = 岛外 alpha>=thr 的像素占全图的比例        —— 越大说明掩膜铺到不该铺的地方
#   cover(正写) - cover(反写) > TOL  -> ROWORDER_TOP（正写 row=(1-v)·H 正确）
#   cover(反写) - cover(正写) > TOL  -> MIRRORED（写成了 row=v·H，上下翻转）
#   两者都 <= TOL                     -> AMBIGUOUS（掩膜近似上下对称，或缺覆盖，判不出）
#
# 为什么不能只看一个方向：图形上下对称时两种行序结果相同，此时本工具必须报
# AMBIGUOUS 而不是猜一个——猜错就等于把静默失败带回管线。
#
# 用法：
#   python mask_roworder_audit.py --mask <png> --uv <hair_uv.tsv> [--size N]
#                                 [--alpha-thr 250] [--group-contains 正面]
#   python mask_roworder_audit.py --selftest        # 反向闸门：注入翻转必须报 MIRRORED
#
# uv tsv 由 scripts/probes/dump_hair_uv.py 生成，字段 `组名 u1 v1 u2 v2 u3 v3`，
# v 为 Blender 侧自下而上的原始 v（本脚本自己决定翻不翻，不要预先翻过）。
#
# 退出码：
#   0 = ROWORDER_TOP（正写）
#   4 = MIRRORED（翻转过，需重写掩膜）
#   5 = AMBIGUOUS（判不出，换一张非对称掩膜或加 --group-contains 收窄）
#   1 = 参数/输入错误

import argparse
import os
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

TOL = 0.02


def parse_uv(tsv, group_contains=None):
    """读 dump_hair_uv.py 的 tsv，返回 [(组名, ((u,v),(u,v),(u,v))), ...]。"""
    tris = []
    with open(tsv, "r", encoding="utf-8", errors="replace") as fh:
        for ln, line in enumerate(fh, 1):
            parts = line.strip().split("\t")
            if len(parts) < 7:
                parts = line.strip().split()
            if len(parts) < 7:
                continue
            try:
                vals = [float(x) for x in parts[-6:]]
            except ValueError:
                continue  # 表头或注释行
            name = parts[0]
            if group_contains and group_contains not in name:
                continue
            tris.append((name, ((vals[0], vals[1]), (vals[2], vals[3]), (vals[4], vals[5]))))
    return tris


def raster(tris, size, flipped):
    """flipped=False -> row=(1-v)·H（正写）；True -> row=v·H（上下翻转）。"""
    img = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(img)
    s = size - 1
    for _, tri in tris:
        pts = []
        for u, v in tri:
            y = (v if flipped else 1.0 - v) * s
            pts.append((u * s, y))
        d.polygon(pts, fill=255)
    return np.asarray(img) > 0


def read_alpha(path):
    im = Image.open(path).convert("RGBA")
    return np.asarray(im)[:, :, 3]


def audit(mask_path, uv_path, size=None, alpha_thr=250, group_contains=None):
    tris = parse_uv(uv_path, group_contains)
    if not tris:
        raise ValueError("uv 表里没有可用三角（检查分隔符与 --group-contains）")
    alpha = read_alpha(mask_path)
    h, w = alpha.shape
    size = size or min(h, w)
    if (h, w) != (size, size):
        alpha = np.asarray(
            Image.open(mask_path).convert("RGBA").resize((size, size), Image.NEAREST)
        )[:, :, 3]
    solid = alpha >= alpha_thr

    out = {"mask": mask_path, "uv": uv_path, "size": size, "triangles": len(tris)}
    for key, flipped in (("top", False), ("flipped", True)):
        island = raster(tris, size, flipped)
        island_px = int(island.sum())
        cover = float((solid & island).sum()) / max(island_px, 1)
        leak = float((solid & ~island).sum()) / float(size * size)
        out[key] = {"island_px": island_px, "cover": cover, "leak": leak}

    d = out["top"]["cover"] - out["flipped"]["cover"]
    if d > TOL:
        verdict = "ROWORDER_TOP"
    elif -d > TOL:
        verdict = "MIRRORED"
    else:
        verdict = "AMBIGUOUS"
    out["delta"] = d
    out["verdict"] = verdict
    return out


def _selftest():
    """反向闸门：同一份 UV + 同一张掩膜，正写必须 TOP，翻转必须 MIRRORED。"""
    tmp = tempfile.mkdtemp(prefix="roworder_")
    uv = os.path.join(tmp, "uv.tsv")
    # 一条明显上下不对称的三角形（尖端朝上），保证两种行序可区分
    with open(uv, "w", encoding="utf-8") as fh:
        fh.write("front\t0.20\t0.10\t0.80\t0.10\t0.50\t0.55\n")
    tris = parse_uv(uv)
    ok = 0
    for name, flipped, want in (("top", False, "ROWORDER_TOP"), ("flip", True, "MIRRORED")):
        island = raster(tris, 512, flipped)
        img = np.zeros((512, 512, 4), dtype=np.uint8)
        img[:, :, 3] = np.where(island, 255, 0)
        p = os.path.join(tmp, f"mask_{name}.png")
        Image.fromarray(img, "RGBA").save(p)
        got = audit(p, uv, size=512)["verdict"]
        flag = "PASS" if got == want else "FAIL"
        print(f"SELFTEST {name}: want={want} got={got} {flag}")
        ok += got == want
    print(f"SELFTEST_RESULT {ok}/2")
    return 0 if ok == 2 else 6


def main(argv=None):
    ap = argparse.ArgumentParser(description="alpha 掩膜行序审计")
    ap.add_argument("--mask", help="掩膜图（png；dds 请先转 png）")
    ap.add_argument("--uv", help="dump_hair_uv.py 产出的 tsv")
    ap.add_argument("--size", type=int, default=None)
    ap.add_argument("--alpha-thr", type=int, default=250)
    ap.add_argument("--group-contains", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return _selftest()
    if not (a.mask and a.uv):
        ap.print_help()
        return 1
    try:
        r = audit(a.mask, a.uv, a.size, a.alpha_thr, a.group_contains)
    except Exception as exc:  # noqa: BLE001 - 顶层要把原因原样带回
        print(f"MASK_ROWORDER_ERROR {exc}")
        return 1

    for key, label in (("top", "row=(1-v)*H"), ("flipped", "row=v*H    ")):
        e = r[key]
        print(
            f"MASK_ROWORDER {label} island_px={e['island_px']:>9} "
            f"cover={e['cover']:.4f} leak={e['leak']:.5f}"
        )
    print(
        f"MASK_ROWORDER delta={r['delta']:+.4f} triangles={r['triangles']} "
        f"verdict={r['verdict']}"
    )
    return {"ROWORDER_TOP": 0, "MIRRORED": 4}.get(r["verdict"], 5)


if __name__ == "__main__":
    sys.exit(main())
