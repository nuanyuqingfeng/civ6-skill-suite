import bpy
import math

from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

BLEND = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx\weapon_rigged.blend"
CLIPS = ["Ui_Weapon_Start", "Ui_Weapon_Loop", "Ui_Weapon_End"]
RIG_ALIGN = Matrix.Rotation(math.radians(90.0), 4, 'Z')
ANIM_SCALE = 100.0
BONE = "WeaponProp01"
SIDE = "L"

bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
weapon = bpy.data.objects["JinhsiWeapon"]
body = [o for o in bpy.data.objects if o.type == 'MESH' and o is not weapon][0]
bound = {g.index: 0 for g in weapon.vertex_groups}
for v in weapon.data.vertices:
    for g in v.groups:
        bound[g.group] += 1
print("OPENED", arm.name, "weapon_verts", len(weapon.data.vertices), "body_verts", len(body.data.vertices))
print("BIND", [(g.name, bound[g.index]) for g in weapon.vertex_groups],
      [(m.type, m.object.name) for m in weapon.modifiers],
      "materials", [m.name for m in weapon.data.materials], "uv", [u.name for u in weapon.data.uv_layers])
print("REST_BOX", [round(min(v.co[i] for v in weapon.data.vertices), 2) for i in range(3)],
      [round(max(v.co[i] for v in weapon.data.vertices), 2) for i in range(3)])
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


def eval_mesh(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    pts = [ev.matrix_world @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return pts, polys


summary = {"inside": 0, "zmin": 1e9, "grip_max": 0.0, "tip_z_min": 1e9, "tip_z_max": -1e9}
for clip in CLIPS:
    act = bpy.data.actions[clip]
    arm.animation_data.action = act
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    for f in range(f0, f1 + 1, 5):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        apply_correct_pose()
        wp, _ = eval_mesh(weapon)
        bp, bpolys = eval_mesh(body)
        tree = BVHTree.FromPolygons(bp, bpolys, all_triangles=False)
        grip = arm.pose.bones[BONE].matrix.translation.copy()
        far = max(wp, key=lambda p: (p - grip).length)
        inside = 0
        for p in wp:
            hit = tree.find_nearest(p, 0.8)
            if hit[0] is None:
                continue
            loc, nrm, idx, dist = hit
            if (p - loc).dot(nrm) < 0.0:
                inside += 1
        f0p = arm.pose.bones["Bip001%sFinger0" % SIDE].matrix.translation
        f4p = arm.pose.bones["Bip001%sFinger4" % SIDE].matrix.translation
        f02p = arm.pose.bones["Bip001%sFinger02" % SIDE].matrix.translation
        palm = (f0p + f4p + f02p) / 3.0
        gd = (grip - palm).length
        summary["inside"] = max(summary["inside"], inside)
        summary["zmin"] = min(summary["zmin"], min(p.z for p in wp))
        summary["grip_max"] = max(summary["grip_max"], gd)
        summary["tip_z_min"] = min(summary["tip_z_min"], far.z)
        summary["tip_z_max"] = max(summary["tip_z_max"], far.z)
        print("VERIFY", clip, f, "weapon_z", [round(min(p.z for p in wp), 1), round(max(p.z for p in wp), 1)],
              "tip", [round(c, 1) for c in far], "blade_len", round((far - grip).length, 1),
              "inside_verts", inside, "grip_to_palm", round(gd, 2))
print("SUMMARY", "max_inside_verts", summary["inside"], "weapon_zmin", round(summary["zmin"], 2),
      "grip_to_palm_max", round(summary["grip_max"], 2),
      "tip_z", [round(summary["tip_z_min"], 1), round(summary["tip_z_max"], 1)])
print("VERIFY_DONE")
