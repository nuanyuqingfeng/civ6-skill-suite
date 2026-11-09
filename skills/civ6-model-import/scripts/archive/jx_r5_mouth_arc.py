import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_face as rig

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r5_vcheck")
SCALE = 0.915502
LABEL = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "before"
XS = [-2.4, -1.8, -1.2, -0.6, 0.0, 0.6, 1.2, 1.8, 2.4]
STEP = 0.005
SPAN = 1.5
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
if LABEL == "before":
    rig.MOUTH_CORNER_HALF_CM = 0.0
    print("ARC_BEFORE_MODE", LABEL, "corner disabled")
elif LABEL.startswith("v"):
    _p = LABEL[1:].split("_")
    rig.JAW_RAMP_SPAN_CM = float(_p[0])
    rig.JAW_RAMP_SHIFT_CM = float(_p[1])
    if float(_p[2]) < 0.0:
        rig.MOUTH_CORNER_HALF_CM = 0.0
    else:
        rig.MOUTH_CORNER_LIFT_CM = float(_p[2])
    print("ARC_VARIANT", LABEL, "span", rig.JAW_RAMP_SPAN_CM, "shift", rig.JAW_RAMP_SHIFT_CM,
          "lift", rig.MOUTH_CORNER_LIFT_CM, "half", rig.MOUTH_CORNER_HALF_CM)
rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)

rest_all = {b.name: b.matrix_local.copy() for b in arm.data.bones}
co = [v.co.copy() for v in body.data.vertices]
ring = parts["mouth_ap"]
mouth = sum((co[i] for i in ring), Vector()) / len(ring)
print("ARC_MOUTH", LABEL, [round(v, 4) for v in mouth])

names = [m.name for m in body.data.materials]
face_slot = names.index("MI_R2T1JinxiMd10011Face")
face_polys = [list(p.vertices) for p in body.data.polygons if p.material_index == face_slot]
gname = {g.index: g.name for g in body.vertex_groups}


def jaw_of(vi):
    total = 0.0
    for g in body.data.vertices[vi].groups:
        name = gname[g.group]
        if name == "JX_Jaw" or name.startswith("JX_MouthCorner"):
            total += g.weight
    return total


FACE_JAW = [sum(jaw_of(v) for v in poly) / len(poly) for poly in face_polys]
print("ARC_FACE_POLYS", LABEL, len(face_polys))


def deltas(params):
    pose_world = {n: rest_all[n].copy() for n in rest_all if n.startswith("JX_")}
    rig.pose_face(pose_world, params, rest_all)
    return {n: pose_world[n] @ rest_all[n].inverted() for n in pose_world}


def deform(params):
    if params is None:
        return list(co)
    dl = deltas(params)
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


face_verts = sorted({vi for poly in face_polys for vi in poly})
normals = {}
for poly in face_polys:
    for vi in poly:
        n = body.data.vertices[vi].normal
        if vi not in normals or n.y < normals[vi]:
            normals[vi] = n.y
outer = [vi for vi in face_verts if normals[vi] < -0.2]
print("ARC_OUTER", LABEL, len(outer), "of", len(face_verts))


def select_seam(xs_list):
    upper, lower = [], []
    for xs in xs_list:
        bu, bl = None, None
        for vi in outer:
            c = co[vi]
            if abs(c.x - xs) > 0.15 or c.y > -2.0:
                continue
            if mouth.z <= c.z <= mouth.z + 0.2 and (bu is None or c.y < bu[1]):
                bu = (vi, c.y)
            if mouth.z - 0.5 <= c.z < mouth.z and (bl is None or c.y < bl[1]):
                bl = (vi, c.y)
        upper.append(bu[0] if bu else None)
        lower.append(bl[0] if bl else None)
    return upper, lower


def lip_line(pos, xs_list):
    return ([pos[vi].z for vi in SEAM_UP], [pos[vi].z for vi in SEAM_LO])


def fit_circle(points):
    n = len(points)
    mx = sum(p[0] for p in points) / n
    mz = sum(p[1] for p in points) / n
    suu = sum((p[0] - mx) ** 2 for p in points)
    svv = sum((p[1] - mz) ** 2 for p in points)
    suv = sum((p[0] - mx) * (p[1] - mz) for p in points)
    suuu = sum((p[0] - mx) ** 3 for p in points)
    svvv = sum((p[1] - mz) ** 3 for p in points)
    suvv = sum((p[0] - mx) * (p[1] - mz) ** 2 for p in points)
    svuu = sum((p[1] - mz) * (p[0] - mx) ** 2 for p in points)
    a = 2.0 * (suu * svv - suv * suv)
    b1 = suuu + suvv
    b2 = svvv + svuu
    uc = (svv * b1 - suv * b2) / a
    vc = (suu * b2 - suv * b1) / a
    r = math.sqrt(uc * uc + vc * vc + (suu + svv) / n)
    dev = [abs(math.hypot(p[0] - mx - uc, p[1] - mz - vc) - r) for p in points]
    return (mx + uc, mz + vc, r, dev)


SEAM_UP, SEAM_LO = select_seam(XS)
print("ARC_SEAM", LABEL, [(vi, round(co[vi].x, 2), round(co[vi].z, 3), {gname[g.group]: round(g.weight, 2) for g in body.data.vertices[vi].groups}) for vi in SEAM_UP])
print("ARC_SEAM_LO", LABEL, [(vi, round(co[vi].x, 2), round(co[vi].z, 3), {gname[g.group]: round(g.weight, 2) for g in body.data.vertices[vi].groups}) for vi in SEAM_LO])
rest_up, rest_lo = lip_line(co, XS)
PARAMS = {"jaw": 1.0, "lip": 0.65}
if LABEL == "before":
    PARAMS["corner"] = 0.0
open_pos = deform(PARAMS)
open_up, open_lo = lip_line(open_pos, XS)

table = {
    "label": LABEL,
    "mouth": [round(v, 4) for v in mouth],
    "xs": XS,
    "rest_upper": [round(v, 4) for v in rest_up],
    "rest_lower": [round(v, 4) for v in rest_lo],
    "open_upper": [round(v, 4) for v in open_up],
    "open_lower": [round(v, 4) for v in open_lo],
    "open_gap": [round(u - l, 4) for u, l in zip(open_up, open_lo)],
    "upper_dz": [round(u - r, 4) for u, r in zip(open_up, rest_up)],
    "lower_dz": [round(l - r, 4) for l, r in zip(open_lo, rest_lo)],
}
pts = [(XS[i], open_up[i]) for i in range(9)] + [(XS[i], open_lo[i]) for i in range(9)]
cx, cz, r, dev = fit_circle(pts)
table["circle"] = {"cx": round(cx, 4), "cz": round(cz, 4), "r": round(r, 4), "max_dev": round(max(dev), 4),
                   "dev_points": [round(d, 4) for d in dev]}
table["up_center_minus_corner"] = round(open_up[4] - 0.5 * (open_up[0] + open_up[8]), 4)
table["lo_center_minus_corner"] = round(open_lo[4] - 0.5 * (open_lo[0] + open_lo[8]), 4)
table["rest_up_center_minus_corner"] = round(rest_up[4] - 0.5 * (rest_up[0] + rest_up[8]), 4)
table["rest_lo_center_minus_corner"] = round(rest_lo[4] - 0.5 * (rest_lo[0] + rest_lo[8]), 4)

path = os.path.join(OUT, "mouth_arc_%s.json" % LABEL)
with open(path, "w", encoding="utf-8") as fh:
    json.dump(table, fh, ensure_ascii=False, indent=2)

print("ARC_TABLE", LABEL)
for i, xs in enumerate(XS):
    print("ARC_ROW %s x=%+.1f rest_up=%.3f rest_lo=%.3f open_up=%.3f open_lo=%.3f gap=%.3f up_dz=%+.3f lo_dz=%+.3f" % (
        LABEL, xs, rest_up[i], rest_lo[i], open_up[i], open_lo[i],
        open_up[i] - open_lo[i], table["upper_dz"][i], table["lower_dz"][i]))
print("ARC_CIRCLE", LABEL, "cx=%.4f cz=%.4f r=%.4f max_dev=%.4f" % (cx, cz, r, max(dev)))
print("ARC_SINK up_center_minus_corner=%+.4f lo_center_minus_corner=%+.4f rest_up=%+.4f rest_lo=%+.4f" % (
    table["up_center_minus_corner"], table["lo_center_minus_corner"],
    table["rest_up_center_minus_corner"], table["rest_lo_center_minus_corner"]))
print("ARC_DONE", LABEL, path)
