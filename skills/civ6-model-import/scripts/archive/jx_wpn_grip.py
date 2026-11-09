import bpy
import math

from mathutils import Matrix, Vector

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"
CLIPS = ["Ui_Weapon_Start", "Ui_Weapon_Loop", "Ui_Weapon_End"]
RIG_ALIGN = Matrix.Rotation(math.radians(90.0), 4, 'Z')
ANIM_SCALE = 100.0
CAND = {"WeaponProp01": "L", "WeaponProp02": "R"}
AXES = [("X", Vector((1, 0, 0))), ("-X", Vector((-1, 0, 0))), ("Y", Vector((0, 1, 0))),
        ("-Y", Vector((0, -1, 0))), ("Z", Vector((0, 0, 1))), ("-Z", Vector((0, 0, -1)))]
SAMPLES = {"Ui_Weapon_Start": [0, 15, 30, 45, 60], "Ui_Weapon_Loop": [0, 20, 40, 60, 80],
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


def topo():
    order = []
    seen = set()

    def visit(pb):
        if pb.name in seen:
            return
        seen.add(pb.name)
        if pb.parent is not None:
            visit(pb.parent)
        order.append(pb)

    for pb in arm.pose.bones:
        visit(pb)
    return order


ORDER = topo()
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'


def apply_correct_pose():
    pw = {}
    for pb in ORDER:
        local = Matrix.LocRotScale(pb.location * ANIM_SCALE, pb.rotation_quaternion, pb.scale)
        pw[pb.name] = (RIG_ALIGN @ local) if pb.parent is None else (pw[pb.parent.name] @ local)
    for pb in ORDER:
        pb.matrix = pw[pb.name]
        bpy.context.view_layer.update()


def palm(side):
    f0 = arm.pose.bones["Bip001%sFinger0" % side].matrix.translation.copy()
    f01 = arm.pose.bones["Bip001%sFinger01" % side].matrix.translation.copy()
    f4 = arm.pose.bones["Bip001%sFinger4" % side].matrix.translation.copy()
    fingers = (f01 - f0).normalized()
    across = (f4 - f0).normalized()
    return fingers, across, fingers.cross(across).normalized()


ACC = {}
for clip in CLIPS:
    arm.animation_data.action = bpy.data.actions[clip]
    for f in SAMPLES[clip]:
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        apply_correct_pose()
        for bone, side in CAND.items():
            pm = arm.pose.bones[bone].matrix
            fingers, across, pn = palm(side)
            for aname, avec in AXES:
                a = (pm.to_3x3() @ avec).normalized()
                rec = ACC.setdefault((bone, aname), {"f": [], "n": [], "a": []})
                rec["f"].append(math.degrees(a.angle(fingers)))
                rec["n"].append(math.degrees(a.angle(pn)))
                rec["a"].append(math.degrees(a.angle(across)))
for key in sorted(ACC):
    r = ACC[key]
    print("GRIP", key[0], key[1],
          "to_fingers_mean", round(sum(r["f"]) / len(r["f"]), 1),
          "to_palm_normal_mean", round(sum(r["n"]) / len(r["n"]), 1),
          "to_across_mean", round(sum(r["a"]) / len(r["a"]), 1))
print("GRIP_DONE")
