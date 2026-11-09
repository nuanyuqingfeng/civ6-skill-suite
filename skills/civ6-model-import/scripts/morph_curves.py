#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""官方表情曲线 → 逐帧权重表，并做双实现交叉校验。

口径见 references/morph-curves.md。核心只有三条：
  1) 帧对齐用实测 L = numFrames - 1，不用 fps 反算；
  2) 拼接按 total 截断、不足处冻结在末帧（不循环、不补零）；
  3) 双实现必须 MAE = 0，单实现自测只能证明"没崩"。

用法
----
  # 生成
  python morph_curves.py build --curves <曲线目录> --targets targets.json --out <输出目录>
  # 只校验已生成的表
  python morph_curves.py verify --curves <曲线目录> --targets targets.json --out <输出目录>

无曲线来源不是合法结局：--require-source（默认开）在所有 target 都没有任何
白名单命中曲线时以 CURVE_SOURCE_EMPTY 非零退出——A 路线下必须先补导官方曲线
（references/unpack-expression-curves.md）或走询问协议
（references/expression-route.md），不允许静默产出空表后照常继续。
部分片段缺曲线（如公共体型动画）仍按 SKIP 处理，属 A2 局部补位，需在报告记录。

targets.json
------------
  {
    "YYY_IDLE":   {"total": 220, "source": 220, "segments": [["Ui_Nature_Loop", 1]]},
    "YYY_Defeat": {"total": 157, "source": 96, "segments": [["Ui_Nature_End", 1], ["Cos_Pose", 1]]}
  }
  segments 里第二项是重复次数。source = 身体动画 NLA 的保持帧（各源片段 ueanim
  帧长之和，与御三家 ysj2_morph_curves.TARGETS 同源）；省略时取各段曲线
  L=numFrames-1 之和。total > source 的帧冻结为 NLA HOLD（动作末帧采样）。

曲线文件命名：<片段名>.json，结构 {numFrames, fps, curves:{name:{times,values}}}。
"""
import argparse
import json
import os
import re
import sys

# 纳入：表情 / 瞳孔 / 源动画自带口型
# VISEMES 与御三家已验证链（ysj2_morph_curves.py）逐字对齐，含 "Aa"；
# 缺 Aa 会在 Defeat 类片段整列丢失元音口型（2026-11-06 P1 回归实证）。
PREFIXES = ("B_", "E_", "M_", "C_", "Pupil_", "P_M_")
VOWELS = {"A", "Aa", "E", "I", "O", "U"}
# 排除：值域不是权重的参数曲线 / 材质参数 / 开关
DENY_SUBSTR = ("morpher_", "UI_Eyes_Control")
DENY_RE = re.compile(r"^Eye\d+$|^Pupil\d+$")
EPS = 1e-4


def included(name):
    if any(s in name for s in DENY_SUBSTR) or DENY_RE.match(name):
        return False
    if name in VOWELS:
        return True
    return name.startswith(PREFIXES)


def load_curve(path):
    d = json.load(open(path, encoding="utf-8"))
    nf = int(d["numFrames"])
    vals = {}
    for name, c in d["curves"].items():
        if not included(name):
            continue
        v = c.get("values") or []
        if v and (min(v) < -0.01 or max(v) > 1.01):
            # 值域越界 → 不是 0-1 权重，排除（多半拿成了参数曲线）
            continue
        vals[name] = [min(1.0, max(0.0, float(x))) for x in v]
    return {"numFrames": nf, "L": nf - 1, "curves": vals}


def build_layout(target, curves_dir):
    """返回 [(曲线数据, start, end)] 与 source 总量。

    段区间为半开 [start, end)：一条 strip 占 L = numFrames-1 帧，
    下一帧起属于下一段——与身体动画 NLA strip 铺帧及御三家已验证链
    （ysj2_morph_curves._layout）逐帧一致。2026-11-06 P1 回归证实：
    闭区间会让边界帧重复计入前段（每段多占一帧），多段表全体漂移。
    """
    layout, cursor, source = [], 1, 0
    for clip, rep in target["segments"]:
        path = os.path.join(curves_dir, clip + ".json")
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        d = load_curve(path)
        for _ in range(int(rep)):
            start = cursor
            end = cursor + d["L"]
            layout.append((d, start, end))
            cursor = end
            source += d["L"]
    return layout, source


def _hold(layout):
    """越过末条 strip = NLA HOLD：停在动作末帧（最后一个采样 v[-1]）。

    御三家已验证链的冻结语义即此（ysj2_morph_curves._value_at 的
    越界分支），不是 v[L-1]。"""
    last = layout[-1][0]
    return {n: v[-1] for n, v in last["curves"].items()}


def value_at(frame, layout):
    """正向实现：frame 为 1-based 目标帧。落在哪段就取该段第 (frame-start) 帧；
    越过末条 strip（frame >= 末段 end）返回动作末帧 hold。"""
    for d, start, end in layout:
        if start <= frame < end:
            i = min(frame - start, d["L"] - 1)
            return {n: v[min(i, len(v) - 1)] for n, v in d["curves"].items()}
    if layout:
        return _hold(layout)
    return {}


def value_reverse(frame, layout):
    """反向实现：从目标帧反推所属段与段内偏移，逻辑与正向独立书写。"""
    for d, start, end in layout:
        if frame < start or frame >= end:
            continue
        off = frame - start
        i = 0 if d["L"] == 0 else min(off, d["L"] - 1)
        # 该段的曲线长度可能短于 L，钳到末尾
        out = {}
        for n, v in d["curves"].items():
            out[n] = v[i] if i < len(v) else v[-1]
        return out
    if layout:
        return _hold(layout)
    return {}


def clean(row):
    return {k: (0.0 if v <= EPS else round(v, 6)) for k, v in row.items()}


def build_one(name, target, curves_dir, out_dir):
    layout, source_sum = build_layout(target, curves_dir)
    # source 可由 targets 显式给出（= 身体动画 NLA 保持帧，与御三家 TARGETS 同源）；
    # 缺省时 = 各段 L 之和。冻结/保持行 value_at(source) 两种取值下都与已验证链一致。
    source = int(target["source"]) if "source" in target else source_sum
    total = int(target["total"])
    names = sorted({n for d, _s, _e in layout for n in d["curves"]})
    if not names:
        return None

    frames = []
    for f in range(1, total + 1):
        if f <= source:
            row = value_at(f, layout)
        else:
            # 冻结段：保持 source 帧，不循环、不补零
            row = value_at(source, layout)
        frames.append([clean(row).get(n, 0.0) for n in names])

    peak = max((max(r) if r else 0.0) for r in frames) if frames else 0.0
    active = sum(1 for r in frames if max(r) > EPS)
    table = {"clip": name, "total": total, "source": source,
             "morphs": names, "frames": frames,
             "peak": round(peak, 4), "active_frames": active}
    os.makedirs(out_dir, exist_ok=True)
    json.dump(table, open(os.path.join(out_dir, name + ".json"), "w",
                          encoding="utf-8"), ensure_ascii=False)
    return table


def verify_one(name, target, curves_dir, out_dir):
    path = os.path.join(out_dir, name + ".json")
    if not os.path.exists(path):
        return ("MISSING", name, None)
    table = json.load(open(path, encoding="utf-8"))
    layout, source_sum = build_layout(target, curves_dir)
    source = int(target["source"]) if "source" in target else source_sum
    total = int(target["total"])
    names = table["morphs"]
    idx = {n: i for i, n in enumerate(names)}
    worst, worst_abs = 0.0, 0.0
    for f in range(1, total + 1):
        ref = value_reverse(f if f <= source else source, layout)
        for n in names:
            expect = 0.0 if ref.get(n, 0.0) <= EPS else round(ref[n], 6)
            got = table["frames"][f - 1][idx[n]]
            d = abs(got - expect)
            worst_abs = max(worst_abs, d)
            worst += d
    mae = worst / max(1, total * len(names))
    return ("OK" if worst_abs <= 1e-9 else "FAIL", name,
            {"mae": round(mae, 10), "max_abs": worst_abs})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["build", "verify"])
    ap.add_argument("--curves", required=True)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--require-source", dest="require_source", default=True,
                    action="store_true",
                    help="默认开：全部 target 都无白名单命中曲线 → CURVE_SOURCE_EMPTY 非零退出")
    ap.add_argument("--no-require-source", dest="require_source", action="store_false")
    args = ap.parse_args()

    targets = json.load(open(args.targets, encoding="utf-8"))
    if args.action == "build":
        # 整条来源缺失（目录不存在 / 目录内无任何曲线 JSON）→ CURVE_SOURCE_EMPTY
        has_source = os.path.isdir(args.curves) and any(
            f.endswith(".json") for f in os.listdir(args.curves))
        if not has_source:
            print("CURVE_SOURCE_EMPTY 曲线目录无任何来源：%s" % args.curves)
            if args.require_source:
                print("CURVE_SOURCE_EMPTY A 路线禁止静默降级——先补导官方曲线或走询问协议")
                return 2
            return 0
        built = empty = 0
        for name, t in targets.items():
            table = build_one(name, t, args.curves, args.out)
            if table:
                built += 1
                print("BUILT %-18s total=%3d source=%3d morphs=%2d peak=%.2f active=%3d"
                      % (name, table["total"], table["source"],
                         len(table["morphs"]), table["peak"], table["active_frames"]))
            else:
                empty += 1
                print("CURVE_SOURCE_EMPTY %-18s 该片段无任何白名单命中曲线" % name)
        if empty and built == 0 and args.require_source:
            print("CURVE_SOURCE_EMPTY 全部 %d 个 target 均无可用曲线："
                  "A 路线禁止静默降级——先补导官方曲线或走询问协议" % empty)
            return 2
        return 0

    bad = 0
    for name, t in targets.items():
        status, _n, info = verify_one(name, t, args.curves, args.out)
        print("VERIFY %-18s %-6s %s" % (name, status, info or ""))
        if status != "OK":
            bad += 1
    print("VERIFY_DONE bad=%d" % bad)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
