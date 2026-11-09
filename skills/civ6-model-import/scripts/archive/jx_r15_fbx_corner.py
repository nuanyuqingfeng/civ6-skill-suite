import json
import math
import os

import bpy

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
FBX = os.path.join(ROOT, "workspace", "gen", "jinhsi_fbx", "JX_Kudos.fbx")
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r15_fbx_corner.json")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=FBX)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
scale = arm.matrix_world.to_scale()[0]
print("FBX_SCALE", scale, [(a.name, tuple(round(x) for x in a.frame_range)) for a in bpy.data.actions], flush=True)
rest = {b.name: arm.matrix_world @ b.matrix_local for b in arm.data.bones}
rows = {}
for frame in (1, 124, 125, 126, 268):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    rec = {}
    for name in ("JX_Jaw", "JX_MouthCorner_L", "JX_MouthCorner_R", "JX_LipUp", "JX_LipLo",
                 "JX_LidUp_L", "JX_LidUp_R"):
        m = arm.matrix_world @ arm.pose.bones[name].matrix
        r = rest[name]
        d = m.translation - r.translation
        rec[name] = {"trans_cm": [round(c / scale, 5) for c in d],
                     "len_cm": round(d.length / scale, 5),
                     "rot_deg": round(math.degrees(m.to_quaternion().rotation_difference(r.to_quaternion()).angle), 4)}
    rows[str(frame)] = rec
    print("FBX_F", frame, json.dumps(rec), flush=True)
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(rows, fh)
print("FBX_OUT", OUT, flush=True)
