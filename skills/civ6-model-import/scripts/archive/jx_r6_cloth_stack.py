import bpy
import os
import json
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
MODEL = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
TEXDIR = os.path.join(ROOT, "Jinzhou_Jinhsi", "Textures")
REPORT = os.path.join(ROOT, "workspace", "gen", "reports", "cloth_probe5.json")

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
CENT = (a + b + c) / 3.0
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
poly_col = np.ones((len(me.polygons), 4), dtype=np.float64)
for p in me.polygons:
    name = SLOT[p.material_index]
    if "Down" in name:
        poly_col[p.index] = sample(tex_down, poly_uv[p.index])
    elif "Skirt" in name:
        poly_col[p.index] = sample(tex_skirt, poly_uv[p.index])
TRI_COL = poly_col[[t.polygon_index for t in me.loop_triangles]]
TRI_LUM = 0.2126 * TRI_COL[:, 0] + 0.7152 * TRI_COL[:, 1] + 0.0722 * TRI_COL[:, 2]
GARMENT = (PMAT == 3) | (PMAT == 4)

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

def trace(origin, direction, max_layers=6):
    hits = []
    t = 0.0
    for _ in range(max_layers):
        loc, nrm, tri_i, dist = bvh.ray_cast(Vector(origin) + Vector(direction) * t, Vector(direction))
        if loc is None:
            break
        hits.append((t + dist, int(tri_i)))
        t = t + dist + 0.02
    return hits

def classify(x, z):
    hits = trace((x, -80.0, z), (0.0, 1.0, 0.0))
    seq = []
    for dist, ti in hits:
        if TN[ti][1] > 0.0 and GARMENT[ti]:
            seq.append((dist, ti))
    if not seq:
        return "empty", None
    d0, t0 = seq[0]
    dark0 = TRI_LUM[t0] < 0.25
    for d1, t1 in seq[1:]:
        gap = d1 - d0
        if dark0 and TRI_LUM[t1] >= 0.5 and gap < 3.0:
            return "black_in_front_of_light", gap
        if (not dark0) and dark0 is False and TRI_LUM[t1] < 0.25 and gap < 0.5:
            return "light_over_black_close", gap
        if (not dark0) and TRI_LUM[t1] < 0.25:
            return "light_over_black", gap
        break
    if dark0:
        return "black_exposed", None
    return "light_only", None

grid = {}
for z in np.arange(96.0, 130.01, 0.5):
    for x in np.arange(-13.0, 13.01, 0.5):
        cls, gap = classify(float(x), float(z))
        d = grid.setdefault(cls, {"cells": 0, "gaps": []})
        d["cells"] += 1
        if gap is not None:
            d["gaps"].append(round(float(gap), 3))
print("CHEST_GRID_CELLS", sum(v["cells"] for v in grid.values()))
for k, v in sorted(grid.items()):
    g = np.array(v["gaps"]) if v["gaps"] else None
    print("CLS", k, v["cells"], "area_cm2", round(v["cells"] * 0.25, 1),
          ("gap_p50=%0.3f" % float(np.median(g))) if g is not None and len(g) else "",
          ("gap_min=%0.3f" % float(g.min())) if g is not None and len(g) else "")

def whole_front():
    counts = {}
    for z in np.arange(40.0, 140.01, 0.5):
        for x in np.arange(-40.0, 40.01, 0.5):
            hits = trace((float(x), -120.0, float(z)), (0.0, 1.0, 0.0))
            seq = []
            for dist, ti in hits:
                if TN[ti][1] > 0.0:
                    seq.append((dist, ti))
            if not seq:
                continue
            d0, t0 = seq[0]
            key = "one_layer"
            if len(seq) > 1 and seq[1][0] - d0 < 0.2:
                key = "two_layers_lt_0.2"
            elif len(seq) > 1 and seq[1][0] - d0 < 0.5:
                key = "two_layers_lt_0.5"
            counts[key] = counts.get(key, 0) + 1
    return counts

fc = whole_front()
print("WHOLE_FRONT", json.dumps(fc))

with open(REPORT, "w", encoding="utf-8") as f:
    json.dump({"chest": {k: {"cells": v["cells"],
                             "gap_median": round(float(np.median(v["gaps"])), 3) if v["gaps"] else None,
                             "gap_min": round(float(min(v["gaps"])), 3) if v["gaps"] else None}
                        for k, v in grid.items()},
               "whole_front": fc}, f, ensure_ascii=False, indent=1)
print("PROBE5_OK")
