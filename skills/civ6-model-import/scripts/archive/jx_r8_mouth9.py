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
LABEL = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "r8"
XS = [-2.4, -1.8, -1.2, -0.6, 0.0, 0.6, 1.2, 1.8, 2.4]

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

# 与 jx_build5.rotate_rig 一致：成品朝向 = 绕 Z 轴 90 度
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
arm.rotation_mode = 'XYZ'
arm.rotation_euler = (0.0, 0.0, math.radians(90.0))
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
body.data.transform(Matrix.Rotation(math.radians(90.0), 4, 'Z'))
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()

gname = {g.index: g.name for g in body.vertex_groups}
co = [v.co.copy() for v in body.data.vertices]
nrm = [v.normal.copy() for v in body.data.vertices]
mouth = sum((co[i] for i in parts["mouth_ap"]), Vector()) / len(parts["mouth_ap"])
print("M9_MOUTH", [round(v, 4) for v in mouth])

for bone in ("JX_Jaw", "JX_LipLo", "JX_LipUp", "JX_MouthCorner_L", "JX_MouthCorner_R"):
    vg = body.vertex_groups.get(bone)
    if vg is None:
        print("M9_GROUP", bone, "MISSING")
        continue
    total = 0
    acc = 0.0
    top = 0.0
    high = 0
    for v in body.data.vertices:
        for g in v.groups:
            if g.group != vg.index:
                continue
            total += 1
            acc += g.weight
            top = max(top, g.weight)
            if g.weight >= 0.9:
                high += 1
    print("M9_GROUP %s verts=%d mean=%.4f max=%.4f ge090=%d" % (
        bone, total, acc / max(1, total), top, high))

names = [m.name for m in body.data.materials]
face_slot = names.index("MI_R2T1JinxiMd10011Face")
face_verts = set()
for p in body.data.polygons:
    if p.material_index == face_slot:
        face_verts.update(p.vertices)
outer = [vi for vi in face_verts if nrm[vi].x > 0.2]
print("M9_OUTER", len(outer), "of", len(face_verts))


def pick(xs, zlo, zhi):
    best = None
    for vi in outer:
        c = co[vi]
        if abs(c.y - xs) > 0.15 or c.x < 2.2:
            continue
        if not (zlo <= c.z <= zhi):
            continue
        if best is None or c.x > co[best].x:
            best = vi
    return best


SEAM_UP = [pick(xs, mouth.z, mouth.z + 0.2) for xs in XS]
SEAM_LO = [pick(xs, mouth.z - 0.5, mouth.z - 0.02) for xs in XS]
for tag, seam in (("UP", SEAM_UP), ("LO", SEAM_LO)):
    for xs, vi in zip(XS, seam):
        if vi is None:
            print("M9_W %s x=%+.1f NONE" % (tag, xs))
            continue
        print("M9_W %s x=%+.1f vi=%d z=%.3f %s" % (
            tag, xs, vi, co[vi].z, {gname[g.group]: round(g.weight, 3) for g in body.data.vertices[vi].groups}))

rest_all = {b.name: b.matrix_local.copy() for b in arm.data.bones}
pose_world = {n: rest_all[n].copy() for n in rest_all if n.startswith("JX_")}
rig.pose_face(pose_world, {"jaw": 1.0}, rest_all)
delta = {n: pose_world[n] @ rest_all[n].inverted() for n in pose_world}
for name in sorted(delta):
    print("M9_DELTA", name, [round(delta[name][i][3], 4) for i in range(3)])

opened = []
for v in body.data.vertices:
    weights = [(gname[g.group], g.weight) for g in v.groups]
    keep = 1.0 - sum(x for k, x in weights if k in delta)
    p = v.co * keep
    for k, x in weights:
        if k in delta:
            p = p + (delta[k] @ v.co) * x
    opened.append(p)

print("M9_TABLE", LABEL)
rows = []
for i, xs in enumerate(XS):
    if SEAM_UP[i] is None or SEAM_LO[i] is None:
        print("M9_ROW x=%+.1f 缺采样点" % xs)
        continue
    up = opened[SEAM_UP[i]].z
    lo = opened[SEAM_LO[i]].z
    rup = co[SEAM_UP[i]].z
    rlo = co[SEAM_LO[i]].z
    rows.append((xs, rup, rlo, up, lo, up - lo))
    print("M9_ROW x=%+.1f rest_up=%.3f rest_lo=%.3f open_up=%.3f open_lo=%.3f gap=%.3f up_dz=%+.3f lo_dz=%+.3f" % (
        xs, rup, rlo, up, lo, up - lo, up - rup, lo - rlo))
gaps = [r[5] for r in rows]
print("M9_GAP", " ".join("%.3f" % v for v in gaps))
if len(gaps) == 9:
    mono = all(gaps[i] < gaps[i + 1] for i in range(4)) and all(gaps[i] > gaps[i + 1] for i in range(4, 8))
    print("M9_RATIO center=%.4f corner=%.4f ratio=%.3f monotone=%s" % (
        gaps[4], 0.5 * (gaps[0] + gaps[8]), gaps[4] / max(1e-6, 0.5 * (gaps[0] + gaps[8])), mono))
print("M9_DONE", LABEL)
