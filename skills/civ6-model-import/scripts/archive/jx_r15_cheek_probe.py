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
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r15_cheek_probe.json")
X_LO, X_HI = 2.0, 4.5
Z_LO, Z_HI = 126.0, 132.0

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

scaled = [v.co.copy() for v in body.data.vertices]
parts = rig.load_parts()
rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)
rest_co = [v.co.copy() for v in body.data.vertices]

names = [m.name for m in body.data.materials]
face_slot = names.index("MI_R2T1JinxiMd10011Face")
face_verts = set()
for p in body.data.polygons:
    if p.material_index == face_slot:
        face_verts.update(p.vertices)
face_verts = sorted(face_verts)

drift = max((rest_co[i] - scaled[i]).length for i in range(len(scaled)))
print("PROBE_REST_DRIFT", "%.9f" % drift)

cheek = [i for i in face_verts
         if X_LO <= abs(rest_co[i].x) <= X_HI and Z_LO <= rest_co[i].z <= Z_HI]
print("PROBE_CHEEK_VERTS", len(cheek), "of_face", len(face_verts))
left = [i for i in cheek if rest_co[i].x < 0.0]
right = [i for i in cheek if rest_co[i].x > 0.0]
print("PROBE_CHEEK_SIDES", len(left), len(right))

gname = {g.index: g.name for g in body.vertex_groups}
wmap = {}
for i in cheek:
    wmap[i] = sorted(((gname[g.group], g.weight) for g in body.data.vertices[i].groups),
                     key=lambda x: -x[1])
per_bone = {}
for i in cheek:
    for name, w in wmap[i]:
        if not name.startswith("JX_"):
            continue
        rec = per_bone.setdefault(name, [0, 0.0, 0.0])
        rec[0] += 1
        rec[1] += w
        rec[2] = max(rec[2], w)
print("PROBE_CHEEK_BONES", json.dumps({k: [v[0], round(v[1], 4), round(v[2], 4)]
                                       for k, v in sorted(per_bone.items())}))
sums = [sum(w for _n, w in wmap[i]) for i in cheek]
bad = [i for i, s in zip(cheek, sums) if abs(s - 1.0) > 0.02]
print("PROBE_CHEEK_SUM", "bad=%d" % len(bad), "max_dev=%.5f" % max(abs(s - 1.0) for s in sums),
      "sum_range=[%.5f,%.5f]" % (min(sums), max(sums)))

# 顶点自身在当前静置网格上的权重构成（只列 JX_ 骨与头骨）
rows = []
for i in cheek:
    js = {n: round(w, 4) for n, w in wmap[i] if n.startswith("JX_") or n == "Bip001Head"}
    rows.append({"v": i, "x": round(rest_co[i].x, 4), "y": round(rest_co[i].y, 4),
                 "z": round(rest_co[i].z, 4), "sum": round(sum(w for _n, w in wmap[i]), 5),
                 "w": js})

rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
envelope = anim.load_envelope()
pose_sets = {
    "rest": {},
    "blink": {"blink_L": 1.0, "blink_R": 1.0},
    "jaw": {"jaw": 1.0},
    "idle1": anim.facial_params("JX_IDLE", 1, envelope),
    "idle90": anim.facial_params("JX_IDLE", 90, envelope),
}
inv_rest = {k: v.inverted() for k, v in rest.items()}
results = {}
for label, params in pose_sets.items():
    pose_world = {}
    rig.pose_face(pose_world, params, rest)
    mats = {}
    for bone, pw in pose_world.items():
        mats[bone] = pw @ inv_rest[bone]
    disp = {}
    for i in cheek:
        p = rest_co[i]
        q = Vector()
        for name, w in wmap[i]:
            m = mats.get(name)
            q += (m @ p if m is not None else p) * w
        disp[i] = q - p
    peak = max(disp, key=lambda i: disp[i].length)
    results[label] = {
        "max_len": round(disp[peak].length, 5),
        "max_vert": peak,
        "max_vec": [round(c, 5) for c in disp[peak]],
        "min_y": round(min(d.y for d in disp.values()), 5),
        "mean_len": round(sum(d.length for d in disp.values()) / len(disp), 5),
        "over_0.05": sum(1 for d in disp.values() if d.length > 0.05),
    }
    print("PROBE_POSE", label, json.dumps(results[label]))
    results[label]["per_vertex"] = {str(i): [round(c, 5) for c in disp[i]] for i in cheek}
    if label in ("blink", "jaw"):
        worst = sorted(cheek, key=lambda i: -disp[i].length)[:12]
        print("PROBE_WORST", label, [(i, [round(c, 3) for c in rest_co[i]],
                                      round(disp[i].length, 4),
                                      wmap[i][0][0] if wmap[i] else "-") for i in worst])

report = {
    "rest_drift_max": round(drift, 9),
    "cheek_verts": len(cheek),
    "left": len(left),
    "right": len(right),
    "bones": {k: [v[0], round(v[1], 4), round(v[2], 4)] for k, v in sorted(per_bone.items())},
    "weight_sum": {"bad": len(bad), "max_dev": round(max(abs(s - 1.0) for s in sums), 5),
                   "min": round(min(sums), 5), "max": round(max(sums), 5)},
    "vertices": rows,
    "poses": results,
}
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(report, fh)
print("PROBE_OUT", OUT, os.path.getsize(OUT))
print("PROBE_DONE")
