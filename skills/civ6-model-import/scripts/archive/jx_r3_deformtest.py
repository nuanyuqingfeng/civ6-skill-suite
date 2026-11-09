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
arm.animation_data.action_slot = slot

mods = [m.type for m in body.modifiers]
print("MODIFIERS", mods)
scene = bpy.context.scene
for f in (2, 134):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    idx = {g.index for g in body.vertex_groups if g.name == "JX_LidUp_L"}
    zs = [(ev.matrix_world @ v.co).z for v in me.vertices if any(g.group in idx and g.weight > 0.5 for g in v.groups)]
    pb = arm.pose.bones["JX_LidUp_L"]
    ev.to_mesh_clear()
    print("F%d mesh_lid_z=%.4f bone_lid_z=%.4f n=%d" % (f, sum(zs) / len(zs), pb.matrix.translation.z, len(zs)))
print("DEFORMTEST_DONE")
