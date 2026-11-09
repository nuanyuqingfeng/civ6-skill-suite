import bpy
import math

from mathutils import Matrix, Vector

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"
CLIPS = ["Ui_Weapon_Start", "Ui_Weapon_Loop", "Ui_Weapon_End"]
RIG_ALIGN = Matrix.Rotation(math.radians(90.0), 4, 'Z')
ANIM_SCALE = 100.0
CANDIDATES = [("WeaponProp01", "Bip001LHand"), ("WeaponProp02", "Bip001RHand")]
AXES = [("X", Vector((1, 0, 0))), ("-X", Vector((-1, 0, 0))), ("Y", Vector((0, 1, 0))),
        ("-Y", Vector((0, -1, 0))), ("Z", Vector((0, 0, 1))), ("-Z", Vector((0, 0, -1)))]
BLADE_CM = 144.3

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


def topo(armature):
    order = []
    seen = set()

    def visit(pb):
        if pb.name in seen:
            return
        seen.add(pb.name)
        if pb.parent is not None:
            visit(pb.parent)
        order.append(pb)

    for pb in armature.pose.bones:
        visit(pb)
    return order


ORDER = topo(arm)
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'


def apply_correct_pose():
    pose_world = {}
    for pb in ORDER:
        local = Matrix.LocRotScale(pb.location * ANIM_SCALE, pb.rotation_quaternion, pb.scale)
        if pb.parent is None:
            pose_world[pb.name] = RIG_ALIGN @ local
        else:
            pose_world[pb.name] = pose_world[pb.parent.name] @ local
    for pb in ORDER:
        pb.matrix = pose_world[pb.name]
        bpy.context.view_layer.update()
    return pose_world


def seg_point_dist(a, b, p):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (a + ab * t - p).length


def spine_clearance(a, b):
    worst = 1e9
    for z in (58.0, 70.0, 82.0, 94.0, 106.0, 118.0, 130.0, 142.0):
        worst = min(worst, seg_point_dist(a, b, Vector((0.0, 0.0, z))))
    return worst


CACHE = {}
for clip in CLIPS:
    act = bpy.data.actions[clip]
    arm.animation_data.action = act
    f0 = int(act.frame_range[0])
    f1 = int(act.frame_range[1])
    step = max(1, (f1 - f0) // 12)
    frames = list(range(f0, f1 + 1, step))
    if frames[-1] != f1:
        frames.append(f1)
    for f in frames:
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        apply_correct_pose()
        if f == frames[0]:
            dg = bpy.context.evaluated_depsgraph_get()
            ev = body.evaluated_get(dg)
            me = ev.to_mesh()
            zs = [(ev.matrix_world @ v.co).z for v in me.vertices]
            ys = [(ev.matrix_world @ v.co).y for v in me.vertices]
            ev.to_mesh_clear()
            print("BODY_POSED", clip, f, "z", [round(min(zs), 2), round(max(zs), 2)],
                  "y", [round(min(ys), 2), round(max(ys), 2)])
        for bone, parent in CANDIDATES:
            pm = arm.pose.bones[bone].matrix
            for aname, avec in AXES:
                grip = pm.translation.copy()
                axis = (pm.to_3x3() @ avec).normalized()
                tip = grip + axis * BLADE_CM
                key = (bone, aname)
                rec = CACHE.setdefault(key, {"tip_z": [], "clear": []})
                rec["tip_z"].append(tip.z)
                rec["clear"].append(spine_clearance(grip, tip))
        if f == frames[0]:
            for bn in ("Bip001LHand", "Bip001RHand", "WeaponProp01", "WeaponProp02"):
                print("POSED_BONE", clip, f, bn, [round(c, 2) for c in arm.pose.bones[bn].matrix.translation])

for key, rec in CACHE.items():
    print("ATTACH2", key[0], key[1], "tip_z_min", round(min(rec["tip_z"]), 2),
          "spine_clear_min", round(min(rec["clear"]), 2))
print("ATTACH2_DONE")
