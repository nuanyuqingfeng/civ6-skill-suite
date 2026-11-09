import bpy

FBX = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx\JX_FirstMeet.fbx"

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=FBX)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
print("FBX_ARMATURE", arm.name, "bones", len(arm.data.bones), "actions", len(bpy.data.actions))
print("FBX_JX_BONES", [b.name for b in arm.data.bones if b.name.startswith("JX_")])
for act in bpy.data.actions:
    curves = {}
    for fc in act.fcurves:
        if '"JX_' not in fc.data_path:
            continue
        name = fc.data_path.split('"')[1]
        prop = fc.data_path.split(".")[-1]
        values = [kp.co[1] for kp in fc.keyframe_points]
        curves[(name, prop, fc.array_index)] = (len(values), min(values), max(values))
    print("FBX_ACTION", act.name, "range", tuple(round(v) for v in act.frame_range), "jx_curves", len(curves))
    for key in sorted(curves):
        count, low, high = curves[key]
        print("FBX_CURVE", key[0], key[1], key[2], "keys", count, "min %.6f max %.6f" % (low, high))
print("FBXCH_DONE")
