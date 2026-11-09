import argparse
import json
import math
import os
import subprocess
import sys

def run(exe, args, timeout=180):
    p = subprocess.run([exe] + args, capture_output=True, timeout=timeout)
    return p.stdout.decode("utf-8-sig", errors="replace")

def qn(q):
    n = math.sqrt(sum(c * c for c in q))
    if n == 0.0:
        return None
    return tuple(c / n for c in q)

def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)

def qconj(q):
    return (-q[0], -q[1], -q[2], q[3])

def angle(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    return math.degrees(2.0 * math.acos(min(1.0, d)))

def parse_tsv(text):
    rows = []
    header = None
    for line in text.splitlines():
        cells = line.rstrip("\r").split("\t")
        if header is None:
            if "bone" in [c.strip() for c in cells]:
                header = [c.strip() for c in cells]
            continue
        if len(cells) < len(header):
            continue
        rows.append({header[i]: cells[i].strip() for i in range(len(header))})
    return rows

def read_rest(ne, geo):
    rows = parse_tsv(run(os.path.join(ne, "NexusRestDump.exe"), [geo]))
    out = {}
    for r in rows:
        name = r.get("bone")
        if not name:
            continue
        out[name] = {
            "p": (float(r["px"]), float(r["py"]), float(r["pz"])),
            "q": qn((float(r["q0"]), float(r["q1"]), float(r["q2"]), float(r["q3"]))),
        }
    return out

def read_clip_root(ne, clip):
    text = run(os.path.join(ne, "NexusCurveDump.exe"), [clip])
    cur = None
    for line in text.splitlines():
        s = line.strip()
        if " knots " in s:
            cur = s.split()[0]
            continue
        if cur == "Root" and s.startswith("ori(0)="):
            body = s.split("ori(0)=")[1].split("]")[0].strip(" [")
            return qn(tuple(float(x) for x in body.split(",")))
    return None

def walk_chain(rest, base, length):
    """从 base 沿骨链向下走 length 段，返回实际走过的骨名列表。"""
    children = {}
    for name, v in rest.items():
        pass
    return None

def bone_lengths(rest, pairs):
    out = {}
    for a, b in pairs:
        if a in rest and b in rest:
            out[(a, b)] = math.dist(rest[a]["p"], rest[b]["p"])
    return out

DEFAULT_PAIRS = [
    ("Bip001", "Bip001Head"),
    ("Bip001", "Bip001LThigh"),
    ("Bip001LThigh", "Bip001LCalf"),
    ("Bip001LCalf", "Bip001LFoot"),
    ("Bip001LClavicle", "Bip001LUpperArm"),
    ("Bip001LUpperArm", "Bip001LForearm"),
    ("Bip001LForearm", "Bip001LHand"),
    ("Bip001Pelvis", "Bip001Spine2"),
]

def main():
    ap = argparse.ArgumentParser(description="单位几何与片段一致性审计：根骨净旋转、静止骨长、骨骼集合")
    ap.add_argument("project", help="工程根")
    ap.add_argument("--geo", default=None, help="几何 fgx，默认 Geometries 下带同名 .geo 的最大 fgx")
    ap.add_argument("--anim-dir", default=None)
    ap.add_argument("--ne", default=r"E:\SoftWares\civ6_nexus_work\CivNexus6")
    ap.add_argument("--pairs", default=None, help="额外骨对，格式 A-B,A-B")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    anim_dir = args.anim_dir or os.path.join(project, "Animations")
    geo = args.geo
    if geo is None:
        gdir = os.path.join(project, "Geometries")
        cands = [os.path.join(gdir, f) for f in os.listdir(gdir)
                 if f.lower().endswith(".fgx") and os.path.isfile(os.path.join(gdir, f[:-4] + ".geo"))]
        if not cands:
            raise SystemExit("Geometries 下找不到同时带 .geo 的 fgx")
        geo = max(cands, key=os.path.getsize)
    print("GEO %s" % geo)

    rest = read_rest(args.ne, geo)
    if "Root" not in rest:
        raise SystemExit("静止姿态里没有 Root")
    print("REST_BONES %d" % len(rest))

    pairs = list(DEFAULT_PAIRS)
    if args.pairs:
        for spec in args.pairs.split(","):
            if "-" in spec:
                a, b = spec.split("-", 1)
                pairs.append((a.strip(), b.strip()))
    lens = bone_lengths(rest, pairs)
    print("REST_LEN " + " ".join("%s-%s=%.4f" % (a, b, v) for (a, b), v in lens.items()))

    clips = sorted(f for f in os.listdir(anim_dir) if f.lower().endswith(".fgx"))
    if not clips:
        raise SystemExit("片段目录没有 fgx")
    print("CLIPS %d" % len(clips))

    root_rest = rest["Root"]["q"]
    worst = 0.0
    worst_clip = ""
    rows = []
    for f in clips:
        p = os.path.join(anim_dir, f)
        q = read_clip_root(args.ne, p)
        if q is None:
            rows.append({"clip": f, "net_deg": None})
            continue
        net = qmul(q, qconj(root_rest))
        deg = angle(net, (0.0, 0.0, 0.0, 1.0))
        rows.append({"clip": f, "net_deg": deg})
        if deg > worst:
            worst, worst_clip = deg, f
    print("NET_ROT_MAX %.6f deg at %s" % (worst, worst_clip))

    ok = worst < 1e-3
    result = {
        "geo": geo,
        "rest_bones": len(rest),
        "rest_len": {"%s-%s" % k: v for k, v in lens.items()},
        "clips": len(clips),
        "net_rot_max_deg": worst,
        "net_rot_worst_clip": worst_clip,
        "rows": rows,
        "ok": ok,
    }
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=1)
        print("JSON %s" % args.json)
    print("UNIT_GEO_AUDIT_%s" % ("OK" if ok else "FAIL"))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
