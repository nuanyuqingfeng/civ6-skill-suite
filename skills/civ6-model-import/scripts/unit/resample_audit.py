import argparse
import json
import sys


def build_seq(start, end, out_frames):
    span = end - start
    return [start + int(round(span * i / out_frames)) for i in range(out_frames + 1)]


def audit(start, end, out_frames):
    seq = build_seq(start, end, out_frames)
    dup = sum(1 for a, b in zip(seq, seq[1:]) if a == b)
    steps = sorted({b - a for a, b in zip(seq, seq[1:])})
    return {"dupes": dup, "steps": steps, "frames": len(seq)}


def main():
    parser = argparse.ArgumentParser(
        description="检查动作重采样是否产生重复帧。输出帧数大于源帧区间跨度即必然出现停下再走的节奏。")
    parser.add_argument("--clip", action="append", required=True, metavar="NAME:START:END:OUT",
                        help="片段名:源起始帧:源结束帧:输出帧数，可重复")
    parser.add_argument("--json")
    args = parser.parse_args()

    rows = []
    bad = []
    for spec in args.clip:
        parts = spec.split(":")
        if len(parts) != 4:
            print("参数格式错误：%s，应为 NAME:START:END:OUT" % spec, file=sys.stderr)
            return 2
        name = parts[0]
        start, end, out_frames = (int(x) for x in parts[1:])
        if out_frames <= 0:
            print("输出帧数必须为正：%s" % spec, file=sys.stderr)
            return 2
        r = audit(start, end, out_frames)
        rows.append({"clip": name, "start": start, "end": end,
                     "out": out_frames, "dupes": r["dupes"], "steps": r["steps"]})
        ok = r["dupes"] == 0 and r["steps"] == [1]
        if not ok:
            bad.append(name)
        print("%-20s src=%d..%d out=%d dupes=%-3d steps=%s %s" % (
            name, start, end, out_frames, r["dupes"], r["steps"], "OK" if ok else "FAIL"))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"rows": rows, "bad": bad, "ok": not bad}, fh, ensure_ascii=False, indent=1)
        print("JSON %s" % args.json)
    print("RESAMPLE_AUDIT_%s" % ("OK" if not bad else "FAIL"))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
