import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_face as rig

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
SCALE = 0.915502
XS = [-2.4, -1.8, -1.2, -0.6, 0.0, 0.6, 1.2, 1.8, 2.4]
LEVELS = (0.35, 0.7, 1.0)
LABEL = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "r9"
SWEEP = [float(v) for v in sys.argv[sys.argv.index("--") + 2].split(",")] if len(sys.argv) > sys.argv.index("--") + 2 else []

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = max([o for o in bpy.data.objects if o.type == 'MESH'], key=lambda o: len(o.data.vertices))
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
arm.scale = (SCALE, SCALE, SCALE)
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
body.data.transform(Matrix.Scale(SCALE, 4))
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()

parts = rig.load_parts()
rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)

arm.rotation_mode = 'XYZ'
arm.rotation_euler = (0.0, 0.0, math.radians(90.0))
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
body.data.transform(Matrix.Rotation(math.radians(90.0), 4, 'Z'))
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()

gname = {g.index: g.name for g in body.vertex_groups}
co = [v.co.copy() for v in body.data.vertices]
mouth = sum((co[i] for i in parts["mouth_ap"]), Vector()) / len(parts["mouth_ap"])
print("N9_MOUTH", [round(v, 4) for v in mouth])
names = [m.name for m in body.data.materials]
face_slot = names.index("MI_R2T1JinxiMd10011Face")
face_verts = set()
for p in body.data.polygons:
    if p.material_index == face_slot:
        face_verts.update(p.vertices)


def weight_of(vi, bone):
    for g in body.data.vertices[vi].groups:
        if gname[g.group] == bone:
            return g.weight
    return 0.0


SEAM_UP = []
SEAM_LO = []
for xs in XS:
    up_lip = []
    up_corner = []
    lo_jaw = []
    for vi in face_verts:
        c = co[vi]
        if abs(c.y - xs) > 0.15 or c.x < 2.0 or abs(c.z - mouth.z) > 0.60:
            continue
        if weight_of(vi, "JX_LipUp") > 0.05:
            up_lip.append(vi)
        if max(weight_of(vi, "JX_MouthCorner_L"), weight_of(vi, "JX_MouthCorner_R")) > 0.05 and c.z > mouth.z:
            up_corner.append(vi)
        if weight_of(vi, "JX_Jaw") > 0.01:
            lo_jaw.append(vi)
    upper = up_lip if up_lip else up_corner
    SEAM_UP.append(min(upper, key=lambda vi: co[vi].z) if upper else None)
    SEAM_LO.append(max(lo_jaw, key=lambda vi: co[vi].z) if lo_jaw else None)

for i, xs in enumerate(XS):
    for tag, vi in (("UP", SEAM_UP[i]), ("LO", SEAM_LO[i])):
        if vi is None:
            print("N9_SEAM %s x=%+.1f NONE" % (tag, xs))
            continue
        print("N9_SEAM %s x=%+.1f vi=%d z=%.4f w=%s" % (
            tag, xs, vi, co[vi].z, {gname[g.group]: round(g.weight, 3) for g in body.data.vertices[vi].groups}))

rest_all = {b.name: b.matrix_local.copy() for b in arm.data.bones}
pose_world = {n: rest_all[n].copy() for n in rest_all if n.startswith("JX_")}
base_world = {n: pose_world[n].copy() for n in pose_world}


def deform(params):
    for n in pose_world:
        pose_world[n] = base_world[n].copy()
    rig.pose_face(pose_world, params, rest_all)
    dl = {n: pose_world[n] @ rest_all[n].inverted() for n in pose_world}
    pos = []
    for v in body.data.vertices:
        w = [(gname[g.group], g.weight) for g in v.groups]
        keep = 1.0 - sum(x for k, x in w if k in dl)
        p = v.co * keep
        for k, x in w:
            if k in dl:
                p = p + (dl[k] @ v.co) * x
        pos.append(p)
    return pos


rest_gap = [co[SEAM_UP[i]].z - co[SEAM_LO[i]].z for i in range(9)]
print("N9_REST_GAP", " ".join("%.4f" % v for v in rest_gap))
print("N9_REST_ABS", " ".join("%.4f" % v for v in rest_gap))

SURF_UP = []
SURF_LO = []
for xs in XS:
    bu = None
    bl = None
    for vi in face_verts:
        c = co[vi]
        if abs(c.y - xs) > 0.15 or c.x < 2.2:
            continue
        if mouth.z <= c.z <= mouth.z + 0.2 and (bu is None or c.x > co[bu].x):
            bu = vi
        if mouth.z - 0.5 <= c.z <= mouth.z - 0.02 and (bl is None or c.x > co[bl].x):
            bl = vi
    SURF_UP.append(bu)
    SURF_LO.append(bl)
print("N9_SURF_GAP", " ".join("%.4f" % (co[SURF_UP[i]].z - co[SURF_LO[i]].z) for i in range(9)))

for ang in [rig.JAW_MAX_DEG] + SWEEP:
    rig.JAW_MAX_DEG = ang
    for lvl in LEVELS:
        pos = deform({"jaw": lvl})
        gaps = [pos[SEAM_UP[i]].z - pos[SEAM_LO[i]].z for i in range(9)]
        net = [gaps[i] - rest_gap[i] for i in range(9)]
        sgaps = [pos[SURF_UP[i]].z - pos[SURF_LO[i]].z for i in range(9)]
        mono = all(net[i] < net[i + 1] for i in range(4)) and all(net[i] > net[i + 1] for i in range(4, 8))
        print("N9_ROW ang=%.2f lvl=%.2f net=%s" % (ang, lvl, " ".join("%.4f" % v for v in net)))
        print("N9_ABS ang=%.2f lvl=%.2f abs=%s surf=%s" % (
            ang, lvl, " ".join("%.4f" % v for v in gaps), " ".join("%.4f" % v for v in sgaps)))
        print("N9_CHK ang=%.2f lvl=%.2f center=%.4f corner=%.4f mono=%s" % (
            ang, lvl, net[4], 0.5 * (net[0] + net[8]), mono))
print("N9_DONE", LABEL)
