#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""G0 表情数据链闸门：官方曲线来源探测 + A/B 路线决策状态机。

任务书口径（P0 铁律 3-6）：
  「找不到官方曲线」的严格定义 = curves/*.uecurves.json 不存在，
  **且**按补导链路（unpack-expression-curves.md）尝试后仍无
  「曲线名 ∩ 形态键清单 ∩ 拟合表 bones>0」命中。
  命中 > 0 → A 路线（默认唯一）。命中 = 0 → NEED_APPROVAL：给出探测证据 +
  B1 手工 PRESETS / B2 表情层留空 / B3 用户补数据 三方案（含影响与回退点），
  只有用户**明确点名**某一方案才构成授权；中断、会话结束、无答复、答非所问、
  「你看着办」、多选、工具异常、超时一律 **ABSTAIN = 不做**（零写操作，
  只写闸门日志与报告）。
  A2 局部补位（某段无曲线 / 短眨眼交回 blink_plan / MANUAL_GAIN=0.55 混合 /
  f>source 冻结段交回人工）属御三家已验证链路，照常执行但必须在报告记录，
  不触发询问。

用法
----
  # 1) G0 探测（产出曲线来源指纹 manifest）
  python expr_route_gate.py probe --curves-dir <角色>/curves \
      --morph-keys <形态键清单.json> --fit-table <拟合表bones.json> \
      --char 角色 [--manifest-out <out.json>] [--inject no-curve]

  # 2) 决策（probe 返回 10 后由用户答复驱动）
  python expr_route_gate.py decide --decision B1 --approval-verbatim "<用户答复原文>"
  python expr_route_gate.py decide --decision A2          # A2 局部补位，免询问

形态键清单 / 拟合表 bones 文件格式：
  morph-keys : ["E_Close", "E_Smile_L", ...]            # PSK MRPHINFO 全量键
  fit-table  : {"E_Close": 6, "E_Smile_L": 3, ...}      # 拟合成功且 bones>0 的键

退出码：0 = A 路线；10 = NEED_APPROVAL（须询问）；11 = ABSTAIN（不做）；
        12 = APPROVED_B（--approval-verbatim 必须含点名的方案号）；
        2 = 参数/环境错误。
"""
import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from morph_curves import included  # noqa: E402  白名单单一来源（含 Aa）

VALID_B = ("B1", "B2", "B3")

APPROVAL_TEXT = """\
G0 表情数据链：官方曲线来源缺失（或白名单全空），进入询问协议。
可选方案（必须明确点名其一，其余答复一律视为未授权）：
  B1  手工 PRESETS：项目人工表情预置接管全部表情。
      影响：无官方微表情、无长闭眼演出、眨眼节奏与官方无关。
      回退点：补导曲线后重跑 A 路线即可整体替换，人工层不残留。
  B2  表情层留空：面骨通道与拟合表照建，但不接任何表情驱动。
      影响：实机面部完全静止（仅身体动画）；后续可随时接入。
      回退点：同 B1。
  B3  用户补数据：把官方曲线文件放入 curves/ 后重跑本闸门。
      影响：无；恢复 A 路线。
未获明确点名授权 = ABSTAIN：不写工程文件/动画/权重表、不 cook、不部署、
不生成任何降级产物、不补齐、不推测、不留半成品，等待答复期间同样零写操作。"""


def sha8(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


def load_json_arg(value):
    raw = value
    if not raw.lstrip().startswith(("[", "{")):
        raw = open(raw, encoding="utf-8").read()
    return json.loads(raw)


def probe(args):
    curves_dir = args.curves_dir
    if not os.path.isdir(curves_dir):
        print("G0_PROBE curves 目录不存在：%s" % curves_dir)
        return {"verdict": "NEED_APPROVAL", "reason": "CURVES_DIR_MISSING",
                "curves_dir": curves_dir, "files": [], "hits": []}

    morph_keys = set(load_json_arg(args.morph_keys))
    fit_table = load_json_arg(args.fit_table)
    files, curve_names, tracks_total = [], set(), 0
    for fn in sorted(os.listdir(curves_dir)):
        if not fn.endswith(".uecurves.json"):   # 只认曲线产物；响应/清单文件不参与
            continue
        path = os.path.join(curves_dir, fn)
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            files.append({"file": fn, "sha8": sha8(path), "bytes": os.path.getsize(path),
                          "error": "JSON 解析失败 %s" % e})
            continue
        names = list((d.get("curves") or {}).keys())
        curve_names.update(names)
        tracks = len(d.get("curves") or {})
        files.append({"file": fn, "sha8": sha8(path), "bytes": os.path.getsize(path),
                      "numFrames": int(d.get("numFrames") or 0),
                      "tracks": tracks,
                      "objectPath": d.get("objectPath")})
        tracks_total += tracks

    # 严格命中定义：曲线名 ∩ 形态键清单 ∩ 拟合表 bones>0，且过白名单
    hits = sorted(n for n in curve_names
                  if included(n) and n in morph_keys and int(fit_table.get(n, 0)) > 0)
    prefix_hits = sorted(n for n in curve_names if included(n))
    injected = args.inject or ""
    if injected == "no-curve":
        hits = []
    manifest = {
        "char": args.char,
        "curves_dir": os.path.abspath(curves_dir),
        "files": files,
        "tracks_total": tracks_total,
        "morph_keys_total": len(morph_keys),
        "fit_table_total": len(fit_table),
        "whitelist_hits": prefix_hits,
        "hits": hits,
        "hit_count": len(hits),
        "inject": injected,
    }
    if args.manifest_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.manifest_out)) or ".",
                    exist_ok=True)
        json.dump(manifest, open(args.manifest_out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    return manifest


def verdict_of_probe(m):
    if m["inject"] == "unauthorized-fallback":
        return "ABSTAIN"
    return "A" if m["hit_count"] > 0 else "NEED_APPROVAL"


def do_probe(args):
    m = probe(args)
    v = verdict_of_probe(m)
    print("G0_PROBE curves_dir=%s files=%d tracks=%d whitelist=%d hits=%d inject=%s"
          % (m["curves_dir"], len(m["files"]), m["tracks_total"],
             len(m["whitelist_hits"]), m["hit_count"], m["inject"] or "-"))
    if m["hits"]:
        print("G0_HITS %s" % ",".join(m["hits"]))
    if v == "A":
        print("G0_ROUTE A  hit_count=%d（A 路线；A2 局部补位照常执行但须记录）"
              % m["hit_count"])
        if args.manifest_out:
            print("G0_MANIFEST %s" % args.manifest_out)
        return 0
    if v == "ABSTAIN":
        print("G0_ROUTE ABSTAIN  注入 unauthorized-fallback：未授权降级被状态机拒绝（验证区分力）")
        return 11
    print(APPROVAL_TEXT)
    print("G0_ROUTE NEED_APPROVAL  探测证据：curves=%s files=%d tracks=%d "
          "whitelist命中=%d 严格命中=0（morph_keys=%d fit_table=%d）"
          % (m["curves_dir"], len(m["files"]), m["tracks_total"],
             len(m["whitelist_hits"]), m["morph_keys_total"], m["fit_table_total"]))
    if args.manifest_out:
        print("G0_MANIFEST %s" % args.manifest_out)
    return 10


def do_decide(args):
    decision = (args.decision or "").strip()
    approval = (args.approval_verbatim or "").strip()
    if args.inject == "unauthorized-fallback":
        print("G0_DECIDE ABSTAIN  UNAUTHORIZED_FALLBACK_REJECTED：未授权降级（注入自检）")
        return 11
    if not decision:
        print("G0_DECIDE ABSTAIN  无答复")
        return 11
    up = decision.upper()
    tokens = [t for t in re.split(r"[,\s、/]+", up) if t]
    if len(tokens) > 1:
        print("G0_DECIDE ABSTAIN  多选（%s）不算授权" % decision)
        return 11
    if up in ("A", "A2"):
        print("G0_DECIDE %s  A2 局部补位照常执行，须在报告 A2 清单记录" % up)
        return 0
    if up in VALID_B:
        if not approval:
            print("G0_DECIDE ABSTAIN  点名了 %s 但没有授权答复原文（--approval-verbatim）" % up)
            return 11
        if up not in approval.upper():
            print("G0_DECIDE ABSTAIN  授权原文与点名方案不一致（原文未包含 %s）" % up)
            return 11
        print("G0_DECIDE APPROVED_B  方案=%s 授权原文已记录" % up)
        return 12
    print("G0_DECIDE ABSTAIN  答非所问（%r）：只有 A/A2/B1/B2/B3 是合法答复" % decision)
    return 11


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="action", required=True)

    p1 = sub.add_parser("probe", help="G0 探测")
    p1.add_argument("--curves-dir", required=True)
    p1.add_argument("--morph-keys", required=True, help="形态键清单 JSON（列表）")
    p1.add_argument("--fit-table", required=True, help="拟合表 {键: bones 数}")
    p1.add_argument("--char", default="")
    p1.add_argument("--manifest-out", default=None)
    p1.add_argument("--inject", choices=["no-curve", "unauthorized-fallback"])

    p2 = sub.add_parser("decide", help="询问答复裁决")
    p2.add_argument("--decision", default=None, help="用户答复：A/A2/B1/B2/B3 或原文")
    p2.add_argument("--approval-verbatim", default="", help="授权答复原文（逐字记录进报告）")
    p2.add_argument("--inject", choices=["unauthorized-fallback"])

    args = ap.parse_args()
    if args.action == "probe":
        return do_probe(args)
    return do_decide(args)


if __name__ == "__main__":
    sys.exit(main())
