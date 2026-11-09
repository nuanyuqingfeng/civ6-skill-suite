import json
import math
import os

import addon_utils
import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
GEN = os.path.join(ROOT, "workspace", "gen")
CN6 = os.path.join(GEN, "jinhsi_fbx", "LEAD_Jinhsi_QYQXP.cn6")
IDLE_FBX = os.path.join(GEN, "jinhsi_fbx", "JX_IDLE.fbx")
PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
REPORT = os.path.join(GEN, "reports")
SCALE = 0.915502
X_LO, X_HI = 1.8, 4.5
Z_LO, Z_HI = 124.0, 134.0
Y_FRONT = -0.5
FACE_KEY = "Face"
# 成品 cn6 的网格与骨架整体绕 Z 轴转了 +90 度（面部朝向由 -y 转到 -x），
# 颊部区间按模型自身坐标系（面部朝 -y）给出，故先把它转回模型坐标系
R = Matrix.Rotation(math.radians(90.0), 4, 'Z')
RINV = R.inverted()


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.armatures,
                  bpy.data.actions, bpy.data.materials):
        for item in list(block):
            block.remove(item, do_unlink=True)


def face_slot(obj):
    for i, s in enumerate(obj.material_slots):
        name = s.material.name if s.material else ""
        if FACE_KEY in name:
            return i
    return -1


def in_region(c):
    return X_LO <= abs(c.x) <= X_HI and Z_LO <= c.z <= Z_HI


def cheek_vertices(obj, co):
    slot = face_slot(obj)
    verts = set()
    for p in obj.data.polygons:
        if p.material_index != slot:
            continue
        for vi in p.vertices:
            if in_region(co[vi]):
                verts.add(vi)
    return verts


def tri_faces(obj, co, xf=None):
    me = obj.data
    me.calc_loop_triangles()
    slot = face_slot(obj)
    rot = Matrix.Identity(3) if xf is None else xf.to_3x3()
    out = []
    for t in me.loop_triangles:
        if t.material_index != slot:
            continue
        ctr = (sum((co[v] for v in t.vertices), Vector()) / 3.0)
        if xf is not None:
            ctr = xf @ ctr
        if not in_region(ctr):
            continue
        shade = Vector()
        for li in t.loops:
            shade += Vector(me.corner_normals[li].vector)
        shade.normalize()
        out.append({"ctr": ctr, "geo": rot @ Vector(t.normal), "shade": rot @ shade, "area": t.area})
    return out


# ---------- 阶段一：成品 cn6 网格与骨架，待机第 1 帧 ----------
clear_scene()
addon_utils.enable("io_import_cn6", default_set=True)
bpy.ops.import_shape.cn6(filepath=CN6)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
body = max(meshes, key=lambda o: len(o.data.vertices))
bone_names = {b.name for b in arm.data.bones}
print("R16_CN6", os.path.getsize(CN6), "arm", arm.name, len(arm.data.bones),
      "mesh", body.name, len(body.data.vertices), "face_slot", face_slot(body), flush=True)
head_cn6 = arm.data.bones["Bip001Head"].matrix_local.translation.copy()
print("R16_FRAME", "head_cn6", [round(v, 4) for v in head_cn6],
      "head_model", [round(v, 4) for v in (RINV @ head_cn6)], flush=True)

bpy.ops.import_scene.fbx(filepath=IDLE_FBX)
src = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o is not arm][0]
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
print("R16_IDLE_RIG", src.name, len(src.pose.bones),
      "action", src.animation_data.action.name if src.animation_data and src.animation_data.action else None,
      "frame", bpy.context.scene.frame_current, flush=True)

deltas = {}
src_rest = {b.name: b.matrix_local.copy() for b in src.data.bones}
for pb in src.pose.bones:
    deltas[pb.name] = R @ (pb.matrix @ src_rest[pb.name].inverted()) @ RINV
shift = {n: (d.to_translation().length, math.degrees(d.to_quaternion().angle)) for n, d in deltas.items()}
worst = max(shift, key=lambda n: shift[n][0])
print("R16_IDLE_DELTA", "max_trans_cm", round(shift[worst][0], 6), worst,
      "head_trans_cm", round(shift["Bip001Head"][0], 6),
      "max_rot_deg", round(max(v[1] for v in shift.values()), 4), flush=True)

by_name = {b.name: b for b in arm.data.bones}
miss = [n for n in by_name if n not in deltas]
print("R16_IDLE_BONES", "matched", len(by_name) - len(miss), "missing", len(miss), miss[:8], flush=True)


def depth(name):
    d = 0
    b = by_name[name]
    while b.parent is not None:
        b = b.parent
        d += 1
    return d


for name in sorted(by_name, key=depth):
    bone = by_name[name]
    rest = bone.matrix_local.copy()
    parent = bone.parent.name if bone.parent else None
    dp = deltas[parent] if parent is not None else Matrix.Identity(4)
    arm.pose.bones[name].matrix_basis = rest.inverted() @ (dp.inverted() @ deltas[name]) @ rest
bpy.context.view_layer.update()

rest_cn6 = [v.co.copy() for v in body.data.vertices]
rest_co = [RINV @ c for c in rest_cn6]
dg = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(dg)
me = ev.to_mesh()
skin_co = [RINV @ (body.matrix_world.inverted() @ (ev.matrix_world @ v.co)) for v in me.vertices]
ev.to_mesh_clear()

gname = {g.index: g.name for g in body.vertex_groups}
cheek = sorted(cheek_vertices(body, rest_co))
rows = []
for vi in cheek:
    d = skin_co[vi] - rest_co[vi]
    ws = sorted(((gname[g.group], g.weight) for g in body.data.vertices[vi].groups
                 if g.weight > 0.0 and gname[g.group] in bone_names), key=lambda x: -x[1])
    rows.append({"v": vi, "rest": list(rest_co[vi]), "skin": list(skin_co[vi]), "d": list(d),
                 "len": d.length, "w": ws[:3], "front": rest_co[vi].y < Y_FRONT})
peak = max(rows, key=lambda r: r["len"])
front = [r for r in rows if r["front"]]
fpeak = max(front, key=lambda r: r["len"])
print("R16_CHEEK", len(rows), "front", len(front),
      "max_len", round(peak["len"], 6), "vert", peak["v"], "max_vec", [round(c, 6) for c in peak["d"]],
      "front_max", round(fpeak["len"], 6), "front_vec", [round(c, 6) for c in fpeak["d"]],
      "over_0.05", sum(1 for r in rows if r["len"] > 0.05),
      "mean_len", round(sum(r["len"] for r in rows) / len(rows), 6), flush=True)
dom = {}
for r in rows:
    for n, w in r["w"]:
        rec = dom.setdefault(n, [0, 0.0, 0.0])
        rec[0] += 1
        rec[1] += w
        rec[2] = max(rec[2], w)
main = sorted(dom.items(), key=lambda kv: -kv[1][0])[0]
print("R16_TOP3", json.dumps({k: [v[0], round(v[1], 4), round(v[2], 4)] for k, v in sorted(
    dom.items(), key=lambda kv: -kv[1][0])}), flush=True)
print("R16_DOM", main[0], "verts", main[1][0], "max_w", round(main[1][2], 6), flush=True)
dirs = [r["d"] for r in rows if r["front"]]
print("R16_DIR", "mean_dy_front", round(sum(d[1] for d in dirs) / len(dirs), 6),
      "neg_y_front", sum(1 for d in dirs if d[1] < 0.0),
      "peak_dir", "in" if fpeak["d"][1] < 0.0 else "out", flush=True)

# ---------- 阶段二：成品法线与原始 PSK 对照 ----------
cn6_faces = tri_faces(body, rest_cn6, xf=RINV)


def stats(faces, label):
    res = {}
    for side, sgn in (("L", -1.0), ("R", 1.0)):
        sub = [f for f in faces if f["ctr"].x * sgn > 0.0]
        res[side] = {
            "faces": len(sub),
            "area": sum(f["area"] for f in sub),
            "winding_flip": sum(1 for f in sub if f["geo"].dot(f["shade"]) < 0.0),
            "shade_back": sum(1 for f in sub if f["shade"].y > 0.3),
            "shade_inward": sum(1 for f in sub if sgn * f["shade"].x < -0.3),
            "geo_back": sum(1 for f in sub if f["geo"].y > 0.3),
        }
    print("R16_N_" + label, json.dumps({k: {kk: (round(vv, 4) if isinstance(vv, float) else vv)
                                            for kk, vv in v.items()} for k, v in res.items()}), flush=True)
    return res


front_faces = [f for f in cn6_faces if f["ctr"].y < Y_FRONT]
cn6_stats = stats(front_faces, "CN6")

clear_scene()
bpy.ops.import_scene.psk(filepath=PSK)
psk_meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in psk_meshes:
    for v in o.data.vertices:
        v.co = v.co * SCALE
    o.data.update()
psk_co = {o.name: [v.co.copy() for v in o.data.vertices] for o in psk_meshes}
psk_faces = []
for o in psk_meshes:
    psk_faces += tri_faces(o, psk_co[o.name])
psk_front = [f for f in psk_faces if f["ctr"].y < Y_FRONT]
psk_stats = stats(psk_front, "PSK")

kd = KDTree(len(psk_front))
for i, f in enumerate(psk_front):
    kd.insert(f["ctr"], i)
kd.balance()
pairs = []
for f in front_faces:
    loc, idx, dist = kd.find(f["ctr"])
    if dist <= 0.02:
        pairs.append((f, psk_front[idx], dist))
geo_ang = sorted(math.degrees(math.acos(max(-1.0, min(1.0, f["geo"].dot(g["geo"])))))
                 for f, g, _d in pairs)
shade_ang = sorted(math.degrees(math.acos(max(-1.0, min(1.0, f["shade"].dot(g["shade"])))))
                   for f, g, _d in pairs)
print("R16_N_PAIR", len(pairs), "of", len(front_faces), "geo_rev_gt90",
      sum(1 for a in geo_ang if a > 90.0), "geo_gt30", sum(1 for a in geo_ang if a > 30.0),
      "geo_max", round(geo_ang[-1], 3), "shade_rev_gt90", sum(1 for a in shade_ang if a > 90.0),
      "shade_gt45", sum(1 for a in shade_ang if a > 45.0), "shade_max", round(shade_ang[-1], 3),
      flush=True)

all_psk = [c for o in psk_meshes for c in psk_co[o.name]]
kdv = KDTree(len(all_psk))
for i, c in enumerate(all_psk):
    kdv.insert(c, i)
kdv.balance()
dist_v = sorted(kdv.find(rest_co[vi])[2] for vi in cheek)
print("R16_GEOM_MATCH", "cheek_verts", len(cheek), "max_nn_dist_cm", round(dist_v[-1], 6),
      "p99", round(dist_v[int(0.99 * len(dist_v))], 6), "mean", round(sum(dist_v) / len(dist_v), 6),
      flush=True)

flips = [f for f in front_faces if f["geo"].dot(f["shade"]) < 0.0]
if flips:
    cells = {}
    for f in flips:
        key = (round(f["ctr"].x, 0), round(f["ctr"].z, 0))
        rec = cells.setdefault(key, [0, 0.0])
        rec[0] += 1
        rec[1] += f["area"]
    print("R16_N_FLIP_CELLS", [((int(k[0]), int(k[1])), v[0], round(v[1], 3))
                               for k, v in sorted(cells.items(), key=lambda kv: -kv[1][1])[:10]],
          flush=True)
    print("R16_N_FLIP_AREA", round(sum(f["area"] for f in flips), 4),
          "of", round(sum(f["area"] for f in front_faces), 4), flush=True)

report = {
    "cn6": CN6, "cn6_bytes": os.path.getsize(CN6), "idle_fbx": IDLE_FBX,
    "region": {"x": [X_LO, X_HI], "z": [Z_LO, Z_HI], "y_front": Y_FRONT},
    "idle_delta": {"max_trans_cm": shift[worst][0], "bone": worst,
                   "head_trans_cm": shift["Bip001Head"][0],
                   "max_rot_deg": max(v[1] for v in shift.values())},
    "cheek": {"count": len(rows), "front": len(front), "max_len": peak["len"],
              "max_vert": peak["v"], "max_vec": peak["d"],
              "front_max": fpeak["len"], "front_vec": fpeak["d"],
              "over_0.05": sum(1 for r in rows if r["len"] > 0.05),
              "mean_len": sum(r["len"] for r in rows) / len(rows),
              "bones": {k: [v[0], v[1], v[2]] for k, v in dom.items()},
              "dominant": [main[0], main[1][0], main[1][2]]},
    "normals": {"cn6": cn6_stats, "psk": psk_stats,
                "pairs": len(pairs),
                "geo_rev_gt90": sum(1 for a in geo_ang if a > 90.0),
                "geo_gt30": sum(1 for a in geo_ang if a > 30.0),
                "geo_max": geo_ang[-1],
                "shade_rev_gt90": sum(1 for a in shade_ang if a > 90.0),
                "shade_gt45": sum(1 for a in shade_ang if a > 45.0),
                "shade_max": shade_ang[-1],
                "geom_nn_max": dist_v[-1], "geom_nn_p99": dist_v[int(0.99 * len(dist_v))]},
    "vertices": rows,
}
with open(os.path.join(REPORT, "r16_cheek.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(report, fh)

rows.sort(key=lambda r: -r["len"])
with open(os.path.join(REPORT, "cheek_vertices.tsv"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("vertex	rest_x	rest_y	rest_z\tskin_x\tskin_y\tskin_z	dx	dy	dz	len"
             "\tbone1	w1	bone2	w2	bone3	w3\n")
    for r in rows[:40]:
        w = r["w"] + [("", 0.0)] * (3 - len(r["w"]))
        fh.write("\t".join([
            str(r["v"]),
            "%.4f" % r["rest"][0], "%.4f" % r["rest"][1], "%.4f" % r["rest"][2],
            "%.4f" % r["skin"][0], "%.4f" % r["skin"][1], "%.4f" % r["skin"][2],
            "%.5f" % r["d"][0], "%.5f" % r["d"][1], "%.5f" % r["d"][2], "%.5f" % r["len"],
            w[0][0], "%.4f" % w[0][1], w[1][0], "%.4f" % w[1][1], w[2][0], "%.4f" % w[2][1],
        ]) + "\n")
print("R16_TSV", os.path.join(REPORT, "cheek_vertices.tsv"), min(40, len(rows)), flush=True)
print("R16_DONE", flush=True)
