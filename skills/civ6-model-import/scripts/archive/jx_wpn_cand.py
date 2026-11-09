import bpy
import math

from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
FBX = r"D:\desktop\Material\建模文件\WeaponJinXIWeapon\JinxiSwordModel.fbx"
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"
CLIPS = ["Ui_Weapon_Start", "Ui_Weapon_Loop", "Ui_Weapon_End"]
RIG_ALIGN = Matrix.Rotation(math.radians(90.0), 4, 'Z')
ANIM_SCALE = 100.0
CAND = ["WeaponProp01", "WeaponProp02"]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = [o for o in bpy.data.objects if o.type == 'MESH'][0]
bpy.ops.import_scene.fbx(filepath=FBX)
weapon = [o for o in bpy.data.objects if o.type == 'MESH' and o is not body][0]
warm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o is not arm][0]
loc = [(weapon.matrix_world @ v.co) * 100.0 for v in weapon.data.vertices]
bpy.ops.object.select_all(action='DESELECT')
warm.select_set(True)
bpy.context.view_layer.objects.active = warm
bpy.ops.object.delete(use_global=False)
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


REST = {b: arm.data.bones[b].matrix_local.copy() for b in CAND}
STATS = {b: {"zmin": 1e9, "zmin_f": None, "inside_max": 0, "inside_f": None, "inside_sum": 0} for b in CAND}
for clip in CLIPS:
    act = bpy.data.actions[clip]
    arm.animation_data.action = act
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    for f in range(f0, f1 + 1, 2):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        apply_correct_pose()
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        me = ev.to_mesh()
        bp = [ev.matrix_world @ v.co for v in me.vertices]
        bpolys = [tuple(p.vertices) for p in me.polygons]
        ev.to_mesh_clear()
        tree = BVHTree.FromPolygons(bp, bpolys, all_triangles=False)
        for b in CAND:
            M = arm.pose.bones[b].matrix @ REST[b].inverted() @ REST[b] @ Matrix.Scale(100.0, 4)
            pts = [M @ v for v in loc]
            zmin = min(p.z for p in pts)
            inside = 0
            for p in pts:
                hit = tree.find_nearest(p, 0.8)
                if hit[0] is None:
                    continue
                if (p - hit[0]).dot(hit[1]) < 0.0:
                    inside += 1
            s = STATS[b]
            s["inside_sum"] += inside
            if inside > s["inside_max"]:
                s["inside_max"] = inside
                s["inside_f"] = (clip, f)
            if zmin < s["zmin"]:
                s["zmin"] = zmin
                s["zmin_f"] = (clip, f)
for b in CAND:
    s = STATS[b]
    print("CAND", b, "zmin", round(s["zmin"], 2), "at", s["zmin_f"],
          "inside_max", s["inside_max"], "at", s["inside_f"], "inside_sum", s["inside_sum"])
print("CAND_DONE")
