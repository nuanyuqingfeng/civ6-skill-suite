#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""逐帧骨头导出与摘要：把 fgx 的指定骨轨道 dump 成 TSV，并给出可直接判读的统计。

存在的理由：现有读数 exe 有三类坑——长输出路径崩溃、固定采样漏短事件、
只看"相对第 0 帧"会把基准恰在峰值的样本判成静止。这里一次性处理掉。

用法
----
  python dump_tracks.py --fgx <动画.fgx> --code YYY \
      --bones LidUp_L,LidLo_L,Eye_L [--frames 220] [--out DIR]

输出
----
  <out>/<fgx名>_<骨>.tsv        逐帧 TSV（frame, px,py,pz）
  控制台                        每骨的 min/max/span（逐轴）、首峰帧、knot 数

判读要点
--------
  span 用**绝对 min–max**，不是相对首帧；短事件看"连续段"，不看最大值所在帧。
"""
import argparse
import os
import subprocess
import sys
import tempfile

SHORT_TMP = os.path.join(tempfile.gettempdir(), "civ6_dump")


def run_dump(exe, fgx, frames, whitelist, out):
    os.makedirs(SHORT_TMP, exist_ok=True)
    tmp = os.path.join(SHORT_TMP, "dump_tmp.tsv")
    if os.path.exists(tmp):
        os.remove(tmp)
    args = [exe, fgx, str(frames)]
    if whitelist:
        args.append(whitelist)
    args.append(tmp)
    try:
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=300)
    except Exception as e:
        print("DUMP_EXC", e)
        return None
    if not os.path.exists(tmp) or os.path.getsize(tmp) < 100:
        return None
    os.replace(tmp, out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fgx", required=True)
    ap.add_argument("--code", required=True, help="骨名前缀，如 YYY")
    ap.add_argument("--bones", required=True, help="逗号分隔的后缀，如 LidUp_L,LidLo_L")
    ap.add_argument("--frames", type=int, default=None,
                    help="采样帧数；默认读 .anm 时长×30，缺省 240")
    ap.add_argument("--dump", default="NexusFrameDump.exe")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    if not os.path.exists(args.fgx):
        print("ENV_FAIL 找不到", args.fgx)
        return 2
    exe = args.dump
    if not os.path.exists(exe):
        print("ENV_FAIL 找不到读数工具", exe, "（用 --dump 指定完整路径）")
        return 2

    frames = args.frames
    if not frames:
        anm = os.path.splitext(args.fgx)[0] + ".anm"
        if os.path.exists(anm):
            import re
            m = re.search(r"<m_fDuration>([0-9.]+)</m_fDuration>",
                          open(anm, encoding="utf-8", errors="replace").read())
            frames = max(2, round(float(m.group(1)) * 30)) if m else 240
        else:
            frames = 240
        print("FRAMES", frames, "(由 .anm 时长推算，可 --frames 覆盖)")

    suffixes = [s.strip() for s in args.bones.split(",") if s.strip()]
    wl = ",".join("%s_%s" % (args.code, s) for s in suffixes)

    os.makedirs(args.out, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.fgx))[0]
    tsv = os.path.join(SHORT_TMP, base + ".tsv")
    got = run_dump(exe, args.fgx, frames, wl, tsv)
    if not got:
        # 降采样重试
        for n in (frames // 2, 120, 64, 32):
            if n < 8:
                continue
            got = run_dump(exe, args.fgx, n, wl, tsv)
            if got:
                print("DUMP_DEGRADED frames", n)
                break
    if not got:
        print("DUMP_FAIL 该片段可能触发读数 exe 的原生崩溃；换更小 --frames 或另寻通道")
        return 1

    rows = {}
    with open(tsv, encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            a = line.rstrip("\n").split("\t")
            rows.setdefault(a[1], []).append(
                (int(a[0]), [float(a[2]), float(a[3]), float(a[4])]))

    print("-" * 66)
    print("%-22s %8s %8s %8s %8s %8s" % ("bone", "span_x", "span_y", "span_z", "at_frame", "knots"))
    for bone, vals in sorted(rows.items()):
        spans = []
        for k in range(3):
            col = [v[1][k] for v in vals]
            spans.append(max(col) - min(col))
        # 主变化轴的首峰帧（绝对位移最大处）
        main = max(range(3), key=lambda k: spans[k])
        col = [v[1][main] for v in vals]
        peak_i = col.index(max(col)) if abs(max(col)) >= abs(min(col)) else col.index(min(col))
        print("%-22s %8.4f %8.4f %8.4f %8d %8s"
              % (bone, spans[0], spans[1], spans[2], vals[peak_i][0], "-"))

    per_bone = os.path.join(args.out, base + "_bones.txt")
    with open(per_bone, "w", encoding="utf-8") as fh:
        fh.write("bone\tframe\tpx\tpy\tpz\n")
        for bone, vals in sorted(rows.items()):
            for f, p in vals:
                fh.write("%s\t%d\t%.6f\t%.6f\t%.6f\n" % (bone, f, p[0], p[1], p[2]))
    print("WROTE", per_bone)

    # 提示：静止/异常骨
    still = [b for b, v in rows.items()
             if max(max(x[1][k] for x in v) - min(x[1][k] for x in v) for k in range(3)) < 0.02]
    if still:
        print("WARN 以下骨几乎静止（<0.02），先确认几何蒙皮是否覆盖：", ", ".join(sorted(still)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
