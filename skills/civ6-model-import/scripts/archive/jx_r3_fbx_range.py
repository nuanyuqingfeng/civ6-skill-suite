import bpy
import math

FBX = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/jinhsi_fbx/%s.fbx"
NAMES = ["JX_IDLE", "JX_FirstMeet", "JX_DeclareWarHuman", "JX_DeclareWarAI", "JX_Kudos", "JX_Warning", "JX_Defeat"]

def ang(pb):
    q = pb.rotation_quaternion
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, abs(q.w)))))

for name in NAMES:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=FBX % name)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    act = arm.animation_data.action
    scene = bpy.context.scene
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    best = {"JX_Jaw": 0.0, "JX_LidUp_L": 0.0, "JX_Eye_L": 0.0, "JX_Brow_L": 0.0}
    jaw_frames = 0
    weapon_far = 0.0
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        for bn in best:
            pb = arm.pose.bones.get(bn)
            if pb is None:
                continue
            a = ang(pb)
            if a > best[bn]:
                best[bn] = a
        jb = arm.pose.bones.get("JX_Jaw")
        if jb is not None and ang(jb) > 0.3:
            jaw_frames += 1
        wb = arm.pose.bones.get("JX_Weapon")
        hb = arm.pose.bones.get("WeaponProp01")
        if wb is not None and hb is not None:
            d = ((arm.matrix_world @ wb.matrix).translation - (arm.matrix_world @ hb.matrix).translation).length
            weapon_far = max(weapon_far, d)
    print("%s frames=%d..%d jaw_max=%.2f jaw_frames=%d lid_max=%.2f eye_max=%.2f brow_max=%.2f weapon_far=%.1f" % (
        name, f0, f1, best["JX_Jaw"], jaw_frames, best["JX_LidUp_L"], best["JX_Eye_L"], best["JX_Brow_L"], weapon_far))
print("RANGECHECK_DONE")
