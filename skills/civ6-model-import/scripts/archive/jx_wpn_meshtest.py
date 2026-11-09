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
CANDIDATES = ["WeaponProp01", "WeaponProp02"]
AXES = [("X", Vector((1, 0, 0))), ("-X", Vector((-1, 0, 0))), ("Y", Vector((0, 1, 0))),
        ("-Y", Vector((0, -1, 0))), ("Z", Vector((0, 0, 1))), ("-Z", Vector((0, 0, -1)))]
SAMPLES = {"Ui_Weapon_Start": [0, 15, 30, 45, 60], "Ui_Weapon_Loop": [0, 20, 40, 60, 80],
           "Ui_Weapon_End": [0, 20, 40, 60, 70]}

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = [o for o in bpy.data.objects if o.type == 'MESH'][0]
bpy.ops.import_scene.fbx(filepath=FBX)
weapon = [o for o in bpy.data.objects if o.type == 'MESH' and o is not body][0]
warm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o is not arm][0]
# 武器 FBX 以米为单位，PSK 骨架以厘米为单位：入骨架空间需放大 100 倍
wverts = [(weapon.matrix_world @ v.co) * 100.0 for v in weapon.data.vertices]
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


def palm_frame():
    f0 = arm.pose.bones["Bip001LFinger0"].matrix.translation.copy()
    f01 = arm.pose.bones["Bip001LFinger01"].matrix.translation.copy()
    f4 = arm.pose.bones["Bip001LFinger4"].matrix.translation.copy()
    fingers = (f01 - f0).normalized()
    across = (f4 - f0).normalized()
    return (f0 + f4) * 0.5, fingers, across, fingers.cross(across).normalized()


def frame_for(axis, palm_n):
    a = axis.normalized()
    z = (palm_n - a * palm_n.dot(a))
    z.normalize()
    y = z.cross(a)
    return Matrix(((a.x, y.x, z.x, 0.0), (a.y, y.y, z.y, 0.0), (a.z, y.z, z.z, 0.0), (0.0, 0.0, 0.0, 1.0)))


STATS = {}
for clip in CLIPS:
    arm.animation_data.action = bpy.data.actions[clip]
    for f in SAMPLES[clip]:
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
        pc, fingers, across, pn = palm_frame()
        for bone in CANDIDATES:
            pm = arm.pose.bones[bone].matrix
            pnb = pm.to_3x3().inverted() @ pn
            pnb.normalize()
            for aname, avec in AXES:
                R = frame_for(avec, pnb)
                M = pm @ R
                inside = 0
                blade_inside = 0
                zmin = 1e9
                for v in wverts:
                    p = M @ v
                    zmin = min(zmin, p.z)
                    hit = tree.find_nearest(p, 0.6)
                    if hit[0] is None:
                        continue
                    loc, nrm, idx, dist = hit
                    if (p - loc).dot(nrm) < 0.0:
                        inside += 1
                        if v.x > 20.0:
                            blade_inside += 1
                rec = STATS.setdefault((bone, aname), {"inside": 0, "blade_inside": 0, "zmin": 1e9, "n": 0})
                rec["inside"] += inside
                rec["blade_inside"] += blade_inside
                rec["zmin"] = min(rec["zmin"], zmin)
                rec["n"] += 1
        print("FRAME_DONE", clip, f, "palm_center", [round(c, 1) for c in pc],
              "palm_normal", [round(c, 2) for c in pn])

for key in sorted(STATS):
    rec = STATS[key]
    print("MESHTEST", key[0], key[1], "inside_verts_total", rec["inside"],
          "blade_inside", rec["blade_inside"], "zmin", round(rec["zmin"], 2), "frames", rec["n"])
print("MESHTEST_DONE")
