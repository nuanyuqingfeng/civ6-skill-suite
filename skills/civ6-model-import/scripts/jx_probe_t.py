import bpy
import os
import math
import sys

from mathutils import Matrix, Euler

OUT_DIR = r"E:\SoftWares\civ6_nexus_work\probe_t2"
MODEL_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
PSK = os.path.join(MODEL_DIR, "R2T1JinxiMd10011.psk")
os.makedirs(OUT_DIR, exist_ok=True)

# 五个候选旋转：目标是让 granny 空间 Bip001 局部落到 +X（达妮娅式站立）
CANDS = {
    "Ry-90": Matrix.Rotation(math.radians(-90), 4, 'Y'),
    "Ry+90": Matrix.Rotation(math.radians(90), 4, 'Y'),
    "Rx+90": Matrix.Rotation(math.radians(90), 4, 'X'),
    "Rx-90": Matrix.Rotation(math.radians(-90), 4, 'X'),
    "Rz-90": Matrix.Rotation(math.radians(-90), 4, 'Z'),
}

tag = sys.argv[-1]
T = CANDS[tag]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for blk in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
    for it in list(blk):
        blk.remove(it, do_unlink=True)

bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = None
for o in bpy.data.objects:
    if o.type == 'MESH' and len(o.data.vertices) > 100:
        body = o
body.name = "JinhsiBody"
if body.data.shape_keys:
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.shape_key_remove(all=True)

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
# 只旋转 Root 骨的 rest：父子相对 rest 在此层级改变，其余子链相对关系保持
root_eb = arm.data.edit_bones.get('Root')
root_eb.matrix = T @ root_eb.matrix
bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
bpy.context.view_layer.objects.active = body
body.matrix_world = T @ body.matrix_world
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

head = arm.data.bones.get('Bip001Head')
print("PROBE_T", tag, "head_blender=", [round(c, 2) for c in (arm.matrix_world @ head.head_local)])

out = os.path.join(OUT_DIR, "LEAD_Jinhsi_QYQXP.cn6")
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.export_shape.cn6(filepath=out, triangulate=True, use_selection=True)
print("PROBE_T_EXPORTED", tag, out)
