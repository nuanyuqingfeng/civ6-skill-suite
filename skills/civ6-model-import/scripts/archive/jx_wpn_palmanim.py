import bpy
import math

from mathutils import Vector

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"
CLIPS = ["Ui_Weapon_Start", "Ui_Weapon_Loop", "Ui_Weapon_End"]
FRAMES = {"Ui_Weapon_Start": [0, 15, 30, 45, 60], "Ui_Weapon_Loop": [0, 20, 40, 60, 80],
          "Ui_Weapon_End": [0, 20, 40, 60, 70]}

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


def ph(name):
    return arm.pose.bones[name].matrix.translation.copy()


for clip in CLIPS:
    arm.animation_data.action = bpy.data.actions[clip]
    for f in FRAMES[clip]:
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        f0 = ph("Bip001LFinger0")
        f01 = ph("Bip001LFinger01")
        f02 = ph("Bip001LFinger02")
        f4 = ph("Bip001LFinger4")
        hand = ph("Bip001LHand")
        prop = arm.pose.bones["WeaponProp01"].matrix
        fingers = (f01 - f0).normalized()
        across = (f4 - f0).normalized()
        palm_n = fingers.cross(across).normalized()
        palm_center = (f0 + f4 + f02) / 3.0
        print("PALMPOSE", clip, f, "palm_center", [round(c, 2) for c in palm_center],
              "prop", [round(c, 2) for c in prop.translation],
              "grip_to_palm_cm", round((prop.translation - palm_center).length, 2),
              "grip_to_wrist_cm", round((prop.translation - hand).length, 2),
              "palm_normal", [round(c, 3) for c in palm_n])
        for nm, v in (("X", Vector((1, 0, 0))), ("-X", Vector((-1, 0, 0))), ("Y", Vector((0, 1, 0))),
                      ("-Y", Vector((0, -1, 0))), ("Z", Vector((0, 0, 1))), ("-Z", Vector((0, 0, -1)))):
            a = (prop.to_3x3() @ v).normalized()
            print("   PAXIS", nm, "world", [round(c, 3) for c in a],
                  "to_palm_normal", round(math.degrees(a.angle(palm_n)), 1),
                  "to_fingers", round(math.degrees(a.angle(fingers)), 1))
print("PALMPOSE_DONE")
