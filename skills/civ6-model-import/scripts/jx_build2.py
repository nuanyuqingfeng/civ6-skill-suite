import bpy
import os
import math

from mathutils import Matrix, Vector

OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx"
CN6_SRC = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx\LEAD_Jinhsi_pristine.cn6"
MODEL_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
PSK = os.path.join(MODEL_DIR, "R2T1JinxiMd10011.psk")
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"

ROT_Y_DEG = -90.0
SCALE = 120.76 / 132.76
FPS = 30

os.makedirs(OUT_DIR, exist_ok=True)


def purge():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
        for item in list(block):
            block.remove(item, do_unlink=True)


def armatures():
    return [o for o in bpy.data.objects if o.type == 'ARMATURE']


purge()

# 1. cn6 骨架（目标约定）
bpy.ops.import_shape.cn6(filepath=CN6_SRC)
arm_b = armatures()[0]
meshes_b = [o for o in bpy.data.objects if o.type == 'MESH']
for o in meshes_b:
    if o.name.endswith('#M'):
        o.name = o.name[:-2]
    while len(o.data.uv_layers) > 1:
        o.data.uv_layers.remove(o.data.uv_layers[-1])
assert len(meshes_b) == 7, "cn6 网格数异常: %d" % len(meshes_b)
print("B_READY bones=", len(arm_b.data.bones), "meshes=", [o.name for o in meshes_b])

# 2. psk 骨架（动作源约定）
bpy.ops.import_scene.psk(filepath=PSK)
arm_a = [a for a in armatures() if a != arm_b][0]
psk_meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o not in meshes_b]
for o in psk_meshes:
    bpy.data.objects.remove(o, do_unlink=True)
print("A_READY bones=", len(arm_a.data.bones), "psk_meshes_removed=", len(psk_meshes))
print("A_OBJ_MATRIX_IDENTITY=", arm_a.matrix_world == Matrix.Identity(4))

names_a = set(arm_a.data.bones.keys())
names_b = set(arm_b.data.bones.keys())
print("BONE_SET_DIFF:", sorted(names_a ^ names_b)[:8], "diff_count=", len(names_a ^ names_b))
print("B_MESHES=", [o.name for o in meshes_b])

# 3. 变换 B：旋转 + 缩放，并入静态数据
T = Matrix.Rotation(math.radians(ROT_Y_DEG), 4, 'Y') @ Matrix.Scale(SCALE, 4)
bpy.ops.object.select_all(action='DESELECT')
arm_b.select_set(True)
for o in meshes_b:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm_b
arm_b.matrix_world = T @ arm_b.matrix_world
for o in meshes_b:
    o.matrix_world = T @ o.matrix_world
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
print("B_APPLY_CHECK obj_matrix_identity=", arm_b.matrix_world == Matrix.Identity(4),
      "mesh0_identity=", meshes_b[0].matrix_world == Matrix.Identity(4))
head_b = arm_b.data.bones.get('Bip001Head')
print("B_TRANSFORMED head_world=", [round(c, 2) for c in arm_b.matrix_world @ head_b.head_local])

for o in meshes_b:
    has_arm = any(m.type == 'ARMATURE' and m.object == arm_b for m in o.modifiers)
    if not has_arm:
        m = o.modifiers.new(name='Armature', type='ARMATURE')
        m.object = arm_b
print("ARMATURE_MODIFIERS_ADDED")

# 4. 导入 ueanim 动作到 A
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


for clip in CLIP_FILES:
    act = get_action(clip)
    print("SRC:", clip, tuple(act.frame_range) if act else "MISSING")

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
        assert act is not None, "缺源: " + src
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


def retarget_to_b(name, src_action, total):
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
            pb_b.matrix = pose_map[pb_name].matrix.copy()
        for pb_name, pb_b in pose_map.items():
            pb_b.keyframe_insert(data_path="location", frame=f)
            pb_b.keyframe_insert(data_path="rotation_quaternion", frame=f)
            pb_b.keyframe_insert(data_path="scale", frame=f)
    print("RETARGET:", name, "frames=", tuple(round(x) for x in act.frame_range),
          "keys=", sum(len(fc.keyframe_points) for fc in act.fcurves))
    return act


def select_export_set():
    bpy.ops.object.select_all(action='DESELECT')
    arm_b.select_set(True)
    for o in meshes_b:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm_b


# 5. 模型导出：cn6（备用）+ FBX（正式，保向）
select_export_set()
cn6_out = os.path.join(OUT_DIR, "LEAD_Jinhsi_QYQXP.cn6")
bpy.ops.export_shape.cn6(filepath=cn6_out, use_selection=True)
print("CN6_EXPORTED:", cn6_out)

arm_b.data.pose_position = 'REST'
clear_anim(arm_b)
select_export_set()
model_fbx = os.path.join(OUT_DIR, "LEAD_Jinhsi_QYQXP_Model.fbx")
model_args = dict(
    use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
    bake_anim=False, axis_forward='-Z', axis_up='Y', apply_unit_scale=True,
    global_scale=1.0, mesh_smooth_type='OFF', use_mesh_modifiers=True,
)
bpy.ops.export_scene.fbx(filepath=model_fbx, **model_args)
print("MODEL_FBX_EXPORTED:", model_fbx)
arm_b.data.pose_position = 'POSE'

# 6. 重定向烘焙 + 逐动画 FBX
bpy.context.scene.render.fps = FPS
bpy.context.scene.render.fps_base = 1.0
FBX_ARGS = dict(
    use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
    bake_anim=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
    axis_forward='-Z', axis_up='Y', apply_unit_scale=True, global_scale=1.0,
    mesh_smooth_type='OFF', use_mesh_modifiers=True,
)
for name, total, segments in TARGETS:
    src = compose_on_a(name, total, segments)
    act = retarget_to_b(name, src, total)
    clear_anim(arm_b)
    arm_b.animation_data.action = act
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = total
    select_export_set()
    path = os.path.join(OUT_DIR, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, **FBX_ARGS)
    print("EXPORTED:", path)
print("BUILD2_DONE rot=%s scale=%.4f" % (ROT_Y_DEG, SCALE))
