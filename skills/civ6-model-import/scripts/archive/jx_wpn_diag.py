import bpy

from mathutils import Vector

BLEND = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx\weapon_rigged.blend"
bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
weapon = bpy.data.objects["JinhsiWeapon"]
body = [o for o in bpy.data.objects if o.type == 'MESH' and o is not weapon][0]
print("BODY_OBJ", body.name, "matrix_world", [round(c, 4) for row in body.matrix_world for c in row])
print("BODY_REST_BOX", [round(min(v.co[i] for v in body.data.vertices), 3) for i in range(3)],
      [round(max(v.co[i] for v in body.data.vertices), 3) for i in range(3)])
print("MODS", [(m.type, m.object.name if m.object else None) for m in body.modifiers])


def bbox_pose(tag):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    zs = [(ev.matrix_world @ v.co).z for v in me.vertices]
    ys = [(ev.matrix_world @ v.co).y for v in me.vertices]
    ev.to_mesh_clear()
    print("BBOX", tag, "z", [round(min(zs), 2), round(max(zs), 2)], "y", [round(min(ys), 2), round(max(ys), 2)])


arm.data.pose_position = 'REST'
bpy.context.view_layer.update()
bbox_pose("REST")
arm.data.pose_position = 'POSE'
arm.animation_data.action = None
bpy.context.view_layer.update()
bbox_pose("POSE_NULL")
for clip in ("Ui_Weapon_Loop",):
    arm.animation_data.action = bpy.data.actions[clip]
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    bbox_pose(clip)
    for bn in ("Root", "Bip001", "Bip001Pelvis", "Bip001Spine2", "Bip001LHand"):
        pb = arm.pose.bones[bn]
        print("PBM", bn, "loc", [round(c, 4) for c in pb.location], "scale", [round(c, 4) for c in pb.scale],
              "world_t", [round(c, 3) for c in pb.matrix.translation],
              "world_scale", [round(c, 4) for c in pb.matrix.to_scale()])
print("DIAG_DONE")
