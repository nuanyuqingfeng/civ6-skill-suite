import argparse
import math
import os
import subprocess
import sys

REST_ROOT_Q = (0.0, 0.707106769, 0.707106769, 0.0)
REST_HIP_P = (1.0164, 85.3512, 0.0)

DOT_MIN = 0.99999
HIP_TOL = 0.5
POSE_TOL = 2.0


def run(exe, args, timeout=180):
    out = subprocess.run([exe] + args, capture_output=True, timeout=timeout)
    return out.stdout.decode("utf-8-sig", errors="replace")


def parse_table(text):
    rows = []
    header = None
    for line in text.splitlines():
        cells = line.rstrip("\r").split("\t")
        if header is None:
            if "bone" in cells:
                header = [c.strip() for c in cells]
            continue
        if len(cells) < len(header):
            continue
        rows.append({header[i]: cells[i].strip() for i in range(len(header))})
    return rows


def rest_pose(ne, geo):
    rows = parse_table(run(os.path.join(ne, "NexusRestDump.exe"), [geo]))
    table = {}
    for r in rows:
        if "bone" not in r:
            continue
        table[r["bone"]] = {
            "p": (float(r["px"]), float(r["py"]), float(r["pz"])),
            "q": (float(r["q0"]), float(r["q1"]), float(r["q2"]), float(r["q3"])),
        }
    return table


def curve_first(ne, clip):
    text = run(os.path.join(ne, "NexusCurveDump.exe"), [clip])
    found = {}
    current = None
    for line in text.splitlines():
        s = line.strip()
        if s.endswith("knots") or " knots " in s:
            parts = s.split()
            current = parts[0] if parts else None
            continue
        if current is None:
            continue
        if s.startswith("ori(0)="):
            body = s[len("ori(0)="):].split("]")[0].strip(" [")
            found.setdefault(current, {})["q"] = tuple(float(x) for x in body.split(","))
        elif s.startswith("pos(0)="):
            body = s[len("pos(0)="):].split("]")[0].strip(" [")
            found.setdefault(current, {})["p"] = tuple(float(x) for x in body.split(","))
    return found


def posedump(ne, geo, anim, tmpdir, tag):
    out = os.path.join(tmpdir, tag + ".tsv")
    run(os.path.join(ne, "NexusPoseDump.exe"), [geo, anim, out])
    rows = parse_table(open(out, encoding="utf-8-sig").read())
    return {r["bone"]: (float(r["cpx"]), float(r["cpy"]), float(r["cpz"])) for r in rows if "bone" in r}


def norm(v):
    return math.sqrt(sum(x * x for x in v))


def angle_deg(q1, q2):
    n1, n2 = norm(q1), norm(q2)
    if n1 == 0 or n2 == 0:
        return 180.0
    d = abs(sum(a * b for a, b in zip(q1, q2))) / (n1 * n2)
    return math.degrees(2 * math.acos(min(1.0, d)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--ne", default=r"E:\SoftWares\civ6_nexus_work\CivNexus6")
    ap.add_argument("--geo", default=None)
    ap.add_argument("--anim-dir", default=None)
    ap.add_argument("--tmp", default=None)
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    geo = args.geo
    if geo is None:
        geo_dir = os.path.join(project, "Geometries")
        cands = [os.path.join(geo_dir, f) for f in os.listdir(geo_dir)
                 if f.lower().endswith(".fgx") and os.path.isfile(os.path.join(geo_dir, f[:-4] + ".geo"))]
        if not cands:
            print("Geometries 下找不到同时带 .geo 的 fgx，请用 --geo 指定")
            return 2
        geo = max(cands, key=os.path.getsize)

    tmpdir = args.tmp or os.path.join(project, "workspace", "tmp", "anchors")
    os.makedirs(tmpdir, exist_ok=True)

    rest = rest_pose(args.ne, geo)
    if "Root" not in rest or "Bip001" not in rest:
        print("静止姿态缺 Root 或 Bip001，检查 " + geo)
        return 2
    rest_posed = posedump(args.ne, geo, "-", tmpdir, "rest")

    anim_dir = args.anim_dir or os.path.join(project, "Animations")
    clips = sorted(f for f in os.listdir(anim_dir) if f.lower().endswith(".fgx"))
    if not clips:
        print("Animations 目录没有 fgx")
        return 2

    print("clip\tdot_root\tdeg_root\thip_dx\thip_dy\thip_dz\thip_max\tpose_max\thip_deg\tpose_bone\tverdict")
    bad = 0
    for name in clips:
        path = os.path.join(anim_dir, name)
        first = curve_first(args.ne, path)
        root = first.get("Root", {}).get("q")
        hip = first.get("Bip001", {}).get("p")
        if root is None or hip is None:
            print("%s\t-\t-\t-\t-\t-\t-\t-\t-\tMISSING" % name)
            bad += 1
            continue
        nr, ns = norm(root), norm(rest["Root"]["q"])
        dot = 0.0 if nr == 0 or ns == 0 else abs(sum(a * b for a, b in zip(root, rest["Root"]["q"]))) / (nr * ns)
        deg = angle_deg(root, rest["Root"]["q"])
        d = [hip[i] - rest["Bip001"]["p"][i] for i in range(3)]
        hip_max = max(abs(x) for x in d)
        hip_q = first.get("Bip001", {}).get("q")
        hip_ang = 180.0 if hip_q is None else angle_deg(hip_q, rest["Bip001"]["q"])
        posed = posedump(args.ne, geo, path, tmpdir, name.replace(".", "_"))
        worst, who = 0.0, ""
        for bone, pos in posed.items():
            if bone not in rest_posed:
                continue
            dist = math.dist(pos, rest_posed[bone])
            if dist > worst:
                worst, who = dist, bone
        # 只有 A 能区分可用与不可用：可用集实测 dot=1.0（含 Bip001 位移为 0 与等于静止姿态两种），
        # 不可用集实测 dot=0.5（Root 带源骨架 Rz(90°)）。B、C 作诊断打印，不参与判定。
        # TURN_* 片段按设计整体旋转根骨，不参与 A 判定（女漂可用集实测 TURN_L 的 dot=0.0）
        lower = name.lower()
        is_turn = "turn" in lower
        ok = dot >= DOT_MIN or is_turn
        if not ok:
            bad += 1
        note = "SKIP_TURN" if is_turn else ("PASS" if ok else "FAIL")
        if note == "PASS" and (hip_max > HIP_TOL or worst > POSE_TOL):
            note = "PASS_DIAG"
        print("%s\t%.9f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.2f\t%s\t%s" % (
            name, dot, deg, d[0], d[1], d[2], hip_max, worst, hip_ang, who, note))

    print("clips=%d fail=%d" % (len(clips), bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
