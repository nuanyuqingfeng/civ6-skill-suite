import bpy
import os
import json
import math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
MODEL = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
TEXDIR = os.path.join(ROOT, "Jinzhou_Jinhsi", "Textures")
REPORT = os.path.join(ROOT, "workspace", "gen", "reports", "cloth_probe.json")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images):
    for item in list(block):
        block.remove(item, do_unlink=True)

bpy.ops.import_scene.psk(filepath=MODEL)
body = None
for o in bpy.data.objects:
    if o.type == 'MESH' and len(o.data.vertices) > 100:
        body = o
print("BODY", body.name)
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
cross = np.cross(b - a, c - a)
AREA = 0.5 * np.linalg.norm(cross, axis=1)

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
    arr = buf.reshape(h, w, 4)
    bpy.data.images.remove(img)
    return arr

def sample(arr, uv):
    h, w, _ = arr.shape
    u = float(min(max(uv[0], 0.0), 0.999999))
    v = float(min(max(uv[1], 0.0), 0.999999))
    x = int(u * w)
    y = int(v * h)
    return arr[y, x]

tex_down = load_img(os.path.join(TEXDIR, "MI_R2T1JinxiMd10011Down_BaseColor.dds"))
tex_skirt = load_img(os.path.join(TEXDIR, "MI_R2T1JinxiMd10011Skirt_BaseColor.dds"))
mask_cloth = load_img(os.path.join(TEXDIR, "JINHSI_LEADER_OPACITY_CLOTH.dds"))
tex_bangs = load_img(os.path.join(TEXDIR, "MI_R2T1JinxiMd10011Bangs_BaseColor.dds"))
print("TEX", tex_down.shape, tex_skirt.shape, mask_cloth.shape, tex_bangs.shape)

poly_col = np.ones((len(me.polygons), 4), dtype=np.float64)
for p in me.polygons:
    midx = p.material_index
    if midx >= len(SLOT):
        continue
    name = SLOT[midx]
    if "Down" in name:
        poly_col[p.index] = sample(tex_down, poly_uv[p.index])
    elif "Skirt" in name:
        poly_col[p.index] = sample(tex_skirt, poly_uv[p.index])
    elif "Bangs" in name:
        poly_col[p.index] = sample(tex_bangs, poly_uv[p.index])
TRI_COL = poly_col[[t.polygon_index for t in me.loop_triangles]]
TRI_MASK = np.array([sample(mask_cloth, TRI_UV[i])[3] for i in range(len(TRI_UV))], dtype=np.float64)

def edges_of(tri):
    return ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0]))

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
    for e in edges_of(tri):
        key = (min(e), max(e))
        if key in owner:
            union(owner[key], i)
        else:
            owner[key] = i
roots = np.array([find(i) for i in range(len(T))], dtype=np.int32)

FRONT = np.array([0.0, -1.0, 0.0])
TN_DOT_FRONT = TN @ FRONT

def isl_stats(mask):
    idx = np.where(mask)[0]
    groups = {}
    for i in idx:
        groups.setdefault(int(roots[i]), []).append(i)
    out = []
    for r, ids in groups.items():
        ids = np.array(ids)
        vs = np.unique(T[ids].reshape(-1))
        mins = V[vs].min(axis=0)
        maxs = V[vs].max(axis=0)
        area = float(AREA[ids].sum())
        col = TRI_COL[ids][:, :3].mean(axis=0)
        front = float(AREA[ids][TN_DOT_FRONT[ids] > 0.3].sum())
        back = float(AREA[ids][TN_DOT_FRONT[ids] < -0.3].sum())
        out.append({
            "tris": int(len(ids)),
            "verts": int(len(vs)),
            "area": round(area, 2),
            "bbox": [round(float(x), 2) for x in list(mins) + list(maxs)],
            "rgb": [round(float(x), 3) for x in col],
            "lum": round(float(0.2126 * col[0] + 0.7152 * col[1] + 0.0722 * col[2]), 3),
            "front_area": round(front, 2),
            "back_area": round(back, 2),
        })
    out.sort(key=lambda d: -d["area"])
    return out

result = {"slots": []}
for idx, name in enumerate(SLOT):
    m = PMAT == idx
    area = float(AREA[m].sum())
    fr = float(AREA[m & (TN_DOT_FRONT > 0.3)].sum())
    bk = float(AREA[m & (TN_DOT_FRONT < -0.3)].sum())
    result["slots"].append({
        "index": idx, "name": name,
        "tris": int(m.sum()), "area": round(area, 2),
        "front_area": round(fr, 2), "back_area": round(bk, 2),
    })
print("SLOTSTAT", json.dumps(result["slots"], ensure_ascii=False))

isl_down = isl_stats(PMAT == 3)
isl_skirt = isl_stats(PMAT == 4)
result["down_islands_top"] = isl_down[:25]
result["skirt_islands_top"] = isl_skirt[:15]
print("DOWN_ISLANDS", len(isl_down), "SKIRT_ISLANDS", len(isl_skirt))
for d in isl_down[:12]:
    print("DI", d["tris"], d["area"], d["bbox"], d["lum"], d["front_area"], d["back_area"])

poly_idx = np.array([t.polygon_index for t in me.loop_triangles], dtype=np.int32)
bvh = BVHTree.FromPolygons([Vector(v) for v in V], [tuple(int(x) for x in tri) for tri in T], all_triangles=True)

ray_rows = []
xs = np.arange(-14.0, 14.01, 1.0)
zs = np.arange(84.0, 136.01, 1.0)
for z in zs:
    for x in xs:
        origin = Vector((float(x), -70.0, float(z)))
        direction = Vector((0.0, 1.0, 0.0))
        t0 = 0.0
        hits = []
        for k in range(6):
            loc, nrm, tri_i, dist = bvh.ray_cast(origin + direction * t0, direction)
            if loc is None:
                break
            hits.append({"t": round(float(t0 + dist), 3), "tri": int(tri_i),
                         "mat": int(PMAT[tri_i]),
                         "ndot": round(float(TN[tri_i] @ (-direction)), 3),
                         "rgb": [round(float(x), 3) for x in TRI_COL[tri_i][:3]]})
            t0 = t0 + dist + 0.02
        ray_rows.append({"x": round(float(x), 1), "z": round(float(z), 1), "hits": hits})
print("RAYS", len(ray_rows))

def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

rays_filled = 0
first_down_front = 0
first_down_back = 0
first_other = 0
gap_pairs = []
band = {}
for row in ray_rows:
    key = "z%02d" % int(row["z"] // 5 * 5)
    b = band.setdefault(key, {"rays": 0, "backfirst": 0, "otherfirst": 0, "empty": 0})
    b["rays"] += 1
    if not row["hits"]:
        b["empty"] += 1
        continue
    h0 = row["hits"][0]
    if h0["mat"] in (3, 4):
        if h0["ndot"] > 0:
            first_down_front += 1
        else:
            first_down_back += 1
            b["backfirst"] += 1
    else:
        first_other += 1
        b["otherfirst"] += 1
    for i in range(len(row["hits"]) - 1):
        h1 = row["hits"][i]
        h2 = row["hits"][i + 1]
        if h1["mat"] in (3, 4) and lum(h1["rgb"]) > 0.45 and lum(h2["rgb"]) < 0.22:
            gap_pairs.append(round(h2["t"] - h1["t"], 3))
print("FIRST down_front", first_down_front, "down_back", first_down_back, "other", first_other)
print("BANDS", json.dumps(band, ensure_ascii=False))
if gap_pairs:
    gp = np.array(gap_pairs)
    print("GAP n", len(gp), "min", gp.min(), "p10", np.percentile(gp, 10), "median", np.median(gp), "max", gp.max())

result["rays_summary"] = {
    "count": len(ray_rows),
    "first_garment_front": first_down_front,
    "first_garment_back": first_down_back,
    "first_other": first_other,
    "bands": band,
    "light_to_dark_gap_cm": {
        "n": len(gap_pairs),
        "min": round(float(min(gap_pairs)), 3) if gap_pairs else None,
        "median": round(float(np.median(gap_pairs)), 3) if gap_pairs else None,
        "max": round(float(max(gap_pairs)), 3) if gap_pairs else None,
    },
}
with open(REPORT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print("PROBE_STAGE1_OK", REPORT)
