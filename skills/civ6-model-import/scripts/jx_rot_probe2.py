import bpy
import os
import math
import sys

from mathutils import Matrix

MODEL_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
PSK = os.path.join(MODEL_DIR, "R2T1JinxiMd10011.psk")
OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx"
SCALE = 120.76 / 132.76

axis = sys.argv[-2]
deg = float(sys.argv[-1])

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
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.separate(type='MATERIAL')
bpy.ops.object.mode_set(mode='OBJECT')
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in meshes:
    slot = o.material_slots[0].name if o.material_slots else "NONE"
    short = slot.replace("MI_R2T1JinxiMd10011", "").replace("MI_", "")
    o.name = short if short else slot
    if o.data.shape_keys:
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.shape_key_remove(all=True)
    has_arm = any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers)
    if not has_arm:
        m = o.modifiers.new(name='Armature', type='ARMATURE')
        m.object = arm

R = Matrix.Rotation(math.radians(deg), 4, axis)
T = R @ Matrix.Scale(SCALE, 4)
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
arm.matrix_world = T @ arm.matrix_world
for o in meshes:
    o.matrix_world = T @ o.matrix_world
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

head = arm.data.bones.get('Bip001Head')
print("PROBE2 %s%+.0f head_blender=" % (axis, deg), [round(c, 2) for c in arm.matrix_world @ head.head_local])

out = os.path.join(OUT_DIR, "PROBE2_%s%+.0f.cn6" % (axis, deg))
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_shape.cn6(filepath=out, use_selection=True)
print("PROBE2_EXPORTED:", out)
