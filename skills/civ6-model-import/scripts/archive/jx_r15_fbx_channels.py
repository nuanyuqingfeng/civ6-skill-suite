import json
import os

import bpy

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
FBX = os.path.join(ROOT, "workspace", "gen", "jinhsi_fbx", "JX_Kudos.fbx")
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r15_fbx_channels.json")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=FBX)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
s = arm.matrix_world.to_scale()[0]
from mathutils import Vector

for name in ("JX_MouthCorner_L", "JX_MouthCorner_R"):
    b = arm.data.bones[name]
    axes = [(b.matrix_local.to_3x3() @ Vector(a)).normalized() for a in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    print("FBX_AXIS", name, [[round(c, 4) for c in v] for v in axes], flush=True)

rows = {}
for frame in (1, 125, 268):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    rec = {}
    for name in ("JX_Jaw", "JX_MouthCorner_L", "JX_MouthCorner_R", "JX_LipUp", "JX_LipLo"):
        pb = arm.pose.bones[name]
        rec[name] = {"loc_cm": [round(c / s, 5) for c in pb.location],
                     "len_cm": round(pb.location.length / s, 5)}
    rows[str(frame)] = rec
    print("FBX_CH", frame, json.dumps(rec), flush=True)
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(rows, fh)
print("FBX_OUT", OUT, flush=True)
