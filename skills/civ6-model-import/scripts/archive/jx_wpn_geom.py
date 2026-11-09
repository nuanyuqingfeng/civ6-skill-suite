import bpy
import os
import sys
import json

from mathutils import Vector

OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\tmp"
FBX = r"D:\desktop\Material\建模文件\WeaponJinXIWeapon\JinxiSwordModel.fbx"
os.makedirs(OUT_DIR, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=FBX)

mesh_obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
me = mesh_obj.data
mw = mesh_obj.matrix_world
verts = [mw @ v.co for v in me.vertices]

print("WEAPON_OBJ", mesh_obj.name, "verts", len(verts), "polys", len(me.polygons))
print("ARMATURE", arm.name, "scale", tuple(arm.scale), "matrix_world", [round(c, 6) for row in arm.matrix_world for c in row])
for b in arm.data.bones:
    bm = arm.matrix_world @ b.matrix_local
    print("WBONE", b.name, "parent", b.parent.name if b.parent else "-",
          "head", [round(c, 4) for c in bm.translation],
          "tail", [round(c, 4) for c in (arm.matrix_world @ b.tail_local)],
          "len", round(b.length, 5))

gi = {g.index: g.name for g in mesh_obj.vertex_groups}
per_group = {name: [] for name in gi.values()}
unweighted = 0
max_inf = 0
for i, v in enumerate(me.vertices):
    if len(v.groups) == 0:
        unweighted += 1
    max_inf = max(max_inf, len(v.groups))
    for g in v.groups:
        per_group[gi[g.group]].append((i, g.weight))
print("WEIGHTS unweighted", unweighted, "max_influences", max_inf)
for name in sorted(per_group):
    items = per_group[name]
    if not items:
        print("VGROUP", name, "count 0")
        continue
    pts = [verts[i] for i, w in items]
    lo = [round(min(p[k] for p in pts), 4) for k in range(3)]
    hi = [round(max(p[k] for p in pts), 4) for k in range(3)]
    wsum = [w for i, w in items]
    print("VGROUP", name, "count", len(items), "bbox", lo, hi,
          "w_min", round(min(wsum), 4), "w_max", round(max(wsum), 4))

xlo = min(p.x for p in verts)
xhi = max(p.x for p in verts)
nb = 32
print("X_SLICES", round(xlo, 4), round(xhi, 4), "bins", nb)
for k in range(nb):
    a = xlo + (xhi - xlo) * k / nb
    b = xlo + (xhi - xlo) * (k + 1) / nb
    pts = [p for p in verts if a <= p.x <= b]
    if not pts:
        print("SLICE", round(a, 3), round(b, 3), "n 0")
        continue
    ylo = min(p.y for p in pts)
    yhi = max(p.y for p in pts)
    zlo = min(p.z for p in pts)
    zhi = max(p.z for p in pts)
    print("SLICE", round(a, 3), round(b, 3), "n", len(pts),
          "Y", [round(ylo, 3), round(yhi, 3)], "Z", [round(zlo, 3), round(zhi, 3)])

dao = per_group.get("dao1", [])
if dao:
    pts = [verts[i] for i, w in dao]
    print("DAO_BBOX", [round(min(p[k] for p in pts), 4) for k in range(3)],
          [round(max(p[k] for p in pts), 4) for k in range(3)])
    w0 = [i for i, w in dao if w > 0.99]
    print("DAO_FULL_WEIGHT", len(w0))
print("GEOM_DONE")
