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
arm.rotation_euler = (0.0, 0.0, 1.5707963267948966)
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
body.data.transform(Matrix.Rotation(1.5707963267948966, 4, 'Z'))
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()

co = [v.co.copy() for v in body.data.vertices]
names = [m.name for m in body.data.materials]
face_slot = names.index("MI_R2T1JinxiMd10011Face")
face_verts = set()
for p in body.data.polygons:
    if p.material_index == face_slot:
        face_verts.update(p.vertices)
mouth = sum((co[i] for i in parts["mouth_ap"]), Vector()) / len(parts["mouth_ap"])
print("PROBE_MOUTH", [round(v, 4) for v in mouth])

rows = []
for vi in face_verts:
    c = co[vi]
    if abs(c.y) <= 0.15 and c.x > 2.2 and 123.2 <= c.z <= 124.9:
        rows.append((c.z, c.x, c.y, vi, body.data.vertices[vi].normal.x))
rows.sort()
print("PROBE_FRONT", len(rows))
for z, x, y, vi, nx in rows:
    print("PROBE_V z=%.4f x=%.4f y=%.4f vi=%d nx=%.3f" % (z, x, y, vi, nx))

zs = [r[0] for r in rows]
diffs = [zs[i + 1] - zs[i] for i in range(len(zs) - 1)]
if diffs:
    top = sorted(range(len(diffs)), key=lambda i: diffs[i])[-6:]
    for i in sorted(top):
        print("PROBE_GAPBIG z0=%.4f z1=%.4f dz=%.4f" % (zs[i], zs[i + 1], diffs[i]))
