import bpy
import math

FBX = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/jinhsi_fbx/JX_IDLE.fbx"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
act = arm.animation_data.action
scene = bpy.context.scene
rows = []
for f in range(120, 152):
    scene.frame_set(f)
    pb = arm.pose.bones["JX_LidUp_L"]
    rows.append((f, tuple(round(v, 2) for v in pb.location), round(pb.matrix.translation.z, 2)))
for r in rows:
    print("F%d loc=%s z=%.2f" % r)
print("BLINKCHECK_DONE")
