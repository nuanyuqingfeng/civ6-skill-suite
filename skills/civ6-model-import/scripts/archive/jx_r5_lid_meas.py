import json
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_face as rig

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r5_lid")
SCALE = 0.915502
TAG = os.environ.get("R5_TAG", "after")
os.makedirs(OUT, exist_ok=True)

if os.environ.get("R5_TAPER") == "off":
    rig._lid_taper = lambda dx, ctr_x: 1.0
    rig.LOWER_LID_RATIO = 0.18

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

parts = rig.build_face_rig(arm, body)
BIND = {pb.name: pb.matrix.copy() for pb in arm.pose.bones}
rig.apply_weights(body, parts)
rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
co = [v.co.copy() for v in body.data.vertices]
gidx = {g.name: g.index for g in body.vertex_groups}


def weight_of(vi, name):
    if name not in gidx:
        return 0.0
    for g in body.data.vertices[vi].groups:
        if g.group == gidx[name]:
            return g.weight
    return 0.0


def skinned(pose_world):
    inv = {b.name: b.matrix_local.inverted() for b in arm.data.bones}
    out = []
    for v in body.data.vertices:
        acc = Vector()
        for g in v.groups:
            name = body.vertex_groups[g.group].name
            m = pose_world.get(name)
            acc += g.weight * (v.co if m is None else ((m @ inv[name]) @ v.co))
        out.append(acc)
    return out


def deform(params):
    pose_world = {b.name: b.matrix_local.copy() for b in arm.data.bones if b.name.startswith("JX_")}
    rig.pose_face(pose_world, params, rest)
    for pb in arm.pose.bones:
        if pb.name.startswith("JX_"):
            delta = pose_world[pb.name] @ rest[pb.name].inverted()
            pb.matrix = delta @ BIND[pb.name]
        else:
            pb.matrix = BIND[pb.name]
    bpy.context.view_layer.update()
    return skinned(pose_world)


def bin_profile(coords, ids, ctr, mode, step=0.25, width=1.9, ymax=-0.8):
    bins = {}
    for vi in ids:
        p = coords[vi]
        if abs(p.x - ctr.x) > width or co[vi].y > ymax:
            continue
        k = int(round((p.x - ctr.x) / step))
        bins.setdefault(k, []).append(p.z)
    return {k: (min(zs) if mode == "min" else max(zs)) for k, zs in bins.items()}


def spread(prof):
    vals = [v for k, v in prof.items() if -7 <= k <= 7]
    return round(max(vals) - min(vals), 4), round(max(vals), 4), round(min(vals), 4)


report = {"tag": TAG, "vert": {}, "rim": {}, "pose": {}}
c_rest = deform({})
c_blink = deform({"blink_L": 1.0, "blink_R": 1.0})
for side in ("L", "R"):
    ctr = rig._eye_center(parts, side)
    eb = parts["eyeball"][side]
    rim = parts["rim" + side]
    rim_z = sum(co[vi].z for vi in rim) / len(rim)
    rim_up = [vi for vi in rim if co[vi].z > rim_z]
    rim_lo = [vi for vi in rim if co[vi].z <= rim_z]
    up_bone = "JX_LidUp_" + side
    lo_bone = "JX_LidLo_" + side
    lo_members = [vi for vi in range(len(co)) if weight_of(vi, lo_bone) > 0.0]
    lo_strong = [vi for vi in lo_members if weight_of(vi, lo_bone) > 0.5]
    up_members = [vi for vi in range(len(co)) if weight_of(vi, up_bone) > 0.0]
    report["vert"][side] = {
        "eye_center": [round(v, 3) for v in ctr],
        "eyeball_radius": round(eb["radius_fit"] * SCALE, 3),
        "rim": len(rim), "rim_up": len(rim_up), "rim_lo": len(rim_lo),
        "lidup_members": len(up_members),
        "lidlo_members": len(lo_members), "lidlo_strong": len(lo_strong),
        "lidlo_rim_hits": len([vi for vi in rim_lo if weight_of(vi, lo_bone) > 0.0]),
    }
    for name, coords in (("rest", c_rest), ("blink", c_blink)):
        up_prof = bin_profile(coords, rim_up, ctr, "min")
        lo_prof = bin_profile(coords, rim_lo, ctr, "max")
        lash_prof = bin_profile(coords, parts["lash" + side], ctr, "min")
        report["pose"].setdefault(name, {})[side] = {
            "up_spread": spread(up_prof),
            "lo_spread": spread(lo_prof),
            "lash_spread": spread(lash_prof),
            "up_center": round(up_prof.get(0, 0.0) - ctr.z, 4),
            "lo_center": round(lo_prof.get(0, 0.0) - ctr.z, 4),
            "up_prof": {k: round(v - ctr.z, 3) for k, v in sorted(up_prof.items())},
            "lo_prof": {k: round(v - ctr.z, 3) for k, v in sorted(lo_prof.items())},
        }

with open(os.path.join(OUT, "meas_%s.json" % TAG), "w", encoding="utf-8") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=1)

for side in ("L", "R"):
    v = report["vert"][side]
    print("LID_VERT", side, "rim", v["rim"], "rim_up", v["rim_up"], "rim_lo", v["rim_lo"],
          "lidup_members", v["lidup_members"], "lidlo_members", v["lidlo_members"],
          "lidlo_strong", v["lidlo_strong"], "lidlo_rim_hits", v["lidlo_rim_hits"],
          "eye", v["eye_center"], "radius", v["eyeball_radius"])
    for name in ("rest", "blink"):
        e = report["pose"][name][side]
        print("LID_EDGE", name, side, "up_spread", e["up_spread"], "lo_spread", e["lo_spread"],
              "lash_spread", e["lash_spread"], "up_center", e["up_center"], "lo_center", e["lo_center"])
    print("LID_UP_PROF", side, report["pose"]["blink"][side]["up_prof"])
print("LID_MEAS_DONE", os.path.join(OUT, "meas_%s.json" % TAG))
