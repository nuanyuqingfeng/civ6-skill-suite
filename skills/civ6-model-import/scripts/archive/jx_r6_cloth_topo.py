import bpy
import os
import json
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
MODEL = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
TEXDIR = os.path.join(ROOT, "Jinzhou_Jinhsi", "Textures")
REPORT = os.path.join(ROOT, "workspace", "gen", "reports", "cloth_probe4.json")

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

edge_info = {}
same_dir = 0
for i, tri in enumerate(T):
    for e in ((int(tri[0]), int(tri[1])), (int(tri[1]), int(tri[2])), (int(tri[2]), int(tri[0]))):
        key = (min(e), max(e))
        if key in edge_info:
            prev = edge_info[key]
            if prev[0] == e:
                same_dir += 1
            edge_info[key] = (e, i, prev[2] + 1)
        else:
            edge_info[key] = (e, i, 1)
boundary_edges = [k for k, v in edge_info.items() if v[2] == 1]
boundary_len = float(sum(np.linalg.norm(V[k[1]] - V[k[0]]) for k in boundary_edges))
print("TOPO edges", len(edge_info), "boundary", len(boundary_edges), "boundary_len_cm", round(boundary_len, 2),
      "same_direction_pairs", same_dir)

vert_tri = {}
for i, tri in enumerate(T):
    for vtx in tri:
        vert_tri.setdefault(int(vtx), i)
slot_bnd = {name: [0, 0.0] for name in SLOT}
for k in boundary_edges:
    ti = vert_tri[int(k[0])]
    slot_bnd[SLOT[PMAT[ti]]][0] += 1
    slot_bnd[SLOT[PMAT[ti]]][1] += float(np.linalg.norm(V[k[1]] - V[k[0]]))
print("BOUNDARY_BY_SLOT", json.dumps(slot_bnd, ensure_ascii=False))

light = np.where((TRI_LUM > 0.5) & ((PMAT == 3) | (PMAT == 4)))[0]
black = np.where((TRI_LUM < 0.22) & ((PMAT == 3) | (PMAT == 4)))[0]
print("LIGHT_TRIS", len(light), "BLACK_TRIS", len(black))

kd = KDTree(len(black))
for j, ti in enumerate(black):
    kd.insert(Vector(CENT[ti]), j)
kd.balance()
gaps = []
signed = []
for ti in light[::3]:
    co, j, dd = kd.find(Vector(CENT[ti]))
    gaps.append(dd)
    tb = black[j]
    signed.append(float((CENT[ti] - CENT[tb]).dot(TN[tb])))
gaps = np.array(gaps)
signed = np.array(signed)
print("LIGHT_TO_BLACK_FACE_GAP p05", round(float(np.percentile(gaps, 5)), 3),
      "p25", round(float(np.percentile(gaps, 25)), 3),
      "median", round(float(np.median(gaps)), 3),
      "frac_lt_0.2", round(float((gaps < 0.2).mean()), 4),
      "frac_lt_0.5", round(float((gaps < 0.5).mean()), 4))
print("SIGNED front_frac", round(float((signed > 0).mean()), 4))

panel = np.where(roots == 22172)[0]
print("PANEL tris", len(panel), "area", round(float(AREA[panel].sum()), 2),
      "lum_min", round(float(TRI_LUM[panel].min()), 3), "lum_max", round(float(TRI_LUM[panel].max()), 3))
pl = KDTree(len(light))
for j, ti in enumerate(light):
    pl.insert(Vector(CENT[ti]), j)
pl.balance()
pg = []
ps = []
for ti in panel:
    co, j, dd = pl.find(Vector(CENT[ti]))
    pg.append(dd)
    ps.append(float((CENT[ti] - CENT[light[j]]).dot(TN[light[j]])))
pg = np.array(pg)
ps = np.array(ps)
print("PANEL_TO_LIGHT_GAP median", round(float(np.median(pg)), 3), "p90", round(float(np.percentile(pg, 90)), 3),
      "frac_lt_1", round(float((pg < 1.0).mean()), 3), "behind_light_frac", round(float((ps < 0).mean()), 3))

panel_keys = [k for k in boundary_edges if int(roots[vert_tri[int(k[0])]]) == 22172]
panel_len = float(sum(np.linalg.norm(V[k[1]] - V[k[0]]) for k in panel_keys))
print("PANEL boundary_edges", len(panel_keys), "len_cm", round(panel_len, 2))

light_isl = [30436, 28655, 15565, 45331, 47267, 47675, 46242, 35082, 41326]
for lid in light_isl:
    sel = roots == lid
    ids = np.where(sel)[0]
    if not len(ids):
        continue
    vs = np.unique(T[ids].reshape(-1))
    bnd = [k for k in boundary_edges if int(roots[vert_tri[int(k[0])]]) == lid]
    blen = float(sum(np.linalg.norm(V[k[1]] - V[k[0]]) for k in bnd))
    print("ISL", lid, "tris", len(ids), "area", round(float(AREA[ids].sum()), 1),
          "bbox_z", round(float(V[vs][:, 2].min()), 1), round(float(V[vs][:, 2].max()), 1),
          "boundary", len(bnd), "bnd_len", round(blen, 1),
          "lum", round(float(TRI_LUM[ids].mean()), 2))

with open(REPORT, "w", encoding="utf-8") as f:
    json.dump({"boundary_edges": len(boundary_edges), "boundary_len_cm": round(boundary_len, 2),
               "same_direction_pairs": same_dir,
               "boundary_by_slot": slot_bnd,
               "light_to_black": {"median": round(float(np.median(gaps)), 3),
                                  "frac_lt_0_2": round(float((gaps < 0.2).mean()), 4),
                                  "frac_lt_0_5": round(float((gaps < 0.5).mean()), 4),
                                  "front_frac": round(float((signed > 0).mean()), 4)},
               "panel": {"tris": int(len(panel)), "area": round(float(AREA[panel].sum()), 2),
                         "to_light_median": round(float(np.median(pg)), 3),
                         "frac_lt_1": round(float((pg < 1.0).mean()), 3),
                         "behind_light_frac": round(float((ps < 0).mean()), 3),
                         "boundary_edges": len(panel_keys), "boundary_len_cm": round(panel_len, 2)}},
              f, ensure_ascii=False, indent=1)
print("PROBE4_OK")
