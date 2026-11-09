import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_face as rig

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
SCALE = 0.915502

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = max([o for o in bpy.data.objects if o.type == 'MESH'], key=lambda o: len(o.data.vertices))
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
arm.scale = (SCALE, SCALE, SCALE)
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
body.data.transform(Matrix.Scale(SCALE, 4))
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()

parts = rig.load_parts()
rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)

arm.rotation_mode = 'XYZ'
arm.rotation_euler = (0.0, 0.0, math.radians(90.0))
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
body.data.transform(Matrix.Rotation(math.radians(90.0), 4, 'Z'))
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()

gname = {g.index: g.name for g in body.vertex_groups}
co = [v.co.copy() for v in body.data.vertices]
mouth = sum((co[i] for i in parts["mouth_ap"]), Vector()) / len(parts["mouth_ap"])
names = [m.name for m in body.data.materials]
face_slot = names.index("MI_R2T1JinxiMd10011Face")
face_verts = set()
for p in body.data.polygons:
    if p.material_index == face_slot:
        face_verts.update(p.vertices)

rows = []
for vi in face_verts:
    c = co[vi]
    if 2.15 <= abs(c.y) <= 2.65 and c.x > 1.8 and 123.3 <= c.z <= 124.8:
        rows.append((abs(c.y), c.z, c.x, vi))
rows.sort()
print("C_PROBE", len(rows))
for ay, z, x, vi in rows:
    w = {gname[g.group]: round(g.weight, 3) for g in body.data.vertices[vi].groups}
    print("C_V |y|=%.3f z=%.4f x=%.4f vi=%d %s" % (ay, z, x, vi, w))
