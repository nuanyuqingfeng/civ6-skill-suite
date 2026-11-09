import bpy
import os
import json
import math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
MODEL = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
TEXDIR = os.path.join(ROOT, "Jinzhou_Jinhsi", "Textures")
REPORT = os.path.join(ROOT, "workspace", "gen", "reports", "cloth_probe2.json")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images):
    for item in list(block):
        block.remove(item, do_unlink=True)
bpy.ops.import_scene.psk(filepath=MODEL)
body = [o for o in bpy.data.objects if o.type == 'MESH' and len(o.data.vertices) > 100][0]
if body.data.shape_keys:
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.shape_key_remove(all=True)
me = body.data
me.calc_loop_triangles()
mw = body.matrix_world
nmat = mw.to_3x3().inverted().transposed()

V = np.array([list(mw @ v.co) for v in me.vertices], dtype=np.float64)
T = np.array([list(t.vertices) for t in me.loop_triangles], dtype=np.int32)
PMAT = np.array([t.material_index for t in me.loop_triangles], dtype=np.int32)
TN = np.array([list((nmat @ me.polygons[t.polygon_index].normal).normalized()) for t in me.loop_triangles], dtype=np.float64)
SLOT = [s.material.name if s.material else "-" for s in body.material_slots]
a = V[T[:, 0]]
b = V[T[:, 1]]
c = V[T[:, 2]]
AREA = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)

poly_uv = np.zeros((len(me.polygons), 2), dtype=np.float64)
uvl = me.uv_layers.active.data
for p in me.polygons:
    acc = np.zeros(2)
    for li in range(p.loop_start, p.loop_start + p.loop_total):
        acc += np.array(uvl[li].uv[:])
    poly_uv[p.index] = acc / p.loop_total
TRI_UV = poly_uv[[t.polygon_index for t in me.loop_triangles]]

def load_img(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    arr = buf.reshape(h, w, 4).copy()
    bpy.data.images.remove(img)
    return arr

def sample(arr, uv):
    h, w, _ = arr.shape
    u = float(min(max(uv[0], 0.0), 0.999999))
    v = float(min(max(uv[1], 0.0), 0.999999))
    return arr[int(v * h), int(u * w)]

tex_down = load_img(os.path.join(TEXDIR, "MI_R2T1JinxiMd10011Down_BaseColor.dds"))
tex_skirt = load_img(os.path.join(TEXDIR, "MI_R2T1JinxiMd10011Skirt_BaseColor.dds"))
mask_cloth = load_img(os.path.join(TEXDIR, "JINHSI_LEADER_OPACITY_CLOTH.dds"))
tex_skin = load_img(os.path.join(TEXDIR, "MI_R2T1JinxiMd10011Face_BaseColor.dds"))

poly_col = np.ones((len(me.polygons), 4), dtype=np.float64)
for p in me.polygons:
    name = SLOT[p.material_index]
    if "Down" in name:
        poly_col[p.index] = sample(tex_down, poly_uv[p.index])
    elif "Skirt" in name:
        poly_col[p.index] = sample(tex_skirt, poly_uv[p.index])
    elif "Face" in name or "Hair" in name or "Bangs" in name or "Eye" in name:
        poly_col[p.index] = sample(tex_skin, poly_uv[p.index])
TRI_COL = poly_col[[t.polygon_index for t in me.loop_triangles]]
TRI_LUM = 0.2126 * TRI_COL[:, 0] + 0.7152 * TRI_COL[:, 1] + 0.0722 * TRI_COL[:, 2]
TRI_MASK = np.array([sample(mask_cloth, TRI_UV[i])[3] for i in range(len(TRI_UV))], dtype=np.float64)

parent = np.arange(len(T), dtype=np.int32)
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(x, y):
    rx, ry = find(x), find(y)
    if rx != ry:
        parent[ry] = rx
owner = {}
for i, tri in enumerate(T):
    for e in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
        key = (min(e), max(e))
        if key in owner:
            union(owner[key], i)
        else:
            owner[key] = i
roots = np.array([find(i) for i in range(len(T))], dtype=np.int32)

bvh = BVHTree.FromPolygons([Vector(v) for v in V], [tuple(int(x) for x in tri) for tri in T], all_triangles=True)

def trace(origin, direction, max_layers=8):
    hits = []
    t = 0.0
    for _ in range(max_layers):
        loc, nrm, tri_i, dist = bvh.ray_cast(Vector(origin) + Vector(direction) * t, Vector(direction))
        if loc is None:
            break
        hits.append((t + dist, int(tri_i)))
        t = t + dist + 0.02
    return hits

def visible_ortho(step):
    xs = np.arange(-30.0, 30.0 + step, step)
    zs = np.arange(40.0, 140.0 + step, step)
    rows = []
    culled = 0
    total = 0
    for z in zs:
        for x in xs:
            total += 1
            hits = trace((float(x), -80.0, float(z)), (0.0, 1.0, 0.0))
            shown = None
            skipped = 0
            for dist, ti in hits:
                if TN[ti] @ np.array([0.0, -1.0, 0.0]) > 0.0:
                    shown = (dist, ti, skipped)
                    break
                skipped += 1
            if shown is not None and shown[2] > 0:
                culled += 1
            if shown is not None:
                rows.append((round(float(x), 2), round(float(z), 2), shown[1], shown[2]))
    return rows, total, culled

ROWS, TOTAL, CULLED = visible_ortho(0.5)
print("VIS_CELLS", TOTAL, "CULLED_CHANGED", CULLED)

def aggregate(rows):
    acc = {}
    dark = 0.0
    dark_by_z = {}
    for x, z, ti, sk in rows:
        key = (int(PMAT[ti]), int(roots[ti]))
        d = acc.setdefault(key, {"cells": 0, "material": SLOT[PMAT[ti]], "lum": round(float(TRI_LUM[ti]), 3),
                                 "zmin": 999.0, "zmax": -999.0, "xmin": 999.0, "xmax": -999.0})
        d["cells"] += 1
        d["zmin"] = min(d["zmin"], z)
        d["zmax"] = max(d["zmax"], z)
        d["xmin"] = min(d["xmin"], x)
        d["xmax"] = max(d["xmax"], x)
        if TRI_LUM[ti] < 0.25:
            dark += 1
            band = "z%03d" % int(z // 5 * 5)
            dark_by_z[band] = dark_by_z.get(band, 0) + 1
    out = []
    for key, d in acc.items():
        out.append({"mat": d["material"], "island": key[1], "cells": d["cells"],
                    "lum": d["lum"], "bbox": [d["xmin"], d["zmin"], d["xmax"], d["zmax"]]})
    out.sort(key=lambda r: -r["cells"])
    return out, dark, dark_by_z

agg, dark_cells, dark_by_z = aggregate(ROWS)
print("VISIBLE_TOP")
for r in agg[:18]:
    print("VIS", r["mat"], r["island"], r["cells"], r["lum"], r["bbox"])
print("DARK_CELLS", dark_cells, "OF", len(ROWS), "BY_Z", json.dumps(dark_by_z, sort_keys=True))

def visible_persp(cam, target):
    camv = Vector(cam)
    tgt = Vector(target)
    base = (tgt - camv)
    dist = base.length
    d = base.normalized()
    up = Vector((0.0, 0.0, 1.0))
    right = d.cross(up).normalized()
    up2 = right.cross(d).normalized()
    rows = []
    n = 60
    for iz in range(n):
        for ix in range(n):
            u = (ix / (n - 1.0) - 0.5) * 0.20
            v = (iz / (n - 1.0) - 0.5) * 0.36
            dirv = (d + right * u + up2 * v).normalized()
            hits = trace(camv, dirv)
            shown = None
            skipped = 0
            for dv, ti in hits:
                if TN[ti].dot(-dirv) > 0.0:
                    shown = (dv, ti, skipped)
                    break
                skipped += 1
            if shown is not None:
                rows.append((0.0, 0.0, shown[1], shown[2]))
    return rows

for cam, tgt, tag in [((0.0, -260.0, 142.0), (0.0, 0.0, 112.0), "eye142"),
                      ((0.0, -260.0, 105.0), (0.0, 0.0, 105.0), "chest105")]:
    rows = visible_persp(cam, tgt)
    ag, dk, dz = aggregate(rows)
    print("PERSP", tag, "cells", len(rows), "dark", dk, "top", [(r["mat"][-12:], r["cells"], r["lum"]) for r in ag[:6]])

mask_stats = {
    "cloth_mask_alpha_mean": round(float(mask_cloth[:, :, 3].mean()), 4),
    "cloth_mask_frac_lt_0.5": round(float((mask_cloth[:, :, 3] < 0.5).mean()), 4),
    "cloth_mask_frac_lt_0.05": round(float((mask_cloth[:, :, 3] < 0.05).mean()), 4),
}
sk = PMAT == 4
mask_stats["skirt_area_frac_mask_lt_0.5"] = round(float(AREA[sk & (TRI_MASK < 0.5)].sum() / AREA[sk].sum()), 4)
mask_stats["skirt_area_frac_mask_lt_0.05"] = round(float(AREA[sk & (TRI_MASK < 0.05)].sum() / AREA[sk].sum()), 4)
print("MASK", json.dumps(mask_stats))

uv_over = {}
for idx, name in enumerate(SLOT):
    m = PMAT == idx
    if not m.any():
        continue
    uv = TRI_UV[m]
    over = ((uv < -1e-6) | (uv > 1.0 + 1e-6)).any(axis=1)
    uv_over[name] = {"tris": int(m.sum()), "outside_frac": round(float(over.mean()), 4)}
print("UV", json.dumps(uv_over, ensure_ascii=False))

deg = AREA < 1e-6
print("DEGENERATE", int(deg.sum()), "AREA", round(float(AREA[deg].sum()), 6))

cent = (a + b + c) / 3.0
key = np.round(cent / 0.05).astype(np.int64)
groups = {}
for i in range(len(T)):
    groups.setdefault((int(key[i, 0]), int(key[i, 1]), int(key[i, 2])), []).append(i)
opp_pairs = 0
opp_min = []
for k, ids in groups.items():
    if len(ids) < 2:
        continue
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            ti, tj = ids[i], ids[j]
            if TN[ti].dot(TN[tj]) < -0.9 and AREA[ti] > 1e-4 and AREA[tj] > 1e-4:
                opp_pairs += 1
                opp_min.append(float(np.linalg.norm(cent[ti] - cent[tj])))
print("COINCIDENT_OPPOSED", opp_pairs, "MED_DIST", round(float(np.median(opp_min)), 4) if opp_min else None)

light_ids = np.where((TRI_LUM > 0.5) & ((PMAT == 3) | (PMAT == 4)))[0]
dark_ids = np.where((TRI_LUM < 0.25) & ((PMAT == 3) | (PMAT == 4)))[0]
lv = np.unique(T[light_ids].reshape(-1))
dv = np.unique(T[dark_ids].reshape(-1))
kd = KDTree(len(dv))
for i, vi in enumerate(dv):
    kd.insert(Vector(V[vi]), i)
kd.balance()
near = []
for vi in lv:
    co, ind, dd = kd.find(Vector(V[vi]))
    near.append(dd)
near = np.array(near)
print("LIGHT_TO_DARK_VERTS", len(near), "p10", round(float(np.percentile(near, 10)), 3),
      "median", round(float(np.median(near)), 3), "frac_lt_0.5cm", round(float((near < 0.5).mean()), 3))

with open(REPORT, "w", encoding="utf-8") as f:
    json.dump({"visible": agg[:60], "dark_cells": dark_cells, "visible_cells": len(ROWS),
               "culled_changed": CULLED, "dark_by_z": dark_by_z, "mask": mask_stats,
               "uv": uv_over, "coincident_opposed": opp_pairs,
               "light_dark_vertex_gap": {"p10": round(float(np.percentile(near, 10)), 3),
                                          "median": round(float(np.median(near)), 3),
                                          "frac_lt_0_5": round(float((near < 0.5).mean()), 3)}},
              f, ensure_ascii=False, indent=1)
print("PROBE2_OK", REPORT)
