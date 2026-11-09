import json
import math
import os

import numpy as np

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
TMP = os.path.join(ROOT, "workspace", "tmp")
FACE = "MI_R2T1JinxiMd10011Face"
EYE = "MI_R2T1JinxiMd10011Eye"

with open(os.path.join(TMP, "jx14_slots.json"), encoding="utf-8") as fh:
    data = json.load(fh)
verts = np.array(data["vertex_coords"], dtype=np.float64)
face_faces = [[c[0] for c in f] for f in data["uv_faces"][FACE]]
eye_faces = [[c[0] for c in f] for f in data["uv_faces"][EYE]]


def union_find(faces):
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for f in faces:
        for k in range(len(f)):
            union(f[k], f[(k + 1) % len(f)])
    groups = {}
    for v in list(parent):
        groups.setdefault(find(v), []).append(v)
    return sorted(groups.values(), key=lambda g: -len(g))


isl_face = union_find(face_faces)
main = isl_face[0]
main_set = set(main)

edge_count = {}
for f in face_faces:
    for k in range(len(f)):
        a, b = f[k], f[(k + 1) % len(f)]
        e = (a, b) if a < b else (b, a)
        edge_count[e] = edge_count.get(e, 0) + 1
adj_b = {}
for (a, b), c in edge_count.items():
    if c == 1:
        adj_b.setdefault(a, []).append(b)
        adj_b.setdefault(b, []).append(a)
seen = set()
loops = []
for start in adj_b:
    if start in seen:
        continue
    stack = [start]
    comp = []
    seen.add(start)
    while stack:
        v = stack.pop()
        comp.append(v)
        for w in adj_b[v]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
    loops.append(sorted(comp))
loops.sort(key=lambda L: -len(L))

rimL = [L for L in loops if len(L) == 33 and float(np.mean([verts[v][0] for v in L])) < -2.0][0]
rimR = []
for v in rimL:
    p = verts[v]
    tgt = np.array([-p[0], p[1], p[2]])
    d = np.linalg.norm(verts[main] - tgt, axis=1)
    rimR.append(main[int(d.argmin())])
rimR = sorted(set(rimR))
print("RIM", len(rimL), len(rimR))

nbr = {v: set() for v in main}
for f in face_faces:
    if f[0] not in main_set:
        continue
    for k in range(len(f)):
        a, b = f[k], f[(k + 1) % len(f)]
        nbr[a].add(b)
        nbr[b].add(a)


def ring_depth(rim, maxd=2):
    depth = {v: 0 for v in rim}
    frontier = set(rim)
    for d in range(1, maxd + 1):
        nxt = set()
        for v in frontier:
            for w in nbr[v]:
                if w not in depth:
                    depth[w] = d
                    nxt.add(w)
        frontier = nxt
    return depth


CZ = float(np.mean([verts[v][2] for v in rimL]))
UP_ZMAX = 140.56
LO_ZMIN = 138.73


def lid(rim, xe):
    depth = ring_depth(rim, 2)
    up = sorted(v for v, d in depth.items() if d >= 1 and CZ < verts[v][2] <= UP_ZMAX
                and verts[v][1] <= -1.9 and abs(verts[v][0] - xe) <= 1.9)
    lo = sorted(v for v, d in depth.items() if d >= 1 and LO_ZMIN <= verts[v][2] < CZ
                and verts[v][1] <= -1.9 and abs(verts[v][0] - xe) <= 1.9)
    return up, lo


upL, loL = lid(rimL, -3.2)
upR, loR = lid(rimR, 3.2)
lashL = sorted(isl_face[10])
lashR = sorted(isl_face[9])
creaseL = sorted(isl_face[12])
creaseR = sorted(isl_face[13])
browL = sorted(isl_face[5])
browR = sorted(isl_face[6])


def stats(tag, s):
    P = verts[s]
    print("SET", tag, len(s), [round(float(P[:, 0].min()), 3), round(float(P[:, 0].max()), 3)],
          [round(float(P[:, 1].min()), 3), round(float(P[:, 1].max()), 3)],
          [round(float(P[:, 2].min()), 3), round(float(P[:, 2].max()), 3)])


for tag, s in (("UP_L", upL), ("LO_L", loL), ("UP_R", upR), ("LO_R", loR),
               ("LASH_L", lashL), ("LASH_R", lashR), ("CREASE_L", creaseL), ("CREASE_R", creaseR),
               ("BROW_L", browL), ("BROW_R", browR)):
    stats(tag, s)

isl_eye = union_find(eye_faces)
eyeball = {}
for g in isl_eye:
    if len(g) != 109:
        continue
    P = verts[g]
    c = P.mean(axis=0)
    A = np.hstack([2.0 * P, np.ones((len(P), 1))])
    b = (P ** 2).sum(axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    sc = sol[:3]
    r = math.sqrt(sol[3] + float((sc ** 2).sum()))
    side = "L" if c[0] < 0 else "R"
    eyeball[side] = {"verts": sorted(g), "center_dome": [float(x) for x in c],
                     "center_fit": [float(x) for x in sc], "radius_fit": float(r),
                     "y_thickness": float(P[:, 1].max() - P[:, 1].min()),
                     "x_range": [float(P[:, 0].min()), float(P[:, 0].max())],
                     "z_range": [float(P[:, 2].min()), float(P[:, 2].max())]}
    print("EYEBALL", side, len(g), [round(float(x), 3) for x in c],
          "fit_r", round(r, 3), "ythick", round(float(P[:, 1].max() - P[:, 1].min()), 3))

mouth_ap = [L for L in loops if len(L) == 71 and abs(float(np.mean([verts[v][0] for v in L]))) < 0.2][0]
P = verts[mouth_ap]
print("MOUTH_APERTURE", len(mouth_ap), [round(float(c), 3) for c in P.mean(axis=0)],
      [round(float(P[:, 0].min()), 3), round(float(P[:, 0].max()), 3)],
      [round(float(P[:, 1].min()), 3), round(float(P[:, 1].max()), 3)],
      [round(float(P[:, 2].min()), 3), round(float(P[:, 2].max()), 3)])

out = {
    "rimL": rimL, "rimR": rimR,
    "upL": upL, "loL": loL, "upR": upR, "loR": loR,
    "lashL": lashL, "lashR": lashR, "creaseL": creaseL, "creaseR": creaseR,
    "browL": browL, "browR": browR,
    "eyeball": eyeball, "mouth_ap": mouth_ap,
    "isl_eye": [sorted(g) for g in isl_eye],
    "isl_face_sizes": [len(g) for g in isl_face],
}
with open(os.path.join(TMP, "jx14_parts.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(out, fh)
print("PARTS_OUT", os.path.join(TMP, "jx14_parts.json"))