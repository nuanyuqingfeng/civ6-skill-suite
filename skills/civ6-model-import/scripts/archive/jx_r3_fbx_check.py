import bpy
import math
from mathutils import Vector

FBX = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/jinhsi_fbx/%s.fbx"
WATCH = ["JX_Jaw", "JX_LidUp_L", "JX_Eye_L", "JX_Weapon", "WeaponProp01"]

for name in ("JX_IDLE", "JX_DeclareWarHuman", "JX_FirstMeet"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=FBX % name)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    act = arm.animation_data.action if arm.animation_data else None
    print("ACTION", name, act.name if act else None, "frames", act.frame_range[:] if act else None)
    scene = bpy.context.scene
    total = int(act.frame_range[1]) if act else 1
    samples = [1, int(total * 0.25) or 1, int(total * 0.5) or 1, int(total * 0.75) or 1, total]
    for f in samples:
        scene.frame_set(f)
        row = ["f%d" % f]
        for bn in WATCH:
            pb = arm.pose.bones.get(bn)
            if pb is None:
                row.append("%s=NA" % bn)
                continue
            q = pb.rotation_quaternion
            ang = math.degrees(2.0 * math.acos(max(-1.0, min(1.0, abs(q.w)))))
            head = (arm.matrix_world @ pb.matrix).translation
            row.append("%s ang=%.2f head=(%.1f,%.1f,%.1f)" % (bn, ang, head.x, head.y, head.z))
        print(" | ".join(row))
print("FBXCHECK_DONE")
