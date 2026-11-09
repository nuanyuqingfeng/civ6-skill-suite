import bpy
import math

FBX = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/jinhsi_fbx/%s.fbx"
NAMES = ["JX_IDLE", "JX_FirstMeet", "JX_DeclareWarHuman", "JX_Kudos", "JX_Warning", "JX_Defeat"]

for name in NAMES:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=FBX % name)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    act = arm.animation_data.action
    scene = bpy.context.scene
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    lid = arm.pose.bones.get("JX_LidUp_L")
    brow = arm.pose.bones.get("JX_Brow_L")
    zs = []
    bs = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        if lid is not None:
            zs.append((arm.matrix_world @ lid.matrix).translation.z)
        if brow is not None:
            bs.append((arm.matrix_world @ brow.matrix).translation.z)
    span = (max(zs) - min(zs)) * 100 if zs else -1
    bspan = (max(bs) - min(bs)) * 100 if bs else -1
    print("%s lid_z_span_cm=%.3f brow_z_span_cm=%.3f" % (name, span, bspan))
print("LIDCHECK_DONE")
