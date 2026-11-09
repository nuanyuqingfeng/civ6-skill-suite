import bpy
import os
import math

from mathutils import Matrix

MODEL_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
PSK = os.path.join(MODEL_DIR, "R2T1JinxiMd10011.psk")
OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx"
SCALE = 120.76 / 132.76

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
    for item in list(block):
        block.remove(item, do_unlink=True)

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

R = Matrix.Rotation(math.radians(-90), 4, 'Y')
S = Matrix.Scale(SCALE, 4)
T = R @ S

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for eb in arm.data.edit_bones:
    eb.matrix = T @ eb.matrix
bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
bpy.context.view_layer.objects.active = body
body.matrix_world = T @ body.matrix_world
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

head = arm.data.bones.get('Bip001Head')
print("FBXMODEL head=", [round(c, 2) for c in arm.matrix_world @ head.head_local])

out = os.path.join(OUT_DIR, "LEAD_Jinhsi_QYQXP_Model.fbx")
args = dict(
    use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
    bake_anim=False, axis_forward='-Z', axis_up='Y', apply_unit_scale=True,
    global_scale=1.0, mesh_smooth_type='OFF', use_mesh_modifiers=True,
)
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.export_scene.fbx(filepath=out, **args)
print("FBXMODEL_EXPORTED:", out, os.path.getsize(out))
