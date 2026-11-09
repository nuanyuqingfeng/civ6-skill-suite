import bpy
import os
import sys
import math

from mathutils import Vector, Matrix

OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\tmp"
PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"
CLIPS = ["Ui_Weapon_Start", "Ui_Weapon_Loop", "Ui_Nature_Loop", "Cos_Pose"]
TRACK = ["Bip001LHand", "Bip001RHand", "WeaponProp01", "WeaponProp02",
         "Bip001LForearm", "Bip001RForearm", "Bip001Spine2", "Bip001Head"]

os.makedirs(OUT_DIR, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
print("RIG", arm.name, len(arm.data.bones))
print("REST_POSE_POSITION", arm.data.pose_position)

bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
for clip in CLIPS:
    bpy.ops.uf.import_ueanim(directory=ANIM_DIR, files=[{'name': clip + '.ueanim'}])

for a in bpy.data.actions:
    print("ACTION", a.name, "range", tuple(round(x) for x in a.frame_range), "fcurves", len(a.fcurves))


def hand_report(act_name, frames):
    act = bpy.data.actions[act_name]
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act
    arm.data.pose_position = 'POSE'
    for f in frames:
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        out = {}
        for bn in TRACK:
            pb = arm.pose.bones[bn]
            m = arm.matrix_world @ pb.matrix
            out[bn] = (m.translation.copy(), m.to_3x3() @ Vector((0, 1, 0)), m.to_3x3() @ Vector((0, 0, 1)))
        lh = out["Bip001LHand"][0]
        rh = out["Bip001RHand"][0]
        dist = (lh - rh).length
        print("POSE", act_name, "f", f,
              "LHand", [round(c, 2) for c in lh],
              "RHand", [round(c, 2) for c in rh],
              "hand_dist", round(dist, 2))
        for bn in ("Bip001LHand", "Bip001RHand", "WeaponProp01", "WeaponProp02"):
            p, y, z = out[bn]
            print("   AXIS", bn, "pos", [round(c, 2) for c in p],
                  "y", [round(c, 3) for c in y], "z", [round(c, 3) for c in z])


for clip in CLIPS:
    act = bpy.data.actions[clip]
    f0 = int(act.frame_range[0])
    f1 = int(act.frame_range[1])
    step = max(1, (f1 - f0) // 12)
    frames = list(range(f0, f1 + 1, step))
    if frames[-1] != f1:
        frames.append(f1)
    print("SAMPLING", clip, f0, f1, frames)
    hand_report(clip, frames)
print("POSE_PROBE_DONE")
