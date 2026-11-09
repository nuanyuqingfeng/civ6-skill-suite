import bpy
import os
import math
import sys

from mathutils import Matrix

CN6_SRC = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx\LEAD_Jinhsi_pristine.cn6"
OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx"
SCALE = 120.76 / 132.76

axis = sys.argv[-2]
deg = float(sys.argv[-1])

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
    for item in list(block):
        block.remove(item, do_unlink=True)

bpy.ops.import_shape.cn6(filepath=CN6_SRC)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in meshes:
    if o.name.endswith('#M'):
        o.name = o.name[:-2]
    while len(o.data.uv_layers) > 1:
        o.data.uv_layers.remove(o.data.uv_layers[-1])
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
print("PROBE %s%+.0f head_blender=" % (axis, deg), [round(c, 2) for c in arm.matrix_world @ head.head_local])

out = os.path.join(OUT_DIR, "PROBE_%s%+.0f.cn6" % (axis, deg))
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_shape.cn6(filepath=out, use_selection=True)
print("PROBE_EXPORTED:", out)
