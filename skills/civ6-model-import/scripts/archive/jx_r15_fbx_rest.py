import json
import math
import os

import bpy

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
FBX = os.path.join(ROOT, "workspace", "gen", "jinhsi_fbx", "JX_IDLE.fbx")
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r15_fbx_bones.json")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=FBX)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
print("FBX_ARMATURE", arm.name, len(arm.data.bones),
      [(a.name, tuple(round(x) for x in a.frame_range)) for a in bpy.data.actions], flush=True)
print("FBX_SCALE", [round(v, 6) for v in arm.matrix_world.to_scale()], flush=True)

rest = {b.name: arm.matrix_world @ b.matrix_local for b in arm.data.bones}
names = [b.name for b in arm.data.bones]
report = {"bones": {}, "frames": {}}
for frame in (1, 2, 3, 30, 88, 90, 92, 200):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    rows = {}
    for name in names:
        if not name.startswith("JX_") and name != "Bip001Head":
            continue
        m = arm.matrix_world @ arm.pose.bones[name].matrix
        r = rest[name]
        d = m.translation - r.translation
        rows[name] = {"len": round(d.length, 5), "vec": [round(c, 5) for c in d],
                      "deg": round(math.degrees(m.to_quaternion().rotation_difference(r.to_quaternion()).angle), 3)}
    report["frames"][str(frame)] = rows
    print("FBX_F", frame, json.dumps(rows), flush=True)

with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(report, fh)
print("FBX_OUT", OUT, os.path.getsize(OUT), flush=True)
