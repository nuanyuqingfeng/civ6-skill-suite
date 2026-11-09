import bpy
import os
import math

from mathutils import Vector

OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\tmp"
PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"
CLIPS = ["Ui_Weapon_Start", "Ui_Weapon_Loop", "Ui_Nature_Loop", "Cos_Pose"]
PAIRS = [("WeaponProp01", "Bip001LHand"), ("WeaponProp02", "Bip001RHand"),
         ("WeaponProp03", "Bip001"), ("WeaponProp04", "WeaponProp03"),
         ("WeaponProp05", "Root"), ("WeaponProp06", "Root"), ("WeaponProp07", "Root")]

os.makedirs(OUT_DIR, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
for clip in CLIPS:
    bpy.ops.uf.import_ueanim(directory=ANIM_DIR, files=[{'name': clip + '.ueanim'}])

if arm.animation_data is None:
    arm.animation_data_create()

for clip in CLIPS:
    act = bpy.data.actions[clip]
    arm.animation_data.action = act
    f0 = int(act.frame_range[0])
    f1 = int(act.frame_range[1])
    stats = {}
    for prop, parent in PAIRS:
        stats[prop] = {"t": [], "q": []}
    for f in range(f0, f1 + 1):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        for prop, parent in PAIRS:
            mp = arm.pose.bones[prop].matrix
            mb = arm.pose.bones[parent].matrix
            rel = mb.inverted() @ mp
            stats[prop]["t"].append(rel.translation.copy())
            stats[prop]["q"].append(rel.to_quaternion())
    for prop, parent in PAIRS:
        ts = stats[prop]["t"]
        qs = stats[prop]["q"]
        tmax = max((ts[i] - ts[0]).length for i in range(len(ts)))
        qmax = max(math.degrees(qs[0].rotation_difference(qs[i]).angle) for i in range(len(qs)))
        print("REL", clip, prop, "parent", parent,
              "t0", [round(c, 4) for c in ts[0]],
              "t_dev_max", round(tmax, 4),
              "rot_dev_max_deg", round(qmax, 3))
print("REL_PROBE_DONE")
