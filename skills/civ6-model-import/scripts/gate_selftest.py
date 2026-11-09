#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""闸门自检器：证明验收脚本真的会对错误说 FAIL。

背景见 references/misattribution.md 第五节「反向闸门」。
一个闸门如果在注入已知错误后仍然 PASS，它就没有区分力——此时"全绿"不构成证据。

用法
----
  python gate_selftest.py --gate <闸门脚本> --base "<正常跑的命令>" \
      [--inject-flag "--inject"] [--cases no-face-skin,weak-blink,lower-lid-static]

约定：被检闸门必须支持 `--inject <ERRCODE>`，并在注入后返回非零。
本脚本自动完成「基线必须 PASS → 逐个注入必须 FAIL → 不留残余」。

退出码：0 = 闸门有效；1 = 闸门无区分力；2 = 参数/环境问题。
"""
import argparse
import shlex
import subprocess
import sys


def run_cmd(template, inject=None, inject_flag="--inject"):
    cmd = template.format(inject=("" if inject is None else "%s %s" % (inject_flag, inject)))
    p = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", required=True, help="闸门脚本路径（仅用于展示/校验存在）")
    ap.add_argument("--base", required=True,
                    help='命令模板，用 {inject} 占位，例如：'
                         '"python face_skin_gate.py --geo G --anim A --code YYY '
                         '--clips c.json --meshtable M --dump D {inject}"')
    ap.add_argument("--inject-flag", default="--inject")
    ap.add_argument("--cases",
                    default="no-face-skin,weak-blink,lower-lid-static,"
                            "no-curve,unauthorized-fallback")
    args = ap.parse_args()

    import os
    if not os.path.exists(args.gate):
        print("ENV_FAIL 闸门脚本不存在:", args.gate)
        return 2

    rc, out = run_cmd(args.base, None, args.inject_flag)
    tail = "\n".join(out.strip().splitlines()[-3:])
    print("[基线] exit=%d  %s" % (rc, tail.replace("\n", " / ")))
    if rc != 0:
        print("SELFTEST_FAIL 基线没有通过，无法判断区分力（先让正常输入 PASS）")
        return 2

    bad = []
    for case in [c.strip() for c in args.cases.split(",") if c.strip()]:
        rc, out = run_cmd(args.base, case, args.inject_flag)
        ok = rc != 0
        print("[注入 %-16s] exit=%d  %s" % (case, rc, "OK(已 FAIL)" if ok else "!! 仍然 PASS"))
        if not ok:
            bad.append(case)

    print("-" * 60)
    if bad:
        print("SELFTEST_RESULT INVALID  无区分力的注入项:", ", ".join(bad))
        return 1
    print("SELFTEST_RESULT VALID  闸门对全部注入项均能 FAIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
