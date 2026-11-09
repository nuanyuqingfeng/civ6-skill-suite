import bpy
import os
import math

from mathutils import Matrix

OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx"
MODEL_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
PSK = os.path.join(MODEL_DIR, "R2T1JinxiMd10011.psk")
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"

ROT_Y_DEG = -90.0
SCALE = 120.76 / 132.76
FPS = 30
T = Matrix.Rotation(math.radians(ROT_Y_DEG), 4, 'Y') @ Matrix.Scale(SCALE, 4)

os.makedirs(OUT_DIR, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
    for item in list(block):
        block.remove(item, do_unlink=True)

bpy.ops.import_scene.psk(filepath=PSK)
arm_a = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = None
for o in bpy.data.objects:
    if o.type == 'MESH' and len(o.data.vertices) > 100:
        body = o
body.name = "JinhsiBody"
if body.data.shape_keys:
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.shape_key_remove(all=True)

arm_a_name = arm_a.name
bpy.ops.object.select_all(action='DESELECT')
arm_a.select_set(True)
bpy.context.view_layer.objects.active = arm_a
bpy.ops.object.duplicate(linked=False)
arm_b = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o != arm_a][0]
arm_b.name = arm_a_name
arm_a.name = arm_a_name + "_src"
print("DUAL_ARMATURES", arm_a.name, arm_b.name)

for mod in body.modifiers:
    if mod.type == 'ARMATURE':
        mod.object = arm_b
has_arm = any(m.type == 'ARMATURE' and m.object == arm_b for m in body.modifiers)
if not has_arm:
    m = body.modifiers.new(name='Armature', type='ARMATURE')
    m.object = arm_b

bpy.context.view_layer.objects.active = arm_b
bpy.ops.object.mode_set(mode='EDIT')
for eb in arm_b.data.edit_bones:
    eb.matrix = T @ eb.matrix
bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
bpy.context.view_layer.objects.active = body
body.matrix_world = T @ body.matrix_world
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

head = arm_b.data.bones.get('Bip001Head')
print("B_HEAD=", [round(c, 2) for c in arm_b.matrix_world @ head.head_local])
print("A_HEAD=", [round(c, 2) for c in arm_a.matrix_world @ arm_a.data.bones['Bip001Head'].head_local])

CLIP_FILES = ["Ui_Nature_Loop", "Ui_Nature_Start", "Ui_Weapon_Start", "Ui_Weapon_Loop",
              "Ui_Resonant_Start", "Ui_Resonant_Loop", "Team_Stand2", "Ui_Chip_End", "Cos_Pose"]
for clip in CLIP_FILES:
    bpy.ops.object.select_all(action='DESELECT')
    arm_a.select_set(True)
    bpy.context.view_layer.objects.active = arm_a
    bpy.ops.uf.import_ueanim(directory=ANIM_DIR, files=[{'name': clip + '.ueanim'}])


def get_action(name):
    for a in bpy.data.actions:
        if a.name == name and not a.name.endswith("_Curves"):
            return a
    return None


FALLBACK = {
    "Ui_Weapon_Start": "Ui_Nature_Start", "Ui_Weapon_Loop": "Ui_Nature_Loop",
    "Ui_Resonant_Start": "Ui_Weapon_Start", "Ui_Resonant_Loop": "Ui_Weapon_Loop",
    "Team_Stand2": "Ui_Nature_Loop", "Ui_Chip_End": "Cos_Pose", "Cos_Pose": "Ui_Nature_Loop",
}


def resolve(name):
    seen = set()
    while get_action(name) is None and name in FALLBACK and name not in seen:
        seen.add(name)
        name = FALLBACK[name]
    return get_action(name)


TARGETS = [
    ("JX_IDLE", 240, [("Ui_Nature_Loop", 1)]),
    ("JX_FirstMeet", 210, [("Ui_Nature_Start", 1), ("Ui_Nature_Loop", 2)]),
    ("JX_DeclareWarHuman", 180, [("Ui_Weapon_Start", 1), ("Ui_Weapon_Loop", 2)]),
    ("JX_DeclareWarAI", 330, [("Ui_Weapon_Start", 1), ("Ui_Weapon_Loop", 4)]),
    ("JX_Kudos", 240, [("Ui_Resonant_Start", 1), ("Ui_Resonant_Loop", 2)]),
    ("JX_Warning", 150, [("Team_Stand2", 1)]),
    ("JX_Defeat", 90, [("Cos_Pose", 1), ("Ui_Chip_End", 1)]),
]


def clear_anim(arm):
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = None
    for t in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(t)


def compose_on_a(name, total, segments):
    clear_anim(arm_a)
    track = arm_a.animation_data.nla_tracks.new()
    cur = 1.0
    for src, repeat in segments:
        act = resolve(src)
        assert act is not None
        strip = track.strips.new(act.name, int(cur), act)
        if repeat > 1:
            strip.repeat = repeat
        cur += (act.frame_range[1] - act.frame_range[0]) * repeat
    bpy.context.view_layer.objects.active = arm_a
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(frame_start=1, frame_end=total, step=1, only_selected=True,
                     visual_keying=True, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    baked = arm_a.animation_data.action
    baked.name = "SRC_" + name
    return baked


def retarget(name, src_action, total):
    clear_anim(arm_b)
    act = bpy.data.actions.new(name)
    arm_b.animation_data.action = act
    clear_anim(arm_a)
    arm_a.animation_data.action = src_action
    pose_map = {}
    for pb in arm_a.pose.bones:
        pose_map[pb.name] = arm_b.pose.bones[pb.name]
    for f in range(1, total + 1):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        for pb_name, pb_b in pose_map.items():
            pb_b.matrix = T @ pose_map[pb_name].matrix
        for pb_name, pb_b in pose_map.items():
            pb_b.keyframe_insert(data_path="location", frame=f)
            pb_b.keyframe_insert(data_path="rotation_quaternion", frame=f)
            pb_b.keyframe_insert(data_path="scale", frame=f)
    print("RETARGET:", name, "frames=", tuple(round(x) for x in act.frame_range))
    return act


bpy.context.scene.render.fps = FPS
bpy.context.scene.render.fps_base = 1.0
FBX_ARGS = dict(
    use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
    bake_anim=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
    axis_forward='-Z', axis_up='Y', apply_unit_scale=True, global_scale=1.0,
    mesh_smooth_type='OFF', use_mesh_modifiers=True,
)

arm_b.data.pose_position = 'REST'
clear_anim(arm_b)
bpy.ops.object.select_all(action='DESELECT')
arm_b.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = body
model_path = os.path.join(OUT_DIR, "LEAD_Jinhsi_QYQXP_Model.fbx")
model_args = dict(FBX_ARGS)
model_args["bake_anim"] = False
bpy.ops.export_scene.fbx(filepath=model_path, **model_args)
print("MODEL_FBX:", model_path)
arm_b.data.pose_position = 'POSE'

for name, total, segments in TARGETS:
    src = compose_on_a(name, total, segments)
    act = retarget(name, src, total)
    clear_anim(arm_b)
    arm_b.animation_data.action = act
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = total
    bpy.ops.object.select_all(action='DESELECT')
    arm_b.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = arm_b
    path = os.path.join(OUT_DIR, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, **FBX_ARGS)
    print("ANIM_FBX:", path)
print("BUILD4_DONE")
