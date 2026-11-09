#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""几何蒙皮 + 动画轨迹 + 装配一致 三合一闸门。

为什么需要它：只验动画曲线的脚本看不到几何权重，会出现"离线全绿、实机无表情"。
判据与背景见 references/face-skin-gate.md。

用法
----
  python face_skin_gate.py --geo <Geometries目录> --anim <Animations目录> \
      --code YYY --char-name Yangyang --clips clips.json \
      --meshtable <NexusMeshTable.exe> --dump <NexusFrameDump.exe> \
      [--slug yangyang] [--inject ERRCODE]

clips.json 形如：{"YYY": [["IDLE", 220], ["FirstMeet", 224], ...]}

--inject 用于自检（配合 scripts/gate_selftest.py）：
  no-face-skin          把面骨顶点数强制为 0（模拟"几何没蒙皮"）
  weak-blink            把 LidUp 幅度强制为 0.2（模拟"半闭"）
  lower-lid-static      把 LidLo 幅度强制为 0（模拟"下睑不动"）
  no-curve              模拟"整条官方曲线来源缺失"——A 路线必须 FAIL，
                        不允许静默降级（表情数据链硬闸门，见 references/expression-route.md）
  unauthorized-fallback 模拟"未经用户点名授权的 B 路线降级"——必须 FAIL
注入后必须返回非零；若仍返回 0，说明本闸门没有区分力。

几何文件定位：默认按 --code-map 给出的完整名与 --geo-pattern 匹配，不再硬编码
LEAD_YSJ_* 前缀与 YYY/CXX/BZH 代号表（2026-11-06 P1 回归实证 GEO_MISSING）。

退出码：0 = PASS，1 = FAIL，2 = 参数/环境错误。
"""
import argparse
import fnmatch
import hashlib
import json
import math
import os
import re
import subprocess
import sys

SUFFIXES = ("Jaw", "LipUp", "LipLo", "MouthCorner_L", "MouthCorner_R",
            "LidUp_L", "LidUp_R", "LidLo_L", "LidLo_R", "Eye_L", "Eye_R",
            "Brow_L", "Brow_R", "BrowIn_L", "BrowIn_R", "Cheek_L", "Cheek_R", "Nose")
# LipLo 在多数资产上本来就没有蒙皮权重，不计入缺失
OPTIONAL_BONES = {"LipLo"}

MIN_LIDUP_VERTS = 150
MIN_LIDLO_VERTS = 30
MIN_EYE_VERTS = 90
MIN_LIDUP_SPAN_CM = 1.0
MIN_LIDLO_SPAN_CM = 0.30
MIN_BLINKS_IDLE = 2
LIDLO_STRICT_CLIPS = {"IDLE", "FirstMeet"}

# 两个原生读数 exe 对长输出路径会越界崩溃/截断输出，统一落最短路径
# （实测 %TEMP%≈40 字符仍会截断，必须 C:/Temp 一级；2026-11-06 P1 回归实证）
SHORT_TMP = r"C:\Temp\civ6_gate"


def short_path(name):
    os.makedirs(SHORT_TMP, exist_ok=True)
    return os.path.join(SHORT_TMP, name)


def run(exe, args, timeout=240):
    """跑读数 exe。成功判据与实证链一致：returncode == 0 且产物 >100 字节。

    原生崩溃（AccessViolation）退出码为无符号大值/负值且常留下截断文件，
    只查文件大小会把残缺 TSV 当成功喂给解析器（2026-11-06 P1 实证）。
    """
    try:
        p = subprocess.run([exe] + args, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=timeout)
    except Exception:
        return None
    return p.returncode


def probe_candidates(geo_dir, code, code_map, geo_pattern, ext):
    """按 --geo-pattern / --code-map 定位几何文件；都不给则退回"代号或完整名出现在文件名"。

    兼容 LEAD_YSJ_Yangyang_QYQXP.fgx（代号 YYY）这类"代号 ≠ 文件名"的工程。
    Camera 件不参与。"""
    name_full = code_map.get(code, "")
    files = sorted(f for f in os.listdir(geo_dir) if f.lower().endswith(ext))
    if geo_pattern:
        files = [f for f in files if fnmatch.fnmatch(f, geo_pattern)]
    cand = [f for f in files
            if "camera" not in f.lower()
            and (name_full.lower() in f.lower() or code.lower() in f.lower())]
    return [os.path.join(geo_dir, f) for f in cand]


# ---------------------------------------------------------------- G1 几何蒙皮
def gate_skin(geo_dir, code, meshtable, inject, code_map=None, geo_pattern=None):
    code_map = code_map or {}
    cand = probe_candidates(geo_dir, code, code_map, geo_pattern, ".fgx")
    if not cand:
        return False, "GEO_MISSING 找不到 %s 的几何 fgx" % code, {}
    fgx = cand[0]

    out = short_path("mesh_%s.txt" % code)
    with open(out, "w", encoding="utf-8", errors="replace") as fh:
        subprocess.run([meshtable, fgx], stdout=fh, stderr=subprocess.STDOUT,
                       timeout=240)
    txt = open(out, encoding="utf-8", errors="replace").read()

    dominant = {m.group(1): int(m.group(2))
                for m in re.finditer(r"FAM \S+\((\S+?)\)\s+verts=(\d+)", txt)}
    palette_match = re.search(r"palette=\[([^\]]*)\]", txt)
    palette = set(palette_match.group(1).split(",")) if palette_match else set()

    need = ["%s_%s" % (code, s) for s in SUFFIXES if s not in OPTIONAL_BONES]
    counts = {n: dominant.get(n, 0) for n in need}

    if inject == "no-face-skin":
        counts = {k: 0 for k in counts}

    missing = sorted(n for n, v in counts.items() if v <= 0)
    in_pal = sorted(n for n in need if n in palette)
    lo = min(counts.get("%s_LidLo_L" % code, 0), counts.get("%s_LidLo_R" % code, 0))
    up = min(counts.get("%s_LidUp_L" % code, 0), counts.get("%s_LidUp_R" % code, 0))
    eye = min(counts.get("%s_Eye_L" % code, 0), counts.get("%s_Eye_R" % code, 0))

    fails = []
    if missing:
        fails.append("面骨无权重:" + ",".join(missing))
    if len(in_pal) < len(need) - 1:
        fails.append("palette 缺面骨(%d/%d)" % (len(in_pal), len(need)))
    if up < MIN_LIDUP_VERTS:
        fails.append("LidUp 顶点 %d < %d" % (up, MIN_LIDUP_VERTS))
    if lo < MIN_LIDLO_VERTS:
        fails.append("LidLo 顶点 %d < %d" % (lo, MIN_LIDLO_VERTS))
    if eye < MIN_EYE_VERTS:
        fails.append("Eye 顶点 %d < %d" % (eye, MIN_EYE_VERTS))

    detail = ("palette=%d 面骨=%d/%d LidUp=%d LidLo=%d Eye=%d"
              % (len(palette), len(in_pal), len(need), up, lo, eye))
    return (not fails), (detail if not fails else detail + " | " + "; ".join(fails)), counts


# ---------------------------------------------------------------- G2 动画轨迹
def qangle(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return math.degrees(2.0 * math.acos(min(1.0, d / max(1e-9, na * nb))))


def dump_bones(dump, fgx, frames, code, tag):
    names = ",".join("%s_%s" % (code, s) for s in
                     ("LidUp_L", "LidUp_R", "LidLo_L", "LidLo_R", "Eye_L", "Eye_R"))
    out = short_path(tag + ".tsv")
    # 实证调用约定（ysj5_face_gate.py:121）：NexusFrameDump <fgx> <frames> <out> <names>
    # —— 输出路径第三参、骨名白名单最后。高频采样对部分片段 native 崩溃且
    # 留下截断文件，必须以 returncode==0 且文件完整为成功判据，逐级降采样。
    data = None
    for n in (int(frames), 120, 96, 64, 48, 32):
        rc = run(dump, [fgx, str(n), out, names])
        if rc != 0 or not os.path.exists(out) or os.path.getsize(out) <= 100:
            continue
        data = {}
        with open(out, encoding="utf-8") as fh:
            next(fh)
            for line in fh:
                a = line.rstrip("\n").split("\t")
                if len(a) < 5:
                    continue          # 截断残行（理论上有 rc 判据后不应出现）
                data.setdefault(a[1], []).append(
                    (int(a[0]), [float(x) for x in a[2:5]]))
        if data:
            break
        data = None
    return data
    data = {}
    with open(out, encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            a = line.rstrip("\n").split("\t")
            data.setdefault(a[1], []).append(
                (int(a[0]), [float(x) for x in a[2:5]]))
    return data


def axis_span(rows):
    """绝对 min–max（不看相对第 0 帧，避免基准恰在峰值）。"""
    if not rows:
        return 0.0, []
    out = 0.0
    vecs = [p for _f, p in rows]
    for k in range(3):
        col = [v[k] for v in vecs]
        out = max(out, max(col) - min(col))
    return out, vecs


def count_runs(values, thresh):
    n, active = 0, False
    for v in values:
        if v > thresh and not active:
            n += 1
            active = True
        elif v <= thresh:
            active = False
    return n


def gate_anim(anim_dir, code, clips, dump, inject):
    lines, ok = [], True
    for clip, total in clips:
        name = "%s_%s" % (code, clip)
        fgx = os.path.join(anim_dir, name + ".fgx")
        if not os.path.exists(fgx):
            lines.append("  %-22s MISSING" % name)
            ok = False
            continue
        data = dump_bones(dump, fgx, total, code, "gate_" + name)
        if data is None:
            lines.append("  %-22s DUMP_FAIL" % name)
            ok = False
            continue
        up_span, up_vecs = axis_span(data.get(code + "_LidUp_L"))
        lo_span, _ = axis_span(data.get(code + "_LidLo_L"))

        if inject == "weak-blink":
            up_span = 0.2
        if inject == "lower-lid-static":
            lo_span = 0.0

        # 眨眼次数用竖直轴（第三轴）的绝对阈值计数
        zs = [v[2] for v in up_vecs] if up_vecs else []
        blinks = count_runs([abs(z - zs[0]) for z in zs], MIN_LIDUP_SPAN_CM * 0.45) if zs else 0

        flags = []
        if inject == "no-curve":
            flags.append("NO_CURVE_SOURCE")
        if inject == "unauthorized-fallback":
            flags.append("UNAUTHORIZED_FALLBACK")
        if up_span < MIN_LIDUP_SPAN_CM:
            flags.append("BLINK_WEAK")
        if lo_span < MIN_LIDLO_SPAN_CM:
            # 下睑只对指定片段严格（其余片段官方数据本就不驱动 LidLo）
            flags.append("LOWER_LID_STATIC" if clip in LIDLO_STRICT_CLIPS
                         else "LowerLidLow(源数据限制)")
        if clip == "IDLE" and blinks < MIN_BLINKS_IDLE:
            flags.append("NO_BLINK")

        hard = [f for f in flags if not f.startswith("LowerLidLow")]
        if hard:
            ok = False
        lines.append("  %-22s LidUp=%.3f LidLo=%.3f blinks=%d %s"
                     % (name, up_span, lo_span, blinks,
                        " ".join(flags) if flags else "OK"))
    return ok, "\n".join(lines)


# ---------------------------------------------------------------- G3 装配一致
def gate_assembly(geo_dir, anim_dir, code, clips, slug, blp,
                  code_map=None, geo_pattern=None):
    problems = []
    cand = probe_candidates(geo_dir, code, code_map or {}, geo_pattern, ".geo")
    geo = cand[0] if cand else None
    if geo is None:
        problems.append("GEO_MISSING")
    else:
        txt = open(geo, encoding="utf-8", errors="replace").read()
        absent = [n for n in ("%s_%s" % (code, s) for s in SUFFIXES) if n not in txt]
        if absent:
            problems.append("geo 骨骼表缺:" + ",".join(absent))
    for clip, _t in clips:
        anm = os.path.join(anim_dir, "%s_%s.anm" % (code, clip))
        if not os.path.exists(anm):
            problems.append("anm 缺 " + clip)
        elif ("%s_%s.fgx" % (code, clip)) not in open(anm, encoding="utf-8",
                                                      errors="replace").read():
            problems.append("anm 指向错误 " + clip)
    if blp and os.path.exists(blp):
        blob = open(blp, "rb").read()
        if (code + "_LidLo_L").encode() not in blob:
            problems.append("BLP 内无面骨名（几何可能没进包）")
    return not problems, "; ".join(problems) if problems else "geo/anm/blp OK"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", required=True, help="Geometries 目录")
    ap.add_argument("--anim", required=True, help="Animations 目录")
    ap.add_argument("--code", required=True, help="面骨代号，如 YYY")
    ap.add_argument("--clips", required=True, help="clips.json")
    ap.add_argument("--meshtable", required=True)
    ap.add_argument("--dump", required=True)
    ap.add_argument("--code-map", default=None,
                    help='代号→文件完整名映射，如 \'{"YYY":"Yangyang","DJ":"DanJin"}\'；'
                         "内联 JSON 或 JSON 文件路径。缺省回退“代号本身出现在文件名”")
    ap.add_argument("--geo-pattern", default=None,
                    help="几何文件 fnmatch 通配，如 'LEAD_*_QYQXP.fgx'；缺省不筛选")
    ap.add_argument("--slug", default=None, help="BLP 用，可选")
    ap.add_argument("--blp", default=None, help="BLP 路径，可选")
    ap.add_argument("--inject", default=None,
                    choices=[None, "no-face-skin", "weak-blink", "lower-lid-static",
                             "no-curve", "unauthorized-fallback"])
    args = ap.parse_args()

    code_map = {}
    if args.code_map:
        raw = args.code_map
        if not raw.lstrip().startswith("{"):
            raw = open(raw, encoding="utf-8").read()
        code_map = json.loads(raw)

    for p in (args.meshtable, args.dump):
        if not os.path.exists(p):
            print("ENV_FAIL 找不到读数工具:", p)
            return 2

    clips_map = json.load(open(args.clips, encoding="utf-8"))
    clips = [tuple(x) for x in clips_map.get(args.code, [])]
    if not clips:
        print("ENV_FAIL clips.json 里没有 %s" % args.code)
        return 2

    print("=" * 70)
    print("### %s  inject=%s" % (args.code, args.inject or "-"))

    s_ok, s_msg, _counts = gate_skin(args.geo, args.code, args.meshtable, args.inject,
                                     code_map, args.geo_pattern)
    print(" G1 几何蒙皮  %s  %s" % ("PASS" if s_ok else "FAIL", s_msg))

    a_ok, a_msg = gate_anim(args.anim, args.code, clips, args.dump, args.inject)
    print(" G2 动画轨迹  %s" % ("PASS" if a_ok else "FAIL"))
    print(a_msg)

    c_ok, c_msg = gate_assembly(args.geo, args.anim, args.code, clips,
                                args.slug, args.blp, code_map, args.geo_pattern)
    print(" G3 装配一致  %s  %s" % ("PASS" if c_ok else "FAIL", c_msg))

    ok = s_ok and a_ok and c_ok
    print("=" * 70)
    print("FACE_SKIN_GATE", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
