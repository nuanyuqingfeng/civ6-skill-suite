import bpy
import math

FBX = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/jinhsi_fbx/%s.fbx"

def ang(pb):
    q = pb.rotation_quaternion
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, abs(q.w)))))

for name in ("JX_IDLE", "JX_FirstMeet", "JX_DeclareWarHuman"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=FBX % name)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    act = arm.animation_data.action
    scene = bpy.context.scene
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    best_jaw = (0.0, f0)
    best_lid = (1e9, f0)
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        jb = arm.pose.bones.get("JX_Jaw")
        lb = arm.pose.bones.get("JX_LidUp_L")
        eb = arm.pose.bones.get("JX_Eye_L")
        if jb is not None:
            a = ang(jb)
            if a > best_jaw[0]:
                best_jaw = (a, f)
        if lb is not None and eb is not None:
            dz = (arm.matrix_world @ lb.matrix).translation.z - (arm.matrix_world @ eb.matrix).translation.z
            if dz < best_lid[0]:
                best_lid = (dz, f)
    print("%s jaw_max_frame=%d (%.2f deg) lid_min_frame=%d (dz=%.3f cm)" % (
        name, best_jaw[1], best_jaw[0], best_lid[1], (best_lid[0]) * 100))
print("FRAMEPICK_DONE")
