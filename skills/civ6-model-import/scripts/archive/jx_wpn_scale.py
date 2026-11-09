import bpy
import math

from mathutils import Vector

BLEND = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx\weapon_rigged.blend"
CLIPS = ["Ui_Weapon_Start", "Ui_Weapon_Loop", "Ui_Weapon_End"]
bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
weapon = bpy.data.objects["JinhsiWeapon"]
body = [o for o in bpy.data.objects if o.type == 'MESH' and o is not weapon][0]
if arm.animation_data is None:
    arm.animation_data_create()

for clip in CLIPS:
    act = bpy.data.actions[clip]
    arm.animation_data.action = act
    f0 = int(act.frame_range[0])
    f1 = int(act.frame_range[1])
    for f in (f0, (f0 + f1) // 2, f1):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        me = ev.to_mesh()
        zs = [(ev.matrix_world @ v.co).z for v in me.vertices]
        ev.to_mesh_clear()
        pb = arm.pose.bones["WeaponProp01"]
        root = arm.pose.bones["Root"]
        sc = pb.matrix.to_scale()
        rs = root.matrix.to_scale()
        print("SCALE", clip, "f", f,
              "prop_scale", [round(c, 5) for c in sc],
              "root_scale", [round(c, 5) for c in rs],
              "body_z", [round(min(zs), 2), round(max(zs), 2)],
              "prop_loc", [round(c, 2) for c in pb.matrix.translation])
        print("   CHAN", "prop_loc", [round(c, 4) for c in pb.location],
              "prop_scale", [round(c, 4) for c in pb.scale],
              "root_loc", [round(c, 4) for c in root.location],
              "root_scale", [round(c, 4) for c in root.scale])
print("SCALE_PROBE_DONE")
