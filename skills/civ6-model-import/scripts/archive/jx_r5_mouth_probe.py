import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_face as rig

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r5_vcheck")
SCALE = 0.915502
os.makedirs(OUT, exist_ok=True)

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

co = [v.co.copy() for v in body.data.vertices]
ring = parts["mouth_ap"]
mouth = sum((co[i] for i in ring), Vector()) / len(ring)
print("PROBE_MOUTH", [round(v, 4) for v in mouth])
print("PROBE_BOX", [round(min(c[i] for c in co), 3) for i in range(3)], [round(max(c[i] for c in co), 3) for i in range(3)])

gi = {g.name: g.index for g in body.vertex_groups}
jaw_g = gi.get("JX_Jaw", -1)
lip_g = gi.get("JX_LipUp", -1)


def weights(vi):
    j = 0.0
    l = 0.0
    for g in body.data.vertices[vi].groups:
        if g.group == jaw_g:
            j = g.weight
        elif g.group == lip_g:
            l = g.weight
    return j, l


dg0 = bpy.context.evaluated_depsgraph_get()
ev0 = body.evaluated_get(dg0)
me0 = ev0.to_mesh()
print("PROBE_BIND_COUNT", len(me0.vertices), len(co))
print("PROBE_BIND_DELTA", round(max((me0.vertices[i].co - co[i]).length for i in range(0, len(co), 37)), 6))
print("PROBE_HEAD_POSE", [round(v, 4) for v in arm.pose.bones["Bip001Head"].head],
      [round(v, 4) for v in arm.pose.bones["Bip001Head"].matrix.translation],
      [round(v, 4) for v in arm.data.bones["Bip001Head"].head_local])
ev0.to_mesh_clear()

rest = {b.name: b.matrix_local.copy() for b in arm.data.bones if b.name.startswith("JX_")}
rest_all = {b.name: b.matrix_local.copy() for b in arm.data.bones}
pose_world = {b.name: b.matrix_local.copy() for b in arm.data.bones if b.name.startswith("JX_")}
rig.pose_face(pose_world, {"jaw": 1.0}, rest_all)
for pb in arm.pose.bones:
    if pb.name.startswith("JX_"):
        delta = pose_world[pb.name] @ rest_all[pb.name].inverted()
        pb.matrix = delta @ pb.matrix
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(dg)
me = ev.to_mesh()
open_co = [ev.matrix_world @ v.co for v in me.vertices]
ev.to_mesh_clear()

print("PROBE_ARM_WORLD", [round(c, 5) for row in arm.matrix_world for c in row])
print("PROBE_BODY_WORLD", [round(c, 5) for row in body.matrix_world for c in row])
print("PROBE_JAW_POSE_HEAD", [round(v, 4) for v in arm.pose.bones["JX_Jaw"].head])
print("PROBE_LIP_POSE_HEAD", [round(v, 4) for v in arm.pose.bones["JX_LipUp"].head])
far = [v.index for v in body.data.vertices if v.co.z > 139.0][:5]
for vi in far:
    print("PROBE_FAR", vi, [round(c, 4) for c in co[vi]], [round(c, 4) for c in open_co[vi]])

rows = []
for vi in ring:
    j, l = weights(vi)
    p = co[vi]
    q = open_co[vi]
    side = "up" if p.z >= mouth.z else "lo"
    rows.append((vi, side, p.x, p.z, q.x, q.z, j, l))
rows.sort(key=lambda r: (r[1], r[2]))
path = os.path.join(OUT, "mouth_ring.tsv")
with open(path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("vi\tside\trest_x\trest_z\topen_x\topen_z\tdz\tJaw\tLipUp\n")
    for vi, side, rx, rz_, ox, oz, j, l in rows:
        fh.write("%d\t%s\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\n" % (vi, side, rx, rz_, ox, oz, oz - rz_, j, l))

up = [r for r in rows if r[1] == "up"]
lo = [r for r in rows if r[1] == "lo"]
print("PROBE_RING", len(rows), "up", len(up), "lo", len(lo))
print("PROBE_RING_X", round(min(r[2] for r in rows), 3), round(max(r[2] for r in rows), 3))
print("PROBE_RING_Z", round(min(r[3] for r in rows), 3), round(max(r[3] for r in rows), 3))
print("PROBE_JAW_RANGE", round(min(r[6] for r in rows), 3), round(max(r[6] for r in rows), 3))
print("PROBE_LIP_RANGE", round(min(r[7] for r in rows), 3), round(max(r[7] for r in rows), 3))

region = []
for v in body.data.vertices:
    p = co[v.index]
    if abs(p.x) < 4.5 and p.y < -1.0 and abs(p.z - mouth.z) < 2.0:
        j, l = weights(v.index)
        region.append((v.index, p.x, p.y, p.z, open_co[v.index].z, j, l))
rp = os.path.join(OUT, "mouth_region.tsv")
with open(rp, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("vi\tx\ty\tz\topen_z\tdz\tJaw\tLipUp\n")
    for vi, x, y, z, oz, j, l in sorted(region, key=lambda r: (r[1], r[3])):
        fh.write("%d\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\n" % (vi, x, y, z, oz, oz - z, j, l))
print("PROBE_REGION", len(region), rp)
print("PROBE_DONE")
