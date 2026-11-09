import math
import os

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace"
CURVE = os.path.join(ROOT, "tmp", "bonecurve_calib.tsv")
TABLE = os.path.join(ROOT, "gen", "reports", "anim_channel_map.tsv")
EPS_ANGLE = math.radians(0.01)
eps = (math.sin(EPS_ANGLE / 2.0), 0.0, 0.0, math.cos(EPS_ANGLE / 2.0))


def q_conj(q):
    return (-q[0], -q[1], -q[2], q[3])


def q_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def parse(path):
    rows = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("BC "):
                continue
            f = line.split()
            name = f[1]
            p = [float(f[2]), float(f[3]), float(f[4])]
            q = [float(f[5]), float(f[6]), float(f[7]), float(f[8])]
            rows[name] = (p, q)
    return rows


def load_table(path):
    table = set()
    with open(path, encoding="utf-8") as fh:
        fh.readline()
        for line in fh:
            table.add(line.split("\t")[0])
    return table


curves = parse(CURVE)
table = load_table(TABLE)
missing = [n for n in curves if n.startswith("JX_") and n not in table]
print("CURVE_BONES", len(curves), "TABLE_BONES", len(table), "MISSING_JX", missing)
assert missing, "no missing bone"
with open(TABLE, "a", encoding="utf-8", newline="\n") as fh:
    for name in sorted(missing):
        p, q = curves[name]
        base_q = q_mul(q, q_conj(eps))
        n = math.sqrt(sum(v * v for v in base_q))
        base_q = tuple(v / n for v in base_q)
        fh.write("%s\t%.6f\t%.6f\t%.6f\t%.9f\t%.9f\t%.9f\t%.9f\n" % (
            name, p[0], p[1], p[2], base_q[0], base_q[1], base_q[2], base_q[3]))
print("APPENDED", len(missing))
