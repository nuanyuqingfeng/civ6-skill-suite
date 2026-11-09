import bpy
import os
import sys
import math

from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jx_r3_face as face_rig
import jx_r3_anim as face_anim
import jx_r5_bangs
import jx_secondary
import jx_hair_rib
import jx_morph_face

# 发丝已由 RibbonAnim 原样驱动，二次运动只保留裙摆与飘带，避免在源动画上再叠弹簧
jx_secondary.set_families(("Skirt", "Piao"))

OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx"
REPORT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\reports"
REST_BEFORE = os.path.join(REPORT_DIR, "jinhsi_rest_before.tsv")
REST_AFTER = os.path.join(REPORT_DIR, "jinhsi_rest_after.tsv")
MODEL_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
PSK = os.path.join(MODEL_DIR, "R2T1JinxiMd10011.psk")
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"

# 整体朝向：达妮娅与今汐根骨世界旋转之差在垂直轴上的投影为 -90.000 度（见 workspace/gen/reports/朝向与动画.md）
RIG_ALIGN_Z_DEG = 90.0
ROT_AXIS_DEG = -90.0
# 骨架根（armature 对象）绕 X 轴的局部旋转：该角度进入导出的 bind 矩阵，InverseBind 由此校正到 0.01·rest⁻¹
ROOT_ROT_X_DEG = 0.0
SCALE = 1.0
# 整体等比缩放：140.0 厘米目标身高 ÷ 152.9216 厘米原始身高 = 0.915502
MODEL_SCALE = 0.915502
# 模型段与动画段一起跑：缩放改变骨架与网格，7 段动画必须同步重烘
MODEL_ONLY = False
# 形态键效果的几何诊断：拟合完立即退出，只打印表情预置的逐顶点误差与拉伸
FACE_DIAG = "--face-diag" in sys.argv
# 只导出待机段：验证待机时间线时不重烘其余六段
IDLE_ONLY = "--idle-only" in sys.argv
# 刘海下缘目标＝Eye 段 Z 中位 + 0.21 厘米；下缘一带沿水平外法向外推 0.15 厘米（预缩放尺度）
BANGS_SLOT = "MI_R2T1JinxiMd10011Bangs"
FACE_SLOT = "MI_R2T1JinxiMd10011Face"
EYE_SLOT = "MI_R2T1JinxiMd10011Eye"
BANGS_LOWER_OFFSET = 0.21
BANGS_PUSH = 0.15
BANGS_COLUMN = 0.2
BANGS_EDGE_BAND = 0.15
FRONT_STEP = 0.2
FRONT_ROWS = [140.5, 141.0, 141.5, 142.0, 143.0, 144.0, 145.0, 146.0]
FPS = 30
# ueanim 通道存的是绝对局部变换（单位米），psk 骨架与网格是厘米，二者相差 100 倍；
# 通道目标与模型 rest 同尺度，随 MODEL_SCALE 同比缩小
ANIM_SCALE = 100.0 * MODEL_SCALE
# 待机循环：前段两轮 Ui_Nature_Loop，中段插入待机动作1（Stand1_Action01 第 80…380 帧：首帧左手托住
# 右肘、右手抬到下颌前方 10.6 厘米处，末帧为条带自身最后一个关键帧）。进入过渡 56 帧按两侧速度做
# Hermite，落在插入段第 79 帧；退出过渡 57 帧同样按两侧速度做 Hermite，落在待机第 1 帧，
# 末段待机取第 2…240 帧共 239 帧，合计 720 + 56 + 56 + 301 = 1133 帧（37.767 秒）
IDLE_PERIOD = 240
IDLE_LOOPS_BEFORE = 2
IDLE_LOOPS_AFTER = 1
IDLE_TRANSITION_IN = 56
IDLE_TRANSITION_OUT = 56
INSERT_CLIP = "Stand1_Action01"
INSERT_RANGE = (80, 380)
# 称赞槽位换成祈愿：Stand1_Action03 第 0…458 帧（459 帧，15.267 秒）
KUDOS_CLIP = "Stand1_Action03"
KUDOS_RANGE = (0, 458)
IDLE_TOTAL = ((IDLE_LOOPS_BEFORE + IDLE_LOOPS_AFTER) * IDLE_PERIOD
              + IDLE_TRANSITION_IN + IDLE_TRANSITION_OUT
              + (INSERT_RANGE[1] - INSERT_RANGE[0] + 1))
# 通道旋转恰等于 identity 时转换器额外右乘 R_z(180°)，写通道前统一右乘该固定微旋规避
EPS = Quaternion((1.0, 0.0, 0.0), math.radians(0.01))
T = Matrix.Rotation(math.radians(ROT_AXIS_DEG), 4, 'Y') @ Matrix.Scale(SCALE, 4)

# io_export_cn6.getTranslationOrientation 的逐骨轴变换：转置后按 [[-Z],[Y],[X]] 置换，父级同式相除后再转置
RIG_ALIGN_MATRIX = Matrix.Rotation(math.radians(RIG_ALIGN_Z_DEG), 4, 'Z')
CN6_RZ90_T = Matrix.Rotation(math.radians(90.0), 4, 'Z')
CN6_RZ90_T.transpose()


def cn6_perm(m):
    t = m.copy()
    t.transpose()
    return Matrix([[-t[2][0], -t[2][1], -t[2][2], -t[2][3]],
                   [t[1][0], t[1][1], t[1][2], t[1][3]],
                   [t[0][0], t[0][1], t[0][2], t[0][3]],
                   [t[3][0], t[3][1], t[3][2], t[3][3]]])


def cn6_local(bone_matrix, parent_matrix):
    x = CN6_RZ90_T @ cn6_perm(bone_matrix)
    if parent_matrix is not None:
        x = x @ (CN6_RZ90_T @ cn6_perm(parent_matrix)).inverted()
    x.transpose()
    return x.decompose()


os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

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
# 形态键在删掉之前先取逐顶点位移，后面由 jx_morph_face 拟合成面骨动画通道
MORPHS = jx_morph_face.capture(body)
if body.data.shape_keys:
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.shape_key_remove(all=True)

# 骨架唯一：场景里只保留 psk 导入得到的那一个骨架，网格绑定必须指向它
RIG_NAME = arm_a.name.split(".")[0]
arm_a.name = RIG_NAME
arm_mods = [m for m in body.modifiers if m.type == 'ARMATURE']
assert len(arm_mods) == 1, [(m.name, m.object.name) for m in arm_mods]
assert arm_mods[0].object is arm_a, arm_mods[0].object.name
assert tuple(arm_a.scale) == (1.0, 1.0, 1.0), tuple(arm_a.scale)
print("SCENE_ARMATURES", [(o.name, len(o.data.bones)) for o in bpy.data.objects if o.type == 'ARMATURE'])
print("SCENE_OBJECTS", [(o.name, o.type) for o in bpy.data.objects])
print("RIG_TRANSFORM", arm_a.name, "scale", tuple(arm_a.scale), "location", tuple(arm_a.location),
      "rot", tuple(arm_a.rotation_euler))
print("MESH_BINDING", body.name, "modifier->", arm_mods[0].object.name,
      "parent->", body.parent.name if body.parent else "-")
print("MESH_WORLD", [round(c, 6) for row in body.matrix_world for c in row])

def scale_rig(arm, mesh, k):
    """骨架与网格绕世界原点同比缩放 k：缩放写进骨骼数据与顶点，骨架对象 scale 回到 1，网格世界矩阵回到单位阵。"""
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    arm.scale = (k, k, k)
    bpy.context.view_layer.update()
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.context.view_layer.update()
    mesh.data.transform(Matrix.Scale(k, 4))
    mesh.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.update()
    print("MODEL_SCALE k", k, "arm_scale", tuple(arm.scale),
          "mesh_world", [round(c, 6) for row in mesh.matrix_world for c in row])
    print("MODEL_SCALE_MESH_BOX", [round(min(v.co[i] for v in mesh.data.vertices), 3) for i in range(3)],
          [round(max(v.co[i] for v in mesh.data.vertices), 3) for i in range(3)])


def rotate_rig(arm, mesh, deg):
    """把骨架整体绕 Z 轴旋转 deg：骨架对象旋转后应用到骨骼数据，子骨相对父级的局部不变；
    网格顶点同步旋转，骨架与网格的世界矩阵保持一致的相对关系。"""
    rz = Matrix.Rotation(math.radians(deg), 4, 'Z')
    local_before = {}
    for b in arm.data.bones:
        local_before[b.name] = b.matrix_local.copy() if b.parent is None else \
            b.parent.matrix_local.inverted() @ b.matrix_local
    root_names = [b.name for b in arm.data.bones if b.parent is None]
    assert len(root_names) == 1, root_names
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    arm.rotation_mode = 'XYZ'
    arm.rotation_euler = (0.0, 0.0, math.radians(deg))
    bpy.context.view_layer.update()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    bpy.context.view_layer.update()
    mesh.data.transform(rz)
    mesh.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.update()
    worst = 0.0
    for b in arm.data.bones:
        if b.parent is None:
            continue
        local_after = b.parent.matrix_local.inverted() @ b.matrix_local
        dev = max(abs(local_before[b.name][i][j] - local_after[i][j]) for i in range(4) for j in range(4))
        worst = max(worst, dev)
    print("RIG_ALIGN", arm.name, "deg", deg, "root", root_names[0],
          "子骨局部最大偏差", format(worst, ".9f"))
    print("RIG_ALIGN_ROOT", [round(v, 6) for row in arm.data.bones[root_names[0]].matrix_local for v in row])
    print("RIG_ALIGN_MESH_WORLD", [round(v, 6) for row in mesh.matrix_world for v in row])
    print("RIG_ALIGN_MESH_BOX", [round(min(v.co[i] for v in mesh.data.vertices), 3) for i in range(3)],
          [round(max(v.co[i] for v in mesh.data.vertices), 3) for i in range(3)])


def front_coverage(mesh, rows, band):
    """从 -Y 沿 +Y 打射线，按行统计 band 内刘海为首个命中面的列占比（rows、band、FRONT_STEP 为预缩放尺度）。"""
    names = [m.name for m in mesh.data.materials]
    verts = [v.co.copy() for v in mesh.data.vertices]
    polys = {i: [] for i in range(len(names))}
    for p in mesh.data.polygons:
        polys[p.material_index].append(list(p.vertices))
    trees = [BVHTree.FromPolygons(verts, polys[i], all_triangles=False) for i in range(len(names))]
    ib = names.index(BANGS_SLOT)
    xs = []
    x = band[0] * MODEL_SCALE
    while x <= band[1] * MODEL_SCALE + 1e-9:
        xs.append(x)
        x += FRONT_STEP * MODEL_SCALE
    rows_out = []
    for z in rows:
        zz = z * MODEL_SCALE
        hit = 0
        for xx in xs:
            start = Vector((xx, -60.0 * MODEL_SCALE, zz))
            best = None
            near = 1e9
            for i, t in enumerate(trees):
                loc, nrm, idx, dist = t.ray_cast(start, Vector((0.0, 1.0, 0.0)), 120.0 * MODEL_SCALE)
                if loc is not None and loc.y < near:
                    near = loc.y
                    best = i
            if best == ib:
                hit += 1
        rows_out.append((z, hit, len(xs)))
    return rows_out


def stretch_bangs(mesh):
    """额前刘海下缘拉到眼睛上沿：以子集 Z 上限为锚点按 X 分箱对每列做 Z 方向缩放，
    使该列下缘落到目标 Z；下缘一带沿水平外法向外推，避免插进脸里。"""
    names = [m.name for m in mesh.data.materials]
    slot_verts = {n: set() for n in names}
    for p in mesh.data.polygons:
        for vi in p.vertices:
            slot_verts[names[p.material_index]].add(vi)
    bang = sorted(slot_verts[BANGS_SLOT])
    face = sorted(slot_verts[FACE_SLOT])
    eye = sorted(mesh.data.vertices[v].co.z for v in slot_verts[EYE_SLOT])
    eye_median = 0.5 * (eye[len(eye) // 2 - 1] + eye[len(eye) // 2])
    target = eye_median + BANGS_LOWER_OFFSET * MODEL_SCALE
    before = [mesh.data.vertices[v].co.copy() for v in bang]
    anchor = max(c.z for c in before)
    xlo = min(c.x for c in before)
    xhi = max(c.x for c in before)
    width = BANGS_COLUMN * MODEL_SCALE
    nbin = int(math.ceil((xhi - xlo) / width)) + 1
    lower = [None] * nbin
    for c in before:
        i = min(nbin - 1, int((c.x - xlo) / width))
        if lower[i] is None or c.z < lower[i]:
            lower[i] = c.z
    last = None
    for i in range(nbin):
        if lower[i] is None:
            lower[i] = last
        else:
            last = lower[i]
    last = None
    for i in range(nbin - 1, -1, -1):
        if lower[i] is None:
            lower[i] = last
        else:
            last = lower[i]
    cx = sum(mesh.data.vertices[v].co.x for v in face) / len(face)
    cy = sum(mesh.data.vertices[v].co.y for v in face) / len(face)
    moved = []
    scales = []
    pushed = 0
    for v, c in zip(bang, before):
        i = min(nbin - 1, int((c.x - xlo) / width))
        lo = lower[i]
        span = max(anchor - lo, 1e-6)
        s = (anchor - target) / span
        assert s >= 1.0 - 1e-9, (v, s, lo, target)
        w = (BANGS_EDGE_BAND - (c.z - lo) / span) / BANGS_EDGE_BAND
        w = min(1.0, max(0.0, w))
        if w > 0.0:
            pushed += 1
        scales.append(s)
        dx = c.x - cx
        dy = c.y - cy
        d = math.hypot(dx, dy)
        push = BANGS_PUSH * MODEL_SCALE * w
        moved.append(Vector((c.x + push * dx / d, c.y + push * dy / d, anchor - (anchor - c.z) * s)))
    for v, p in zip(bang, moved):
        mesh.data.vertices[v].co = p
    mesh.data.update()
    after = [mesh.data.vertices[v].co.copy() for v in bang]
    tree = KDTree(len(face))
    for i, v in enumerate(face):
        tree.insert(mesh.data.vertices[v].co, i)
    tree.balance()
    nearest = min(tree.find(c)[2] for c in after)
    scales.sort()
    print("BANGS_SUBSET", len(bang), "Y_max", round(max(c.y for c in before), 4),
          "X", [round(xlo, 4), round(xhi, 4)],
          "Z_before", [round(min(c.z for c in before), 4), round(anchor, 4)])
    print("BANGS_EYE", len(eye), "median", round(eye_median, 4), "max", round(eye[-1], 4),
          "target", round(target, 4), "target_minus_eye_max", round(target - eye[-1], 4))
    print("BANGS_COLUMNS", nbin, "s_min", round(scales[0], 4), "s_median", round(scales[len(scales) // 2], 4),
          "s_max", round(scales[-1], 4), "pushed", pushed)
    print("BANGS_Z_AFTER", [round(min(c.z for c in after), 4), round(max(c.z for c in after), 4)],
          "span_before", round(anchor - min(c.z for c in before), 4),
          "span_after", round(max(c.z for c in after) - min(c.z for c in after), 4))
    print("BANGS_LOWEST_PER_X", [(round(xlo + width * i, 2), round(lower[i] / MODEL_SCALE, 3))
                                 for i in range(0, nbin, 4)])
    print("BANGS_MIN_DIST_FACE", round(nearest, 4), "limit", round(0.1 * MODEL_SCALE, 4),
          "unscaled", round(nearest / MODEL_SCALE, 4))
    print("BANGS_MESH", len(mesh.data.vertices), len(names))
    assert nearest >= 0.1 * MODEL_SCALE, nearest
    assert len(mesh.data.vertices) == 37013, len(mesh.data.vertices)
    assert len(names) == 7, names
    assert max(c.z for c in after) - min(c.z for c in after) > anchor - min(c.z for c in before)


scale_rig(arm_a, body, MODEL_SCALE)
# 面部骨架在整体缩放之后建立：区域坐标与阈值都按最终尺度（140 厘米）定义
face_parts = face_rig.build_face_rig(arm_a, body)
face_rig.apply_weights(body, face_parts)
BANGS_COVERAGE_BEFORE = front_coverage(body, FRONT_ROWS, (-4.5, 4.5))
stretch_bangs(body)
BANGS_COVERAGE_AFTER = front_coverage(body, FRONT_ROWS, (-4.5, 4.5))
print("BANGS_COVERAGE_BEFORE", [(z, round(h / n, 3)) for z, h, n in BANGS_COVERAGE_BEFORE])
print("BANGS_COVERAGE_AFTER", [(z, round(h / n, 3)) for z, h, n in BANGS_COVERAGE_AFTER])
# 刘海整体上移：位移量由上睑缘最高点与刘海最低点之差决定，其余材质顶点不动
jx_r5_bangs.lift_bangs(body)
rotate_rig(arm_a, body, RIG_ALIGN_Z_DEG)
# 形态键 → 面骨通道：在最终（缩放+旋转）坐标系里拟合 86 个形态键的逐骨刚体增量
MORPH_RAW = MORPHS
MORPHS = jx_morph_face.build(arm_a, body, MORPH_RAW, MODEL_SCALE, RIG_ALIGN_Z_DEG) if MORPH_RAW else None
if FACE_DIAG:
    jx_morph_face.diagnose(arm_a, body, MORPH_RAW, MORPHS, MODEL_SCALE, RIG_ALIGN_Z_DEG)
    print("FACE_DIAG_DONE")
    sys.exit(0)

CLIP_FILES = ["Ui_Nature_Loop", "Ui_Nature_Start", "Ui_Weapon_Start", "Ui_Weapon_Loop",
              "Ui_Resonant_Start", "Ui_Resonant_Loop", "Team_Stand2", "Ui_Chip_End", "Cos_Pose"]
for clip in CLIP_FILES:
    bpy.ops.object.select_all(action='DESELECT')
    arm_a.select_set(True)
    bpy.context.view_layer.objects.active = arm_a
    bpy.ops.uf.import_ueanim(directory=ANIM_DIR, files=[{'name': clip + '.ueanim'}])
# 插入的待机动作与祈愿动作在 CommonAnim 根目录，不在 UiAnim 子目录
for clip in (INSERT_CLIP, KUDOS_CLIP):
    bpy.ops.object.select_all(action='DESELECT')
    arm_a.select_set(True)
    bpy.context.view_layer.objects.active = arm_a
    bpy.ops.uf.import_ueanim(directory=os.path.dirname(ANIM_DIR),
                             files=[{'name': clip + '.ueanim'}])
# 鸣潮 RibbonAnim 二次运动层：七段动画的长尾发丝直接采用游戏自带的叠加层
RIB_ACTIONS = ("Rib_Ui_Nature_Start", "Rib_Ui_Nature_Loop",
               "Rib_Ui_Weapon_Start", "Rib_Ui_Weapon_Loop",
               "Rib_Stand1_Action01", "Rib_Stand1_Action03", "Rib_Team_Stand2")
jx_hair_rib.import_actions(arm_a, RIB_ACTIONS)


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


BASE_TARGETS = [
    ("JX_IDLE", IDLE_TOTAL, [("Ui_Nature_Loop", 1)]),
    ("JX_FirstMeet", 210, [("Ui_Nature_Start", 1), ("Ui_Nature_Loop", 2)]),
    ("JX_DeclareWarHuman", 180, [("Ui_Weapon_Start", 1), ("Ui_Weapon_Loop", 2)]),
    ("JX_DeclareWarAI", 330, [("Ui_Weapon_Start", 1), ("Ui_Weapon_Loop", 4)]),
    ("JX_Kudos", KUDOS_RANGE[1] - KUDOS_RANGE[0] + 1, [(KUDOS_CLIP, 1)]),
    ("JX_Warning", 150, [("Team_Stand2", 1)]),
    ("JX_Defeat", 240, [("Ui_Nature_Loop", 1)]),
]
# 动画长度不得短于语音：按语音结束帧补齐尾部（Kudos 语音到帧 400、Warning 到帧 223），
# 补齐段把第 base 帧的姿态原样保持到末帧，源条带轨迹只到 base 帧
FACE_VOICE_END = face_anim.voice_ends()
TARGETS = [(name, max(base, FACE_VOICE_END.get(name, 0)), base, segments)
           for name, base, segments in BASE_TARGETS]
# 通道标定：CALIB_ANIM 为真时写恒等通道，用于测出转换器曲线路径的每骨静态基准
CALIB_ANIM = False
# 单帧跳变限速阈值：超过即视为源数据抽动，按阈值截断
ROT_SPIKE_DEG = 45.0
LOC_SPIKE_CM = 1.2
CHANNEL_TABLE = os.path.join(OUT_DIR.replace("jinhsi_fbx", "reports"), "anim_channel_map.tsv")
FACE_ENVELOPE = face_anim.load_envelope(
    action_frames={name: total for name, total, _base, _segments in TARGETS})
DIAG_ONLY = CALIB_ANIM


def clear_anim(arm):
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = None
    for t in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(t)


def compose_on_a(name, source, total, segments):
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
    bpy.ops.nla.bake(frame_start=1, frame_end=source, step=1, only_selected=True,
                     visual_keying=True, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    baked = arm_a.animation_data.action
    baked.name = "SRC_" + name
    if total > source:
        # 源条带只烘到 base 帧，第 base 帧姿态原样保持到末帧
        bpy.context.scene.frame_set(source)
        bpy.context.view_layer.update()
        for pb in arm_a.pose.bones:
            pb.keyframe_insert(data_path="location", frame=total)
            pb.keyframe_insert(data_path="rotation_quaternion", frame=total)
            pb.keyframe_insert(data_path="scale", frame=total)
        print("ANIM_HOLD", name, "base", source, "total", total)
    return baked


def idle_snapshot(action, frame):
    """取某一动作在某帧的逐骨局部变换（位置、四元数、缩放）。"""
    clear_anim(arm_a)
    arm_a.animation_data.action = action
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy())
            for pb in arm_a.pose.bones}


def pose_step(prev, cur, scale):
    """一帧的局部增量：平移差、在 cur 处取值的旋转向量（弧度）、缩放差，整体乘 scale。"""
    out = {}
    for name in cur:
        dq = prev[name][1].inverted() @ cur[name][1]
        if dq.w < 0.0:
            dq = Quaternion((-dq.w, -dq.x, -dq.y, -dq.z))
        axis, ang = dq.to_axis_angle()
        out[name] = ((cur[name][0] - prev[name][0]) * scale,
                     axis * (ang * scale),
                     (cur[name][2] - prev[name][2]) * scale)
    return out


def clamp_tangent(m, target):
    """切线整形：长度不超过目标位移的一点五倍。
    三次曲线的切线项系数最大只有 0.148，这个上限把冲过头的幅度限制在两成以内；
    切线方向允许与目标相反，修正段需要先反向兜住载体的速度再衰减。"""
    if target.length < 1e-9:
        return Vector((0.0, 0.0, 0.0))
    lim = target.length * 1.5
    return m * (lim / m.length) if m.length > lim else m


def hermite_pose(a, va, b, vb, t):
    """三次 Hermite：位置与缩放走线性三次曲线，旋转在 q0 的切空间里插值。
    va、vb 是两端的一阶切线（pose_step 乘过渡帧数）。两端姿态固定，
    不经过两点间的球面插值，差值接近 180 度时也不会翻到另一侧。"""
    t2 = t * t
    t3 = t2 * t
    h00 = 2.0 * t3 - 3.0 * t2 + 1.0
    h10 = t3 - 2.0 * t2 + t
    h01 = -2.0 * t3 + 3.0 * t2
    h11 = t3 - t2
    out = {}
    for name in a:
        p0, q0, s0 = a[name]
        p1, q1, s1 = b[name]
        dq = q0.inverted() @ q1
        if dq.w < 0.0:
            dq = Quaternion((-dq.w, -dq.x, -dq.y, -dq.z))
        u1 = dq.axis * dq.angle if dq.angle > 1e-9 else Vector((0.0, 0.0, 0.0))
        # 末切线在 q1 的坐标系里给出，转到 q0 的切空间后再整形、相加
        m0 = clamp_tangent(va[name][1], u1)
        m1 = clamp_tangent((q0.inverted() @ q1) @ vb[name][1], u1)
        u = m0 * h10 + u1 * h01 + m1 * h11
        ang = u.length
        rot = Quaternion(u / ang, ang) if ang > 1e-9 else Quaternion()
        t1 = p1 - p0
        d0 = clamp_tangent(va[name][0], t1)
        d1 = clamp_tangent(vb[name][0], t1)
        k1 = s1 - s0
        e0 = clamp_tangent(va[name][2], k1)
        e1 = clamp_tangent(vb[name][2], k1)
        out[name] = (p0 * h00 + d0 * h10 + p1 * h01 + d1 * h11,
                     q0 @ rot,
                     s0 * h00 + e0 * h10 + s1 * h01 + e1 * h11)
    return out


def local_compose(a, b):
    """两段骨骼局部变换相乘：结果等于先走 b 再走 a。"""
    scale = Vector((a[2].x * b[2].x, a[2].y * b[2].y, a[2].z * b[2].z))
    loc = a[0] + a[1] @ Vector((b[0].x * a[2].x, b[0].y * a[2].y, b[0].z * a[2].z))
    return (loc, a[1] @ b[1], scale)


def local_inverse(a):
    scale = Vector((1.0 / a[2].x, 1.0 / a[2].y, 1.0 / a[2].z))
    q = a[1].inverted()
    loc = -(q @ Vector((a[0].x * scale.x, a[0].y * scale.y, a[0].z * scale.z)))
    return (loc, q, scale)


def compose_idle():
    """两轮待机 + 进入过渡 + 待机动作1 + 退出过渡 + 一轮待机，逐帧写关键帧，首尾同为待机第 1 帧。

    两端过渡都走三次 Hermite：端点姿态固定，首末切线取两侧动画自身的逐帧速度，
    接缝两侧的速度因此连续。进入过渡落在插入段第 p0-1 帧，下一帧正是第 p0 帧，
    不会出现同一姿态连写两帧的停顿；退出过渡落在待机第 1 帧，末端切线取待机
    第 1→2 帧的速度。"""
    idle = resolve("Ui_Nature_Loop")
    pray = resolve(INSERT_CLIP)
    assert idle is not None and pray is not None, (idle, pray)
    for pb in arm_a.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    p0, p1 = INSERT_RANGE
    strip_first = p0 - IDLE_TRANSITION_IN - 1
    idle_cache = {f: idle_snapshot(idle, f) for f in range(1, IDLE_PERIOD + 1)}
    pray_cache = {f: idle_snapshot(pray, f) for f in range(strip_first, p1 + 1)}
    idle_end = idle_cache[IDLE_PERIOD]
    idle_first = idle_cache[1]
    prayer_last = pray_cache[p1]
    poses = {}
    head = IDLE_PERIOD * IDLE_LOOPS_BEFORE
    for i in range(head):
        poses[i + 1] = idle_cache[i % IDLE_PERIOD + 1]
    enter_len = IDLE_TRANSITION_IN
    # 进入过渡以插入片段的进入段为载体，叠加一段衰减到零的局部修正：
    # 首帧修正恰好等于「待机末帧相对插入首帧」的差，末帧修正为单位阵，
    # 因此末帧速度完全由载体决定，接上插入段第 p0 帧时既不换方向也不停顿。
    base = pray_cache[strip_first + 1]
    offset = {name: local_compose(local_inverse(base[name]), idle_end[name])
              for name in idle_end}
    step_c = pose_step(base, pray_cache[strip_first + 2], enter_len)
    step_i = pose_step(idle_cache[IDLE_PERIOD - 1], idle_end, enter_len)
    v_off = {}
    for name in idle_end:
        q = offset[name][1]
        v_off[name] = (q.inverted() @ (step_i[name][0] - step_c[name][0]),
                       q.inverted() @ (step_i[name][1] - step_c[name][1]),
                       step_i[name][2] - step_c[name][2])
    rest_pose = {name: (Vector((0.0, 0.0, 0.0)), Quaternion(), Vector((1.0, 1.0, 1.0)))
                 for name in idle_end}
    zero_step = {name: (Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 0.0)))
                 for name in idle_end}
    for i in range(1, enter_len + 1):
        corr = hermite_pose(offset, v_off, rest_pose, zero_step, i / enter_len)
        cur = pray_cache[strip_first + i]
        poses[head + i] = {name: local_compose(cur[name], corr[name]) for name in cur}
    for i in range(p1 - p0 + 1):
        poses[head + enter_len + 1 + i] = pray_cache[p0 + i]
    tail = head + enter_len + (p1 - p0 + 1)
    exit_len = IDLE_TRANSITION_OUT + 1
    v_in = pose_step(pray_cache[p1 - 1], pray_cache[p1], exit_len)
    v_out = pose_step(idle_cache[1], idle_cache[2], exit_len)
    for i in range(1, exit_len + 1):
        poses[tail + i] = hermite_pose(prayer_last, v_in, idle_first, v_out, i / exit_len)
    body = tail + exit_len
    for i in range(IDLE_PERIOD - 1):
        poses[body + i + 1] = idle_cache[i + 2]
    assert body + IDLE_PERIOD - 1 == IDLE_TOTAL, (body, IDLE_TOTAL)

    def seam_steps(first, count):
        """接缝处逐帧的最大角度变化（度）：取该帧全部骨骼中旋转增量最大者。"""
        out = []
        for i in range(1, count + 1):
            worst = 0.0
            for name in poses[first + i]:
                ang = math.degrees(poses[first + i][name][1].rotation_difference(
                    poses[first + i - 1][name][1]).angle)
                if ang > 180.0:
                    ang = 360.0 - ang
                worst = max(worst, ang)
            out.append(worst)
        return out

    for label, first, count in (("HEAD", head, IDLE_TRANSITION_IN + 12),
                                ("TAIL", tail, IDLE_TRANSITION_OUT + 13)):
        steps = seam_steps(first, count)
        print("IDLE_SEAM", label, "frames", first + 1, "..", first + count, "count", count,
              "steps", " ".join("%.2f" % v for v in steps), "max", "%.2f" % max(steps))
    loop = 0.0
    for name in poses[1]:
        ang = math.degrees(poses[1][name][1].rotation_difference(poses[IDLE_TOTAL][name][1]).angle)
        if ang > 180.0:
            ang = 360.0 - ang
        loop = max(loop, ang)
    print("IDLE_SEAM LOOP", "%.2f" % loop)
    act = bpy.data.actions.new("SRC_JX_IDLE")
    clear_anim(arm_a)
    arm_a.animation_data.action = act
    prev = {}
    for f in range(1, IDLE_TOTAL + 1):
        pose = poses[f]
        for pb in arm_a.pose.bones:
            loc, quat, scale = pose[pb.name]
            q = quat.copy()
            if pb.name in prev and q.dot(prev[pb.name]) < 0.0:
                q.negate()
            prev[pb.name] = q.copy()
            pb.location = loc
            pb.rotation_quaternion = q
            pb.scale = scale
            pb.keyframe_insert(data_path="location", frame=f)
            pb.keyframe_insert(data_path="rotation_quaternion", frame=f)
            pb.keyframe_insert(data_path="scale", frame=f)
    print("ANIM_COMPOSE_IDLE", "total", IDLE_TOTAL, "idle_period", IDLE_PERIOD,
          "loops", (IDLE_LOOPS_BEFORE, IDLE_LOOPS_AFTER), "insert", INSERT_CLIP, INSERT_RANGE,
          "transition", (IDLE_TRANSITION_IN, IDLE_TRANSITION_OUT),
          "seams", (head + 1, head + IDLE_TRANSITION_IN, tail + 1, tail + exit_len))
    return act


def topo_order(arm):
    order = []
    seen = set()

    def visit(pb):
        if pb.name in seen:
            return
        seen.add(pb.name)
        if pb.parent is not None:
            visit(pb.parent)
        order.append(pb)

    for pb in arm.pose.bones:
        visit(pb)
    return order


def load_channel_table(path):
    table = {}
    with open(path, encoding="utf-8") as fh:
        fh.readline()
        for line in fh:
            f = line.rstrip("\n").split("\t")
            table[f[0]] = (Vector((float(f[1]), float(f[2]), float(f[3]))),
                           Quaternion((float(f[7]), float(f[4]), float(f[5]), float(f[6]))))
    print("CHANNEL_TABLE", path, len(table))
    return table


def retarget_c(name, src_action, total):
    """ueanim 通道值是绝对局部变换（米），ueformat 导入器把它写成 pose basis。
    目标姿态按骨架链累乘成 armature 空间矩阵，再用 io_export_cn6 的逐骨轴变换求出 cn6 空间的局部变换。
    转换器曲线路径实测为 out_q = Q ⊗ in_q、out_p = Q·in_p + p_Q（Q、p_Q 为动画侧每骨静态基准，
    由 CALIB_ANIM 标定后写成 workspace/gen/reports/anim_channel_map.tsv），据此反解通道取值。
    CALIB_ANIM 为真时写恒等通道并右乘 EPS（规避通道恰为 identity 时转换器额外右乘 R_z(180°)）。"""
    clear_anim(arm_c)
    act = bpy.data.actions.new(name)
    arm_c.animation_data.action = act
    clear_anim(arm_a)
    if src_action is not None:
        arm_a.animation_data.action = src_action

    for pb in arm_c.pose.bones:
        pb.rotation_mode = 'QUATERNION'

    rest_all = {b.name: b.matrix_local.copy() for b in arm_c.data.bones}
    rest_static = {}
    for pb in arm_c.pose.bones:
        bl = arm_c.data.bones[pb.name]
        parent_matrix = None if bl.parent is None else bl.parent.matrix_local.copy()
        rest_static[pb.name] = cn6_local(bl.matrix_local.copy(), parent_matrix)
    channel_base = None if CALIB_ANIM else load_channel_table(CHANNEL_TABLE)

    order = topo_order(arm_c)
    prev_rot = {}
    prev_loc = {}
    jerk = {}
    loc_jerk = {}
    root_hold = None
    for f in range(1, total + 1):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        pose_world = {}
        for pb_c in order:
            pb_a = arm_a.pose.bones[pb_c.name]
            loc = pb_a.location * ANIM_SCALE
            if pb_c.parent is None:
                # 领袖镜头固定，根骨骼位移一律压成首帧值，禁止上下与前后漂移
                if root_hold is None:
                    root_hold = loc.copy()
                    print("ANIM_ROOT_HOLD", name, [round(v, 4) for v in root_hold])
                loc = root_hold.copy()
            local = Matrix.LocRotScale(loc, pb_a.rotation_quaternion, pb_a.scale)
            if pb_c.parent is None:
                pose_world[pb_c.name] = RIG_ALIGN_MATRIX @ local
            else:
                pose_world[pb_c.name] = pose_world[pb_c.parent.name] @ local
        if not CALIB_ANIM:
            params = face_anim.facial_params(name, f, FACE_ENVELOPE)
            if MORPHS is not None and jx_morph_face.takes_over_brow(name, f, total):
                params["brow_L"] = 0.0
                params["brow_R"] = 0.0
            face_rig.pose_face(pose_world, params, rest_all)
            if MORPHS is not None:
                jx_morph_face.pose(pose_world, rest_all, MORPHS, name, f, total)
        for pb_c in order:
            if CALIB_ANIM:
                pb_c.location = Vector((0.0, 0.0, 0.0))
                pb_c.rotation_quaternion = EPS.copy()
                pb_c.scale = Vector((1.0, 1.0, 1.0))
                pb_c.keyframe_insert(data_path="location", frame=f)
                pb_c.keyframe_insert(data_path="rotation_quaternion", frame=f)
                pb_c.keyframe_insert(data_path="scale", frame=f)
                continue
            parent_world = None if pb_c.parent is None else pose_world[pb_c.parent.name]
            t_p, t_q, t_s = cn6_local(pose_world[pb_c.name], parent_world)
            # 每骨的转换器静态基准来自标定表；新增骨必须先跑一轮 CALIB_ANIM 标定再补表
            base_p, base_q = channel_base[pb_c.name]
            loc = base_q.inverted() @ (t_p - base_p)
            rot = (base_q.inverted() @ t_q @ EPS).normalized()
            if pb_c.name in prev_rot and rot.dot(prev_rot[pb_c.name]) < 0.0:
                rot.negate()
            # 单帧跳变限速：源数据里个别骨会出现一帧内的整段位移/翻转，
            # 游戏里就是一次抽动，这里把单帧增量压到阈值内
            if pb_c.name in prev_rot:
                axis_ang = prev_rot[pb_c.name].rotation_difference(rot).to_axis_angle()
                if math.degrees(axis_ang[1]) > ROT_SPIKE_DEG:
                    rot = (prev_rot[pb_c.name] @ Quaternion(
                        axis_ang[0], math.radians(ROT_SPIKE_DEG))).normalized()
            if pb_c.name in prev_loc:
                dv = loc - prev_loc[pb_c.name]
                if dv.length > LOC_SPIKE_CM:
                    loc = prev_loc[pb_c.name] + dv * (LOC_SPIKE_CM / dv.length)
            if pb_c.name in prev_rot:
                step = math.degrees(2.0 * math.acos(min(1.0, abs(rot.dot(prev_rot[pb_c.name])))))
                if step > jerk.get(pb_c.name, (0.0, 0))[0]:
                    jerk[pb_c.name] = (step, f)
            if pb_c.name in prev_loc:
                dstep = (loc - prev_loc[pb_c.name]).length
                if dstep > loc_jerk.get(pb_c.name, (0.0, 0))[0]:
                    loc_jerk[pb_c.name] = (dstep, f)
            prev_loc[pb_c.name] = loc.copy()
            prev_rot[pb_c.name] = rot.copy()
            pb_c.location = loc
            pb_c.rotation_quaternion = rot
            pb_c.scale = t_s
            pb_c.keyframe_insert(data_path="location", frame=f)
            pb_c.keyframe_insert(data_path="rotation_quaternion", frame=f)
            pb_c.keyframe_insert(data_path="scale", frame=f)
        if f == 1:
            diag_bones = [b.name for b in arm_c.data.bones if b.parent is None] +                 ["Root", "Bip001", "Bip001Pelvis", "Bip001Head"]
            for bn in diag_bones:
                if bn not in pose_world:
                    continue
                pb = arm_c.pose.bones[bn]
                parent_world = None if pb.parent is None else pose_world[pb.parent.name]
                t_p, t_q, t_s = cn6_local(pose_world[bn], parent_world)
                s_p, s_q, s_s = rest_static[bn]
                print("RETARGET_C_T0", name, bn,
                      "t_p", [round(v, 4) for v in t_p], "s_p", [round(v, 4) for v in s_p],
                      "t_s", [round(v, 4) for v in t_s],
                      "chan_s", [round(v, 6) for v in pb.scale],
                      "deg", round(math.degrees(t_q.rotation_difference(s_q).angle), 3))
    print("RETARGET_C:", name, "frames=", tuple(round(x) for x in act.frame_range))
    top = sorted(jerk.items(), key=lambda kv: -kv[1][0])[:6]
    print("ANIM_JERK", name, " ".join("%s=%.1f@%d" % (b, v[0], v[1]) for b, v in top))
    top = sorted(loc_jerk.items(), key=lambda kv: -kv[1][0])[:6]
    print("ANIM_JERK_LOC", name, " ".join("%s=%.2f@%d" % (b, v[0], v[1]) for b, v in top))
    return act


bpy.context.scene.render.fps = FPS
bpy.context.scene.render.fps_base = 1.0
FBX_ARGS = dict(
    use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
    bake_anim=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
    axis_forward='-Z', axis_up='Y', apply_unit_scale=False, global_scale=1.0,
    mesh_smooth_type='OFF', use_mesh_modifiers=True,
)


def dump_rest(path):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("bone\tparent\t" + "\t".join("m%d%d" % (r, c) for r in range(4) for c in range(4)) + "\n")
        for b in arm_a.data.bones:
            vals = ["%.9f" % b.matrix_local[r][c] for r in range(4) for c in range(4)]
            fh.write("\t".join([b.name, b.parent.name if b.parent else "-"] + vals) + "\n")
    print("REST_DUMP", path, len(arm_a.data.bones))


# 模型导出：场景里只有 psk 骨架与它自己的网格，选择集就是这两个对象
dump_rest(REST_BEFORE)
arm_a.data.pose_position = 'REST'
clear_anim(arm_a)
# 骨架根旋转只在模型导出期间生效；网格的父级逆矩阵同步补偿，其世界矩阵保持单位
mesh_world_before = body.matrix_world.copy()
mesh_parent_inverse_before = body.matrix_parent_inverse.copy()
arm_a.rotation_mode = 'XYZ'
arm_a.rotation_euler = (math.radians(ROOT_ROT_X_DEG), 0.0, 0.0)
bpy.context.view_layer.update()
body.matrix_parent_inverse = arm_a.matrix_world.inverted()
bpy.context.view_layer.update()
print("ROOT_ROT", arm_a.name, "rot", tuple(arm_a.rotation_euler), "scale", tuple(arm_a.scale),
      "location", tuple(arm_a.location))
print("MESH_WORLD_BEFORE", [round(c, 6) for row in mesh_world_before for c in row])
print("MESH_WORLD_EXPORT", [round(c, 6) for row in body.matrix_world for c in row])
bpy.ops.object.select_all(action='DESELECT')
arm_a.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = body
print("EXPORT_SELECTION", [(o.name, o.type) for o in bpy.context.selected_objects])
print("EXPORT_SCENE_ARMATURES", [o.name for o in bpy.data.objects if o.type == 'ARMATURE'])
# 模型本体走 cn6 链：cn6 逐骨携带 rest 局部变换与 InvWorld，转换器不做额外矩阵写入
model_path = os.path.join(OUT_DIR, "LEAD_Jinhsi_QYQXP.cn6")
print("CN6_SELECTION", [(o.name, o.type) for o in bpy.context.selected_objects])
bpy.ops.export_shape.cn6(filepath=model_path, triangulate=True, use_selection=True)
print("MODEL_CN6:", model_path)
arm_a.rotation_euler = (0.0, 0.0, 0.0)
body.matrix_parent_inverse = mesh_parent_inverse_before
bpy.context.view_layer.update()
print("ROOT_ROT_RESET", arm_a.name, "rot", tuple(arm_a.rotation_euler),
      "mesh_world", [round(c, 6) for row in body.matrix_world for c in row])
arm_a.data.pose_position = 'POSE'
dump_rest(REST_AFTER)

if MODEL_ONLY:
    print("MODEL_ONLY_DONE")
    sys.exit(0)

# 动画侧骨架：模型导出后从同一骨架复制，rest 与模型骨架逐骨一致
arm_a.name = RIG_NAME + "_src"
bpy.ops.object.select_all(action='DESELECT')
arm_a.select_set(True)
bpy.context.view_layer.objects.active = arm_a
bpy.ops.object.duplicate(linked=False)
arm_c = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o != arm_a][0]
arm_c.name = RIG_NAME
# 动画侧 FBX 走 CivNexus6 的 FBX 导入器，它在骨架根节点上写 100 倍单位换算；
# 导出前把骨架对象缩到 0.01，换算后在 fgx 世界骨上回到 1（骨局部不受对象缩放影响）
arm_c.scale = (0.01, 0.01, 0.01)
print("ANIM_RIG", arm_c.name, "from", arm_a.name, "object_scale", tuple(arm_c.scale))

CALIB_REST = False

for name, total, base, segments in TARGETS:
    if DIAG_ONLY and name != "JX_IDLE":
        continue
    idle_head = IDLE_PERIOD * IDLE_LOOPS_BEFORE + IDLE_TRANSITION_IN
    window = (idle_head + 1, idle_head + 1 + (INSERT_RANGE[1] - INSERT_RANGE[0]))
    if name == "JX_IDLE":
        src = compose_idle()
    elif CALIB_REST:
        src = None
    else:
        src = compose_on_a(name, base, total, segments)
    if src is not None:
        rib_window = (window[0], window[0] + (INSERT_RANGE[1] - INSERT_RANGE[0])) \
            if name == "JX_IDLE" else None
        jx_hair_rib.overlay(arm_a, src, name, total, segments, rib_window,
                            damp=0.5 if rib_window is not None else None)
        jx_secondary.bake(arm_a, src, name, total, window, body, ANIM_SCALE, chain_physics=False)
    act = retarget_c(name, src, total)
    clear_anim(arm_c)
    arm_c.animation_data.action = act
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = total
    bpy.ops.object.select_all(action='DESELECT')
    arm_c.select_set(True)
    bpy.context.view_layer.objects.active = arm_c
    path = os.path.join(OUT_DIR, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, **FBX_ARGS)
    print("ANIM_FBX:", path)
    if IDLE_ONLY:
        print("IDLE_ONLY_DONE")
        sys.exit(0)
print("BUILD5_DONE")
