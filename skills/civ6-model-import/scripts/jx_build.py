import bpy
import os
import math

OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx"
MODEL_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
PSK = os.path.join(MODEL_DIR, "R2T1JinxiMd10011.psk")
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"

os.makedirs(OUT_DIR, exist_ok=True)

# 清空默认场景
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
    for item in list(block):
        block.remove(item, do_unlink=True)

# 导入模型
bpy.ops.import_scene.psk(filepath=PSK)
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
assert len(arms) == 1, "期望唯一骨架"
arm = arms[0]
body_mesh = None
for o in bpy.data.objects:
    if o.type == 'MESH' and len(o.data.vertices) > 100:
        body_mesh = o
print("MODEL_IN: bones=%d verts=%d" % (len(arm.data.bones), len(body_mesh.data.vertices)))
print("MODEL_DIMS:", tuple(round(c, 2) for c in body_mesh.dimensions))

# 按材质拆分网格
bpy.ops.object.select_all(action='DESELECT')
body_mesh.select_set(True)
bpy.context.view_layer.objects.active = body_mesh
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.separate(type='MATERIAL')
bpy.ops.object.mode_set(mode='OBJECT')

meshes = [o for o in bpy.data.objects if o.type == 'MESH']
mesh_report = []
for o in meshes:
    slot = o.material_slots[0].name if o.material_slots else "NONE"
    short = slot.replace("MI_R2T1JinxiMd10011", "").replace("MI_", "")
    o.name = short if short else slot
    mesh_report.append((o.name, len(o.data.vertices), slot))
    if o.data.shape_keys:
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.shape_key_remove(all=True)
print("MESH_SPLIT:", mesh_report)

# 导入动画素材
CLIP_FILES = ["Ui_Nature_Loop", "Ui_Nature_Start", "Ui_Weapon_Start", "Ui_Weapon_Loop",
              "Ui_Resonant_Start", "Ui_Resonant_Loop", "Team_Stand2", "Ui_Chip_End", "Cos_Pose"]

def activate_arm():
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm

for clip in CLIP_FILES:
    activate_arm()
    bpy.ops.uf.import_ueanim(directory=ANIM_DIR, files=[{'name': clip + '.ueanim'}])

def get_action(name):
    for a in bpy.data.actions:
        if a.name == name and not a.name.endswith("_Curves"):
            return a
    return None

for clip in CLIP_FILES:
    act = get_action(clip)
    print("SRC_ACTION:", clip, "range=", tuple(act.frame_range) if act else "MISSING")

# 槽位定义：名字, 总帧数(30fps), [(源动作, 重复次数)]
FPS = 30
bpy.context.scene.render.fps = FPS
bpy.context.scene.frame_start = 1
bpy.context.scene.render.fps_base = 1.0
TARGETS = [
    ("JX_IDLE", 240, [("Ui_Nature_Loop", 1)]),
    ("JX_FirstMeet", 210, [("Ui_Nature_Start", 1), ("Ui_Nature_Loop", 2)]),
    ("JX_DeclareWarHuman", 180, [("Ui_Weapon_Start", 1), ("Ui_Weapon_Loop", 2)]),
    ("JX_DeclareWarAI", 330, [("Ui_Weapon_Start", 1), ("Ui_Weapon_Loop", 4)]),
    ("JX_Kudos", 240, [("Ui_Resonant_Start", 1), ("Ui_Resonant_Loop", 2)]),
    ("JX_Warning", 150, [("Team_Stand2", 1)]),
    ("JX_Defeat", 90, [("Cos_Pose", 1), ("Ui_Chip_End", 1)]),
]

# 缺失源动作的降级替换
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

def clear_anim_data():
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = None
    for t in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(t)

def compose(name, total, segments):
    clear_anim_data()
    track = arm.animation_data.nla_tracks.new()
    track.name = name
    cur = 1.0
    for src, repeat in segments:
        act = resolve(src)
        assert act is not None, "缺少源动作: " + src
        strip = track.strips.new(act.name, int(cur), act)
        if repeat > 1:
            strip.repeat = repeat
        act_len = act.frame_range[1] - act.frame_range[0]
        print("  STRIP:", name, src, "start=", int(cur), "len=", int(act_len * repeat))
        cur += act_len * repeat
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(frame_start=1, frame_end=total, step=1, only_selected=True,
                     visual_keying=True, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    baked = arm.animation_data.action
    baked.name = name
    print("BAKED:", name, "frames=", tuple(round(f) for f in baked.frame_range),
          "keys=", sum(len(fc.keyframe_points) for fc in baked.fcurves))
    return baked

def select_export_set():
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm

FBX_ARGS = dict(
    use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
    bake_anim=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
    axis_forward='-Z', axis_up='Y', apply_unit_scale=True, global_scale=1.0,
    mesh_smooth_type='OFF', use_mesh_modifiers=True,
)

# 模型 FBX（静止姿势，不带动画）
arm.data.pose_position = 'REST'
clear_anim_data()
select_export_set()
model_path = os.path.join(OUT_DIR, "LEAD_Jinhsi_QYQXP_Model.fbx")
model_args = dict(FBX_ARGS)
model_args["bake_anim"] = False
bpy.ops.export_scene.fbx(filepath=model_path, **model_args)
print("EXPORTED:", model_path)

arm.data.pose_position = 'POSE'

# 逐动画 FBX
for name, total, segments in TARGETS:
    baked = compose(name, total, segments)
    clear_anim_data()
    arm.animation_data.action = baked
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = total
    select_export_set()
    path = os.path.join(OUT_DIR, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, **FBX_ARGS)
    print("EXPORTED:", path)

print("BUILD_DONE")
