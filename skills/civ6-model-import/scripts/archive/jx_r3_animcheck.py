import os
import sys

import bpy
from mathutils import Matrix

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
print("SLOT", getattr(slot, "name_display", None), "has_slot", slot is not None)
bpy.data.objects.remove(anim_arm, do_unlink=True)
if arm.animation_data is None:
    arm.animation_data_create()
arm.animation_data.action = action
if slot is not None:
    arm.animation_data.action_slot = slot

scene = bpy.context.scene
for f in (2, 60, 134):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    pb = arm.pose.bones["JX_LidUp_L"]
    eb = arm.pose.bones["JX_Eye_L"]
    print("FRAME %d lid_local=%s lid_z=%.4f eye_z=%.4f dz=%.4f" % (
        f, tuple(round(v, 4) for v in pb.location), pb.matrix.translation.z,
        eb.matrix.translation.z, pb.matrix.translation.z - eb.matrix.translation.z))
print("ANIMCHECK_DONE")
