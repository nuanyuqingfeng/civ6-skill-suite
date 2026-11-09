import bpy
import os
import json
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
MODEL = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
TEXDIR = os.path.join(ROOT, "Jinzhou_Jinhsi", "Textures")
REPORT = os.path.join(ROOT, "workspace", "gen", "reports", "cloth_probe3.json")

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

poly_col = np.ones((len(me.polygons), 4), dtype=np.float64)
for p in me.polygons:
    name = SLOT[p.material_index]
    if "Down" in name:
        poly_col[p.index] = sample(tex_down, poly_uv[p.index])
    elif "Skirt" in name:
        poly_col[p.index] = sample(tex_skirt, poly_uv[p.index])
TRI_COL = poly_col[[t.polygon_index for t in me.loop_triangles]]
TRI_LUM = 0.2126 * TRI_COL[:, 0] + 0.7152 * TRI_COL[:, 1] + 0.0722 * TRI_COL[:, 2]

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

black_island = 22172
rows = []
for z in np.arange(106.0, 124.5, 1.5):
    for x in np.arange(-8.0, 8.5, 1.5):
        hits = trace((float(x), -80.0, float(z)), (0.0, 1.0, 0.0))
        seq = []
        for dist, ti in hits[:4]:
            seq.append({"d": round(float(dist), 2), "mat": SLOT[PMAT[ti]].replace("MI_R2T1JinxiMd10011", ""),
                        "isl": int(roots[ti]), "lum": round(float(TRI_LUM[ti]), 2),
                        "nd": round(float(TN[ti][1] * -1.0), 2), "y": round(float(V[T[ti]][:, 1].mean()), 2)})
        rows.append({"x": round(float(x), 1), "z": round(float(z), 1), "seq": seq})

print("SEQ_ROWS")
for r in rows:
    if r["seq"]:
        print("SEQ", r["x"], r["z"], json.dumps(r["seq"][:3], ensure_ascii=False))

target = PMAT == 3
isl = target & (roots == black_island)
print("BLACK_ISLAND", int(isl.sum()), "area", round(float(AREA[isl].sum()), 2),
      "bbox", [round(float(v), 2) for v in list(V[np.unique(T[isl].reshape(-1))].min(axis=0)) + list(V[np.unique(T[isl].reshape(-1))].max(axis=0))])

def gap_behind_black():
    ds = []
    for r in rows:
        if not r["seq"]:
            continue
        if r["seq"][0]["isl"] == black_island:
            for h in r["seq"][1:]:
                if h["isl"] != black_island:
                    ds.append(round(h["d"] - r["seq"][0]["d"], 2))
                    break
    return ds

ds = gap_behind_black()
print("BEHIND_BLACK_GAPS", ds[:20], "n", len(ds), "median", round(float(np.median(ds)), 2) if ds else None)

def normal_audit():
    flipped = 0
    total_area = 0.0
    for p in me.polygons:
        ns = []
        for vi in p.vertices:
            ns.append(me.vertices[vi].normal)
        avg = Vector((0.0, 0.0, 0.0))
        for n in ns:
            avg += n
        if avg.length > 1e-9 and p.normal.dot(avg.normalized()) < 0.0:
            flipped += 1
            total_area += p.area
    return flipped, round(total_area, 2)

flipped, flipped_area = normal_audit()
print("FLIPPED_FACES", flipped, "AREA", flipped_area)

light_chest = (roots == 30436)
print("LIGHT_CHEST_ISLAND", int(light_chest.sum()), round(float(AREA[light_chest].sum()), 2),
      "front", round(float(AREA[light_chest & (TN[:, 1] < -0.3)].sum()), 2),
      "back", round(float(AREA[light_chest & (TN[:, 1] > 0.3)].sum()), 2))

def planarity(isl_mask):
    ids = np.where(isl_mask)[0]
    vs = np.unique(T[ids].reshape(-1))
    p = V[vs]
    ctr = p.mean(axis=0)
    q = p - ctr
    u, s, vt = np.linalg.svd(q, full_matrices=False)
    normal = vt[2]
    dev = np.abs(q @ normal)
    return {"verts": int(len(vs)), "plane_dev_p50": round(float(np.percentile(dev, 50)), 3),
            "plane_dev_p95": round(float(np.percentile(dev, 95)), 3),
            "plane_dev_max": round(float(dev.max()), 3)}

print("PLANAR_LIGHT_CHEST", json.dumps(planarity(light_chest), ensure_ascii=False))
print("PLANAR_BLACK", json.dumps(planarity(isl), ensure_ascii=False))

alphas = tex_down[:, :, 3]
print("DOWN_ALPHA min", round(float(alphas.min()), 4), "mean", round(float(alphas.mean()), 4),
      "frac_lt_0.5", round(float((alphas < 0.5).mean()), 5))
sa = tex_skirt[:, :, 3]
print("SKIRT_ALPHA min", round(float(sa.min()), 4), "mean", round(float(sa.mean()), 4),
      "frac_lt_0.5", round(float((sa < 0.5).mean()), 5))

edge_uv = TRI_UV[light_chest]
h, w = tex_down.shape[0], tex_down.shape[1]
al = np.array([sample(tex_down, uv)[3] for uv in edge_uv])
print("LIGHT_UV_ALPHA min", round(float(al.min()), 4), "frac_lt_0.5", round(float((al < 0.5).mean()), 5))

uvs = TRI_UV[light_chest]
print("LIGHT_UV_RANGE", [round(float(uvs[:, 0].min()), 3), round(float(uvs[:, 0].max()), 3),
                          round(float(uvs[:, 1].min()), 3), round(float(uvs[:, 1].max()), 3)])

with open(REPORT, "w", encoding="utf-8") as f:
    json.dump({"seq": rows, "black_island": black_island, "behind_black_gaps": ds,
               "flipped_faces": flipped, "flipped_area": flipped_area,
               "light_chest": planarity(light_chest), "black_planar": planarity(isl),
               "down_alpha": [round(float(alphas.min()), 4), round(float(alphas.mean()), 4)],
               "light_uv_alpha_min": round(float(al.min()), 4)}, f, ensure_ascii=False, indent=1)
print("PROBE3_OK", REPORT)
