import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_anim as anim
import jx_r3_face as rig

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
SCALE = 0.915502
ENVELOPE = os.path.join(ROOT, "workspace", "gen", "reports", "round3_voice_envelope.json")
DASH = [i for i, a in enumerate(sys.argv) if a == "--"]
LABEL = sys.argv[DASH[-1] + 1] if DASH else "r15"
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r15_measure_" + LABEL + ".json")
XS = [-2.4, -1.8, -1.2, -0.6, 0.0, 0.6, 1.2, 1.8, 2.4]
LEVELS = (0.0, 0.35, 0.7, 1.0)
CHEEK_X = (2.0, 4.5)
CHEEK_Z = (126.0, 132.0)

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

if LABEL == "before":
    # 复原第十三轮的状态：无嘴角外扩、上睑权重不设竖向与横向窗口、下睑横向硬边界 1.60
    rig.JAW_MAX_DEG = 11.5
    rig.CORNER_OUT_CM = 0.0
    rig.MOUTH_CORNER_WEIGHT = 0.45
    rig.MOUTH_CORNER_BAND_CM = (1.70, 2.35)
    rig.MOUTH_CORNER_OUTER_CM = (9.0, 9.5)
    rig.LID_UP_FULL_ABOVE_CM = 99.0
    rig.LID_UP_FADE_ABOVE_CM = 99.5
    rig.LID_UP_FULL_W_CM = 99.0
    rig.LID_UP_FADE_W_CM = 99.5
    rig.LID_LO_FULL_W_CM = 1.60

parts = rig.load_parts()
rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)

gname = {g.index: g.name for g in body.vertex_groups}
co = [v.co.copy() for v in body.data.vertices]
names = [m.name for m in body.data.materials]
face_slot = names.index("MI_R2T1JinxiMd10011Face")
face_verts = set()
for p in body.data.polygons:
    if p.material_index == face_slot:
        face_verts.update(p.vertices)
face_verts = sorted(face_verts)
mouth = sum((co[i] for i in parts["mouth_ap"]), Vector()) / len(parts["mouth_ap"])
print("M_MOUTH", [round(v, 4) for v in mouth], "JAW_MAX_DEG", rig.JAW_MAX_DEG,
      "CORNER", getattr(rig, "CORNER_OUT_CM", 0.0), "W", rig.MOUTH_CORNER_WEIGHT, flush=True)

wts = [{gname[g.group]: g.weight for g in body.data.vertices[i].groups} for i in range(len(co))]
rest_all = {b.name: b.matrix_local.copy() for b in arm.data.bones}
face_bones = [n for n in rest_all if n.startswith("JX_")]


def deform(params):
    pose_world = {n: rest_all[n].copy() for n in face_bones}
    rig.pose_face(pose_world, params, rest_all)
    dl = {n: pose_world[n] @ rest_all[n].inverted() for n in face_bones}
    pos = []
    for v in body.data.vertices:
        p = Vector()
        used = 0.0
        for g in v.groups:
            name = gname[g.group]
            if name in dl:
                p += (dl[name] @ v.co) * g.weight
                used += g.weight
            else:
                p += v.co * g.weight
        pos.append(p)
    return pos


poses = {
    "blink": {"blink_L": 1.0, "blink_R": 1.0},
    "lid_close": {"lid_L": 0.9, "lid_R": 0.9},
}
envelope = anim.load_envelope()
poses["idle1"] = anim.facial_params("JX_IDLE", 1, envelope)
poses["idle91"] = anim.facial_params("JX_IDLE", 91, envelope)
for lvl in LEVELS:
    poses["jaw%.2f" % lvl] = {"jaw": lvl}

# 眼睑环带：眼心左右 1.95 厘米、上下 1.30 厘米以内
eyec = {"L": rig._eye_center(parts, "L"), "R": rig._eye_center(parts, "R")}
cheek = [i for i in face_verts
         if CHEEK_X[0] <= abs(co[i].x) <= CHEEK_X[1] and CHEEK_Z[0] <= co[i].z <= CHEEK_Z[1]]
lid_band = set()
for i in cheek:
    c = co[i]
    ctr = eyec["L" if c.x < 0.0 else "R"]
    if abs(c.x - ctr.x) <= 1.95 and -1.30 <= ctr.z - c.z <= 1.20 and c.y < -0.8:
        lid_band.add(i)
lash = set(parts["lashL"]) | set(parts["lashR"])
lid_band |= {i for i in cheek if i in lash}
core = [i for i in cheek if i not in lid_band]
print("M_CHEEK", len(cheek), "lid_band", len(lid_band), "core", len(core),
      "left", sum(1 for i in core if co[i].x < 0), "right", sum(1 for i in core if co[i].x > 0), flush=True)

sums = [sum(wts[i].values()) for i in cheek]
bad = [i for i, s in zip(cheek, sums) if abs(s - 1.0) > 0.02]
print("M_SUM", "bad=%d" % len(bad), "max_dev=%.6f" % max(abs(s - 1.0) for s in sums), flush=True)
per_bone = {}
for i in cheek:
    for n, w in wts[i].items():
        if n.startswith("JX_"):
            rec = per_bone.setdefault(n, [0, 0.0, 0.0])
            rec[0] += 1
            rec[1] += w
            rec[2] = max(rec[2], w)
print("M_BONES", json.dumps({k: [v[0], round(v[1], 4), round(v[2], 4)] for k, v in sorted(per_bone.items())}), flush=True)

report = {"mouth": [round(v, 4) for v in mouth], "jaw_max_deg": rig.JAW_MAX_DEG,
          "corner_out_cm": getattr(rig, "CORNER_OUT_CM", 0.0),
          "corner_weight": rig.MOUTH_CORNER_WEIGHT,
          "cheek": {"n": len(cheek), "lid_band": len(lid_band), "core": len(core),
                    "sum_bad": len(bad), "sum_max_dev": round(max(abs(s - 1.0) for s in sums), 6),
                    "bones": {k: [v[0], round(v[1], 4), round(v[2], 4)] for k, v in sorted(per_bone.items())}},
          "poses": {}, "mouth9": {}}
for label, params in poses.items():
    pos = deform(params)
    d = {i: pos[i] - co[i] for i in cheek}
    core_len = [d[i].length for i in core]
    band_len = [d[i].length for i in lid_band]
    lr = []
    for i in core:
        if co[i].x < 0.0:
            mirror = min(core, key=lambda j: abs(co[j].x + co[i].x) + abs(co[j].z - co[i].z) + abs(co[j].y - co[i].y))
            if abs(co[mirror].x + co[i].x) <= 0.05:
                lr.append((d[i] - d[mirror]).length)
    report["poses"][label] = {
        "core_max": round(max(core_len), 5), "core_mean": round(sum(core_len) / len(core_len), 5),
        "core_over": sum(1 for v in core_len if v > 0.05),
        "band_max": round(max(band_len), 5), "band_mean": round(sum(band_len) / len(band_len), 5),
        "lr_max": round(max(lr), 5) if lr else None, "lr_pairs": len(lr),
    }
    bands = {}
    for i in core + list(lid_band):
        b = round(math.floor(co[i].z * 2.0) / 2.0, 1)
        rec = bands.setdefault(b, [0, 0.0, 0.0, 0])
        rec[0] += 1
        rec[1] += d[i].length
        rec[2] = max(rec[2], d[i].length)
        rec[3] += 1 if d[i].length > 0.05 else 0
    report["poses"][label]["zband"] = {str(k): [v[0], round(v[1] / v[0], 4), round(v[2], 4), v[3]]
                                       for k, v in sorted(bands.items())}
    print("M_POSE", label, json.dumps(report["poses"][label]), flush=True)
    print("M_ZBAND", label, json.dumps(report["poses"][label]["zband"]), flush=True)
    if label == "blink":
        worst = sorted(core, key=lambda i: -d[i].length)[:8]
        print("M_CORE_WORST", [(i, [round(c, 3) for c in co[i]], round(d[i].length, 4),
                                max(wts[i].get(n, 0.0) for n in per_bone)) for i in worst], flush=True)

# 九点：唇缝两侧相邻顶点
def pick(xs, upper):
    lip = None
    corner = None
    for i in face_verts:
        c = co[i]
        if abs(c.x - xs) > 0.15 or abs(c.y - mouth.y) > 1.2 or abs(c.z - mouth.z) > 0.80:
            continue
        if upper:
            if wts[i].get("JX_LipUp", 0.0) > 0.05 and (lip is None or c.z < co[lip].z):
                lip = i
            if (c.z > mouth.z and max(wts[i].get("JX_MouthCorner_L", 0.0),
                                      wts[i].get("JX_MouthCorner_R", 0.0)) > 0.05
                    and (corner is None or c.z < co[corner].z)):
                corner = i
        else:
            if wts[i].get("JX_Jaw", 0.0) > 0.01 and (lip is None or c.z > co[lip].z):
                lip = i
    return lip if lip is not None else corner


up_v = [pick(xs, True) for xs in XS]
lo_v = [pick(xs, False) for xs in XS]
print("M_SEAM_UP", [(xs, v, [round(k, 3) for k in co[v]] if v is not None else None) for xs, v in zip(XS, up_v)], flush=True)
print("M_SEAM_LO", [(xs, v, [round(k, 3) for k in co[v]] if v is not None else None) for xs, v in zip(XS, lo_v)], flush=True)
rest_gap = [co[up_v[i]].z - co[lo_v[i]].z for i in range(9)]
print("M_REST_GAP", " ".join("%.4f" % v for v in rest_gap), flush=True)
for lvl in LEVELS:
    pos = deform({"jaw": lvl})
    gap = [pos[up_v[i]].z - pos[lo_v[i]].z for i in range(9)]
    net = [gap[i] - rest_gap[i] for i in range(9)]
    dx = [pos[up_v[i]].x - co[up_v[i]].x for i in range(9)]
    dxl = [pos[lo_v[i]].x - co[lo_v[i]].x for i in range(9)]
    report["mouth9"]["%.2f" % lvl] = {"gap": [round(v, 4) for v in gap], "net": [round(v, 4) for v in net],
                                      "corner_dx_up": round(dx[0], 4), "corner_dx_up_r": round(dx[-1], 4),
                                      "corner_dx_lo": round(dxl[0], 4), "corner_dx_lo_r": round(dxl[-1], 4),
                                      "center_net": round(net[4], 4)}
    print("M_N9 lvl=%.2f gap=%s net=%s dxU=%s dxL=%s" % (
        lvl, " ".join("%.4f" % v for v in gap), " ".join("%.4f" % v for v in net),
        " ".join("%.4f" % v for v in dx), " ".join("%.4f" % v for v in dxl)), flush=True)

# 脸颊轮廓：按 0.5 厘米横向分箱，取最靠前（y 最小）的面材质顶点，静置与眨眼对照
prof = []
for xs in [2.0, 2.5, 3.0, 3.5, 4.0, 4.5]:
    for sgn in (-1.0, 1.0):
        col = [i for i in face_verts
               if abs(abs(co[i].x - sgn * xs) <= 0.25) and 126.0 <= co[i].z <= 132.0 and co[i].y < -0.8]
        if not col:
            continue
        front = min(col, key=lambda i: co[i].y)
        prof.append({"x": sgn * xs, "v": front, "y": round(co[front].y, 4), "z": round(co[front].z, 4)})
pos = deform({"blink_L": 1.0, "blink_R": 1.0})
for row in prof:
    i = row["v"]
    row["dy_blink"] = round(pos[i].y - co[i].y, 4)
    row["dz_blink"] = round(pos[i].z - co[i].z, 4)
print("M_PROFILE", json.dumps(prof), flush=True)
report["profile"] = prof

with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(report, fh)
print("M_OUT", OUT, os.path.getsize(OUT), flush=True)
