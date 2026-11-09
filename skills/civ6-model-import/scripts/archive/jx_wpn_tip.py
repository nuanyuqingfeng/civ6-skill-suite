import bpy
import math

from mathutils import Matrix, Vector

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"
CLIPS = ["Ui_Weapon_Start", "Ui_Weapon_Loop", "Ui_Weapon_End"]
RIG_ALIGN = Matrix.Rotation(math.radians(90.0), 4, 'Z')
ANIM_SCALE = 100.0
BLADE = 144.3
CAND = [("WeaponProp01", "Y"), ("WeaponProp01", "X"), ("WeaponProp02", "Y"), ("WeaponProp02", "Z")]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = [o for o in bpy.data.objects if o.type == 'MESH'][0]
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


AX = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1)),
      "-X": Vector((-1, 0, 0)), "-Y": Vector((0, -1, 0)), "-Z": Vector((0, 0, -1))}
for clip in CLIPS:
    act = bpy.data.actions[clip]
    arm.animation_data.action = act
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    for f in range(f0, f1 + 1, 10):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        apply_correct_pose()
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        me = ev.to_mesh()
        zs = [(ev.matrix_world @ v.co).z for v in me.vertices]
        ev.to_mesh_clear()
        line = ["POSE", clip, f, "feet_z", round(min(zs), 1)]
        for bone, ax in CAND:
            pm = arm.pose.bones[bone].matrix
            a = (pm.to_3x3() @ AX[ax]).normalized()
            tip = pm.translation + a * BLADE
            line += [bone[-2:] + ax, round(tip.z, 1)]
        print(" ".join(str(x) for x in line))
print("TIP_DONE")
