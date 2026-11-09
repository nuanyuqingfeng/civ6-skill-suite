import os

import bpy

MODEL_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
PSK = os.path.join(MODEL_DIR, "R2T1JinxiMd10011.psk")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.armatures):
    for item in list(block):
        block.remove(item, do_unlink=True)

bpy.ops.import_scene.psk(filepath=PSK)
body = None
for o in bpy.data.objects:
    if o.type == 'MESH' and len(o.data.vertices) > 100:
        body = o
me = body.data
groups = {g.index: g.name for g in body.vertex_groups}

zmax_all = max(v.co.z for v in me.vertices)
zmin_all = min(v.co.z for v in me.vertices)
print("BODY_Z", round(zmin_all, 3), round(zmax_all, 3), "span", round(zmax_all - zmin_all, 3))

KEY = ("Head", "Face", "Eye", "Brow", "Mouth", "Jaw", "Nose", "Cheek", "Ear")
head_verts = []
names = set()
for v in me.vertices:
    for g in v.groups:
        n = groups[g.group]
        if any(k in n for k in KEY) and g.weight > 0.5:
            head_verts.append(v)
            names.add(n)
            break
if head_verts:
    zs = [v.co.z for v in head_verts]
    xs = [v.co.x for v in head_verts]
    ys = [v.co.y for v in head_verts]
    print("HEAD_VERTS", len(head_verts), "z", round(min(zs), 3), round(max(zs), 3),
          "x", round(min(xs), 3), round(max(xs), 3),
          "y", round(min(ys), 3), round(max(ys), 3))
    print("HEAD_GROUPS", sorted(names)[:12])
