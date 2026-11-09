import bpy
import math

from mathutils import Vector

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"
CLIPS = ["Ui_Weapon_Start", "Ui_Weapon_Loop"]
BLADE_CM = 144.0
CANDIDATES = [("WeaponProp01", "Bip001LHand"), ("WeaponProp02", "Bip001RHand")]
AXES = [("X", Vector((1, 0, 0))), ("-X", Vector((-1, 0, 0))), ("Y", Vector((0, 1, 0))),
        ("-Y", Vector((0, -1, 0))), ("Z", Vector((0, 0, 1))), ("-Z", Vector((0, 0, -1)))]

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


def seg_point_dist(a, b, p):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (a + ab * t - p).length


def spine_clearance(a, b):
    worst = 1e9
    for z in (58.0, 70.0, 82.0, 94.0, 106.0, 118.0, 130.0, 142.0):
        worst = min(worst, seg_point_dist(a, b, Vector((0.0, 0.0, z))))
    return worst


for clip in CLIPS:
    act = bpy.data.actions[clip]
    arm.animation_data.action = act
    f0 = int(act.frame_range[0])
    f1 = int(act.frame_range[1])
    samples = list(range(f0, f1 + 1))
    for bone, parent in CANDIDATES:
        for aname, avec in AXES:
            tip_z = []
            clear = []
            grip_y = []
            for f in samples:
                bpy.context.scene.frame_set(f)
                bpy.context.view_layer.update()
                m = arm.pose.bones[bone].matrix
                grip = m.translation.copy()
                axis = (m.to_3x3() @ avec).normalized()
                tip = grip + axis * BLADE_CM
                tip_z.append(tip.z)
                clear.append(spine_clearance(grip, tip))
                grip_y.append(grip.y)
            print("ATTACH", clip, bone, aname,
                  "tip_z_min", round(min(tip_z), 2),
                  "spine_clear_min", round(min(clear), 2),
                  "spine_clear_max", round(max(clear), 2),
                  "grip_y_range", [round(min(grip_y), 2), round(max(grip_y), 2)])
print("ATTACH_DONE")
