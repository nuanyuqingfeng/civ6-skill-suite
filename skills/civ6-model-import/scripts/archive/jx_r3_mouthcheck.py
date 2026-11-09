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
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()
parts = rig.load_parts()
rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)

mouth = Vector((0.0, -3.2114, 135.417))
near = []
for v in body.data.vertices:
    p = body.matrix_world @ v.co
    if abs(p.x) < 1.2 and (p - mouth).length < 1.6:
        near.append(v.index)

def sample():
    up, lo = [], []
    for vi in near:
        p = body.matrix_world @ body.data.vertices[vi].co
        (up if p.z >= mouth.z else lo).append(p.z)
    return sum(up) / len(up), sum(lo) / len(lo)

rest_up, rest_lo = sample()
print("REST up=%.3f lo=%.3f gap=%.3f n=%d" % (rest_up, rest_lo, rest_up - rest_lo, len(near)))

pose_world = {b.name: b.matrix_local.copy() for b in arm.data.bones if b.name.startswith("JX_")}
rest = {b.name: b.matrix_local.copy() for b in arm.data.bones if b.name.startswith("JX_")}
rig.pose_face(pose_world, {"jaw": 1.0}, rest)
for pb in arm.pose.bones:
    if pb.name.startswith("JX_"):
        delta = pose_world[pb.name] @ rest[pb.name].inverted()
        pb.matrix = delta @ pb.matrix
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(dg)
me = ev.to_mesh()
up, lo = [], []
for vi in near:
    p = ev.matrix_world @ me.vertices[vi].co
    (up if p.z >= mouth.z else lo).append(p.z)
ev.to_mesh_clear()
print("JAW up=%.3f lo=%.3f gap=%.3f" % (sum(up) / len(up), sum(lo) / len(lo), sum(up) / len(up) - sum(lo) / len(lo)))
print("MOUTHCHECK_DONE")
