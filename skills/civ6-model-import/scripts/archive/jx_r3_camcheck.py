import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_face as rig

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
WEAPON = os.path.join(ROOT, "workspace", "gen", "jinhsi_fbx", "weapon_rigged.blend")
FBX = os.path.join(ROOT, "workspace", "gen", "jinhsi_fbx", "JX_IDLE.fbx")
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
rig.join_weapon(body, WEAPON)
parts = rig.load_parts()
rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)

bpy.ops.import_scene.fbx(filepath=FBX)
anim_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o is not arm][0]
action = anim_arm.animation_data.action
slot = anim_arm.animation_data.action_slot
bpy.data.objects.remove(anim_arm, do_unlink=True)
if arm.animation_data is None:
    arm.animation_data_create()
arm.animation_data.action = action
if slot is not None:
    arm.animation_data.action_slot = slot

scene = bpy.context.scene
scene.frame_set(134)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(dg)
me = ev.to_mesh()
xs = [ev.matrix_world @ v.co for v in me.vertices]
zs = [p.z for p in xs]
ys = [p.y for p in xs]
xx = [p.x for p in xs]
print("MESH world z %.1f..%.1f  y %.1f..%.1f  x %.1f..%.1f" % (min(zs), max(zs), min(ys), max(ys), min(xx), max(xx)))
ev.to_mesh_clear()
l = arm.pose.bones["JX_Eye_L"]
print("EYE world", tuple(round(v, 1) for v in (arm.matrix_world @ l.matrix).translation))
print("ARM matrix_world", [round(v, 3) for v in arm.matrix_world.to_scale()])
print("BODY matrix_world", [round(v, 3) for v in body.matrix_world.to_scale()])
print("CAMCHECK_DONE")
