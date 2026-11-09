import bpy
import numpy as np
from mathutils import Vector

MODEL = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials):
    for item in list(block):
        block.remove(item, do_unlink=True)
bpy.ops.import_scene.psk(filepath=MODEL)
body = [o for o in bpy.data.objects if o.type == 'MESH' and len(o.data.vertices) > 100][0]
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

rows = []
for r in np.unique(roots):
    ids = np.where(roots == r)[0]
    mat = int(PMAT[ids[0]])
    if mat not in (3, 4):
        continue
    vs = np.unique(T[ids].reshape(-1))
    z0 = float(V[vs][:, 2].min())
    z1 = float(V[vs][:, 2].max())
    area = float(AREA[ids].sum())
    if z1 < 92.0 or z0 > 130.0 or area < 8.0:
        continue
    front = float(AREA[ids][TN[ids][:, 1] < -0.3].sum())
    back = float(AREA[ids][TN[ids][:, 1] > 0.3].sum())
    rows.append((SLOT[mat].replace("MI_R2T1JinxiMd10011", ""), int(r), len(ids), len(vs),
                 int(vs.min()), int(vs.max()), round(area, 1),
                 [round(float(x), 2) for x in V[vs].min(axis=0)] + [round(float(x), 2) for x in V[vs].max(axis=0)],
                 round(front, 1), round(back, 1)))
rows.sort(key=lambda r: -r[6])
print("ISLAND_TABLE rows", len(rows))
for r in rows[:26]:
    print("ISL", r[0], "id", r[1], "tris", r[2], "verts", r[3], "vidx", r[4], r[5],
          "area", r[6], "bbox", r[7], "front", r[8], "back", r[9])
print("ISLAND_TABLE_OK")
