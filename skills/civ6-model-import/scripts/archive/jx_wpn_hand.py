import bpy
import math

from mathutils import Matrix, Vector

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"
RIG_ALIGN = Matrix.Rotation(math.radians(90.0), 4, 'Z')
ANIM_SCALE = 100.0
BLADE = 144.3
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
for clip in ("Ui_Weapon_Loop",):
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
arm.animation_data.action = bpy.data.actions["Ui_Weapon_Loop"]
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
pw = {}
for pb in ORDER:
    local = Matrix.LocRotScale(pb.location * ANIM_SCALE, pb.rotation_quaternion, pb.scale)
    pw[pb.name] = (RIG_ALIGN @ local) if pb.parent is None else (pw[pb.parent.name] @ local)
for pb in ORDER:
    pb.matrix = pw[pb.name]
    bpy.context.view_layer.update()

for bone, side in (("WeaponProp01", "L"), ("WeaponProp02", "R")):
    pm = arm.pose.bones[bone].matrix
    hand = arm.pose.bones["Bip001%sHand" % side].matrix
    fa = arm.pose.bones["Bip001%sForearm" % side].matrix
    ua = arm.pose.bones["Bip001%sUpperArm" % side].matrix
    fore = (hand.translation - fa.translation).normalized()
    upper = (fa.translation - ua.translation).normalized()
    f0 = arm.pose.bones["Bip001%sFinger0" % side].matrix.translation
    f4 = arm.pose.bones["Bip001%sFinger4" % side].matrix.translation
    print("HAND", bone, side, "pos", [round(c, 1) for c in pm.translation],
          "hand", [round(c, 1) for c in hand.translation],
          "forearm_dir", [round(c, 2) for c in fore],
          "upperarm_dir", [round(c, 2) for c in upper])
    for nm, v in (("X", Vector((1, 0, 0))), ("Y", Vector((0, 1, 0))), ("Z", Vector((0, 0, 1))),
                  ("-X", Vector((-1, 0, 0))), ("-Y", Vector((0, -1, 0))), ("-Z", Vector((0, 0, -1)))):
        a = (pm.to_3x3() @ v).normalized()
        tip = pm.translation + a * BLADE
        print("   OPT", bone, nm, "blade", [round(c, 2) for c in a],
              "to_forearm", round(math.degrees(a.angle(fore)), 1),
              "to_upperarm", round(math.degrees(a.angle(upper)), 1),
              "tip", [round(c, 1) for c in tip])
print("HAND_DONE")
