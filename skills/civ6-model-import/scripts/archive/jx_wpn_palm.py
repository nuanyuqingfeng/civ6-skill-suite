import bpy
import math

from mathutils import Vector

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
bones = arm.data.bones


def head(n):
    return bones[n].head_local.copy()


for side, prop in (("L", "WeaponProp01"), ("R", "WeaponProp02")):
    h = head("Bip001%sHand" % side)
    f0 = head("Bip001%sFinger0" % side)
    f4 = head("Bip001%sFinger4" % side)
    f01 = head("Bip001%sFinger01" % side)
    f02 = head("Bip001%sFinger02" % side)
    fingers = (f01 - f0).normalized()
    across = (f4 - f0).normalized()
    palm = fingers.cross(across).normalized()
    print("PALM", side, "hand_head", [round(c, 2) for c in h],
          "finger0", [round(c, 2) for c in f0], "finger4", [round(c, 2) for c in f4],
          "finger02", [round(c, 2) for c in f02])
    print("PALM_AXES", side, "fingers", [round(c, 3) for c in fingers],
          "across", [round(c, 3) for c in across], "normal", [round(c, 3) for c in palm])
    pm = bones[prop].matrix_local
    for nm, v in (("X", Vector((1, 0, 0))), ("-X", Vector((-1, 0, 0))), ("Y", Vector((0, 1, 0))),
                  ("-Y", Vector((0, -1, 0))), ("Z", Vector((0, 0, 1))), ("-Z", Vector((0, 0, -1)))):
        a = (pm.to_3x3() @ v).normalized()
        print("PROP_AXIS", side, prop, nm,
              "world", [round(c, 3) for c in a],
              "to_fingers", round(math.degrees(a.angle(fingers)), 1),
              "to_across", round(math.degrees(a.angle(across)), 1),
              "to_palm_normal", round(math.degrees(a.angle(palm)), 1))
print("PALM_DONE")
