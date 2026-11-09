import json
import math

import bpy
from mathutils import Matrix, Vector

PARTS = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\tmp\jx14_parts.json"
EYE_SCALE = 0.915502

JAW_MAX_DEG = 10.18
BLINK_DOWN_CM = 1.55
BLINK_FORWARD_CM = 0.10
LOWER_LID_RATIO = 0.40
# 静置眼裂高度：上睑缘在绑定网格上下移、下睑缘轻微上移，眨眼行程按原幅度叠加
REST_LID_DOWN_CM = 0.033
REST_LID_UP_CM = 0.015
# 上睑权重沿横向的收敛：内眦一侧下压多、需减弱得多，外眦一侧只做轻微减弱
LID_TAPER_HALF_W_CM = 1.45
LID_TAPER_INNER_DROP = 0.34
LID_TAPER_OUTER_DROP = 0.06
# 下睑归属判定：眼心下方 0.15~1.15 厘米、横向 1.55 厘米以内
LID_LO_Z_TOP_CM = 0.15
LID_LO_Z_BOTTOM_CM = 1.15
LID_LO_HALF_W_CM = 1.55
# 下睑权重的横向窗口：眼心左右 1.20 厘米内为 1，到 1.55 厘米收敛为 0
LID_LO_FULL_W_CM = 1.20
# 上睑权重的竖向窗口：眼心上方 0.95 厘米内为 1，到 1.30 厘米收敛为 0。
# 眼褶以上的上颊不属于睑部，眨眼时不跟着下落，否则两侧脸颊被上睑骨拉出凹陷
LID_UP_FULL_ABOVE_CM = 0.95
LID_UP_FADE_ABOVE_CM = 1.30
# 上睑权重的横向窗口：眼心左右 1.60 厘米内为 1，到 1.95 厘米收敛为 0（外眦以外的颞部不动）
LID_UP_FULL_W_CM = 1.60
LID_UP_FADE_W_CM = 1.95
GAZE_MAX_DEG = 13.0
# 眼球水平转动绕竖直轴（世界 Z）：角度直接以度传入，正值使视线转向 +Y（画面右侧）
EYE_YAW_AXIS = (0.0, 0.0, 1.0)
BROW_UP_CM = 0.10
# 下颌区域：唇线上方 0.9 厘米到下颏下缘 120.5 厘米，横向 6.2 厘米以内
MOUTH_CORNER_X_CM = 2.4
JAW_Z_TOP_CM = 0.9
JAW_Z_BOTTOM_CM = 120.5
# 张口权重直接写在 JX_Jaw 上，沿横向按 cos(π/2·|x|/2.4) 的 1.5 次方衰减：
# 口部中线 1.0，到嘴角收敛到 0，嘴角不动，张口呈中央最开的梭形
LIP_HALF_W_CM = 2.4
LIP_FALL_POW = 1.5
# 上唇竖向权重：唇线上方 0.30 厘米内恒为 1，到 0.65 厘米收敛为 0
LIP_UP_ZONE_CM = 0.30
LIP_UP_FADE_CM = 0.35
# 嘴角骨只作用于嘴角附近的窄带：横向 1.20 厘米起涨、1.60 厘米满额，
# 2.00 厘米回落归零；颊部 1.8 厘米以外不再受嘴角骨牵动
MOUTH_CORNER_WEIGHT = 1.0
MOUTH_CORNER_BAND_CM = (1.20, 1.60)
MOUTH_CORNER_OUTER_CM = (1.60, 2.00)
MOUTH_CORNER_ZONE_CM = 0.60
# 说话时嘴角沿 ±x 外扩的最大位移（厘米），按张口系数线性取用，闭口为 0
CORNER_OUT_CM = 0.20

FACE_BONES = ("JX_Jaw", "JX_LipUp", "JX_LipLo", "JX_MouthCorner_L", "JX_MouthCorner_R",
              "JX_LidUp_L", "JX_LidUp_R", "JX_LidLo_L", "JX_LidLo_R",
              "JX_Eye_L", "JX_Eye_R", "JX_Brow_L", "JX_Brow_R",
              "JX_BrowIn_L", "JX_BrowIn_R", "JX_Cheek_L", "JX_Cheek_R", "JX_Nose")
# 内眉从眉部的内段分出：按 |x| 取最靠近面部中线的 45%
BROW_INNER_SHARE = 0.45
BROW_INNER_SET = {}
# 眉内/外两段的权重按横向参数连续过渡，避免两骨之间出现一条被撕开的硬缝
BROW_GRAD = {}
# 颊骨横带：眼心横向 1.2~5.0 厘米、唇线上方 1.0 厘米到眼心上方 0.6 厘米，避开睑部与口部权重
CHEEK_LATERAL_CM = (1.2, 5.0)
CHEEK_WEIGHT = 0.55
# 鼻骨横带：中线 ±0.9 厘米、唇线上方 1.9~4.6 厘米
NOSE_HALF_W_CM = 0.9
NOSE_Z_CM = (1.9, 4.6)
NOSE_WEIGHT = 0.60
AXES = {}
DIRS = {}
EYE_PIVOT_LOCAL = {}
BROW_INNER_PIVOT = {}
BROW_INNER_ARM = {}


def load_parts():
    with open(PARTS, encoding="utf-8") as fh:
        return json.load(fh)


def _ramp(x, lo, hi):
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def _lid_taper(dx, ctr_x):
    inner = 1.0 if ctr_x < 0.0 else -1.0
    u_in = min(1.0, max(0.0, dx * inner) / LID_TAPER_HALF_W_CM)
    u_out = min(1.0, max(0.0, -dx * inner) / LID_TAPER_HALF_W_CM)
    return (1.0 - LID_TAPER_INNER_DROP * u_in * u_in) * (1.0 - LID_TAPER_OUTER_DROP * u_out * u_out)


def _eye_center(parts, side):
    return Vector(parts["eyeball"][side]["center_dome"]) * EYE_SCALE


def _eye_pivot(parts, side):
    """眼球拟合球心：瞳孔绕它转动才会在睑裂内横向位移，绕穹面质心转等于原地旋转。"""
    return Vector(parts["eyeball"][side]["center_fit"]) * EYE_SCALE


def _face_vert_indices(mesh):
    names = [m.name for m in mesh.data.materials]
    slot = names.index("MI_R2T1JinxiMd10011Face")
    out = set()
    for p in mesh.data.polygons:
        if p.material_index == slot:
            out.update(p.vertices)
    return sorted(out)


def build_face_rig(arm, mesh):
    parts = load_parts()
    co = [v.co.copy() for v in mesh.data.vertices]
    eyeL = _eye_center(parts, "L")
    eyeR = _eye_center(parts, "R")
    mouth = sum((co[i] for i in parts["mouth_ap"]), Vector()) / len(parts["mouth_ap"])
    print("RIG_MOUTH", [round(v, 4) for v in mouth])
    jaw_pivot = Vector((0.0, 1.6, mouth.z + 2.45))
    lip_pivot = Vector((0.0, -2.2, mouth.z + 2.6))
    global JAW_PIVOT
    JAW_PIVOT = jaw_pivot.copy()
    print("RIG_PIVOT jaw", [round(v, 4) for v in jaw_pivot], "lip", [round(v, 4) for v in lip_pivot])
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    eb.new("JX_Jaw").head = jaw_pivot
    eb["JX_Jaw"].tail = jaw_pivot + Vector((0.0, -3.6, -4.0))
    eb["JX_Jaw"].parent = eb["Bip001Head"]
    eb.new("JX_LipUp").head = lip_pivot
    eb["JX_LipUp"].tail = lip_pivot + Vector((0.0, -1.0, -2.0))
    eb["JX_LipUp"].parent = eb["Bip001Head"]
    lip_line = Vector((0.0, mouth.y, mouth.z))
    eb.new("JX_LipLo").head = lip_line
    eb["JX_LipLo"].tail = lip_line + Vector((0.0, -1.0, -2.0))
    eb["JX_LipLo"].parent = eb["Bip001Head"]
    print("RIG_LIP_LINE", [round(v, 4) for v in lip_line])
    for side, sx in (("L", -1.0), ("R", 1.0)):
        head = Vector((sx * MOUTH_CORNER_X_CM, mouth.y, mouth.z))
        eb.new("JX_MouthCorner_" + side).head = head
        eb["JX_MouthCorner_" + side].tail = head + Vector((sx * 0.8, 0.0, 0.0))
        eb["JX_MouthCorner_" + side].parent = eb["Bip001Head"]
        print("RIG_MOUTH_CORNER", side, [round(v, 4) for v in head])
    for side, c in (("L", eyeL), ("R", eyeR)):
        pivot = _eye_pivot(parts, side)
        print("RIG_EYE_PIVOT", side, [round(v, 4) for v in pivot])
        eb.new("JX_LidUp_" + side).head = c + Vector((0.0, 0.2, 0.0))
        eb["JX_LidUp_" + side].tail = c + Vector((0.0, 0.2, 1.4))
        eb["JX_LidUp_" + side].parent = eb["Bip001Head"]
        eb.new("JX_LidLo_" + side).head = c + Vector((0.0, 0.2, 0.0))
        eb["JX_LidLo_" + side].tail = c + Vector((0.0, 0.2, -1.2))
        eb["JX_LidLo_" + side].parent = eb["Bip001Head"]
        eb.new("JX_Eye_" + side).head = c
        eb["JX_Eye_" + side].tail = c + Vector((0.0, -1.4, 0.0))
        eb["JX_Eye_" + side].parent = eb["Bip001Head"]
    browL = sum((co[i] for i in parts["browL"]), Vector()) / len(parts["browL"])
    browR = sum((co[i] for i in parts["browR"]), Vector()) / len(parts["browR"])
    for side, b in (("L", browL), ("R", browR)):
        eb.new("JX_Brow_" + side).head = b
        eb["JX_Brow_" + side].tail = b + Vector((0.0, 0.0, 0.8))
        eb["JX_Brow_" + side].parent = eb["Bip001Head"]
    # 眉内侧微提绕眉毛最外侧顶点转动：内侧端按臂长抬起，外侧端原地不动
    for side in ("L", "R"):
        idx = parts["brow" + side]
        lat = min(idx, key=lambda i: co[i].x) if side == "L" else max(idx, key=lambda i: co[i].x)
        med = max(idx, key=lambda i: co[i].x) if side == "L" else min(idx, key=lambda i: co[i].x)
        BROW_INNER_PIVOT["JX_Brow_" + side] = co[lat].copy()
        BROW_INNER_ARM["JX_Brow_" + side] = abs(co[lat].x - co[med].x)
        print("RIG_BROW_INNER", side, [round(v, 4) for v in co[lat]], round(BROW_INNER_ARM["JX_Brow_" + side], 4))
    # 内眉骨：把眉内段单独分出来，眉的形态键（内侧上扬/下压）才有第二个自由度
    for side in ("L", "R"):
        idx = parts["brow" + side]
        inner = sorted(idx, key=lambda i: abs(co[i].x))[:max(1, int(len(idx) * BROW_INNER_SHARE))]
        BROW_INNER_SET[side] = set(inner)
        lat_i = min(idx, key=lambda i: co[i].x) if side == "L" else max(idx, key=lambda i: co[i].x)
        med_i = max(idx, key=lambda i: co[i].x) if side == "L" else min(idx, key=lambda i: co[i].x)
        span = abs(co[lat_i].x - co[med_i].x)
        BROW_GRAD[side] = {i: min(1.0, max(0.0, abs(co[i].x - co[med_i].x) / span)) if span > 1e-6 else 1.0
                           for i in idx}
        h = sum((co[i] for i in inner), Vector()) / len(inner)
        eb.new("JX_BrowIn_" + side).head = h
        eb["JX_BrowIn_" + side].tail = h + Vector((0.0, 0.0, 0.8))
        eb["JX_BrowIn_" + side].parent = eb["Bip001Head"]
        print("RIG_BROWIN", side, [round(v, 4) for v in h], len(inner))
    # 颊骨与鼻骨：这两片区域此前没有面骨覆盖，形态键的颊部/鼻部形变只能落在头骨上
    mouth_z = sum(co[i].z for i in parts["mouth_ap"]) / len(parts["mouth_ap"])
    face_idx = _face_vert_indices(mesh)
    mid_z = (eyeL.z + mouth_z) * 0.5
    for side, sx in (("L", -1.0), ("R", 1.0)):
        near = [co[i] for i in face_idx
                if abs(co[i].x - sx * 2.8) < 1.5 and abs(co[i].z - mid_z) < 1.4 and co[i].y < -0.4]
        h = (sum(near, Vector()) / len(near)) if near else Vector((sx * 2.8, -1.4, mid_z))
        eb.new("JX_Cheek_" + side).head = h
        eb["JX_Cheek_" + side].tail = h + Vector((0.0, 0.0, 0.9))
        eb["JX_Cheek_" + side].parent = eb["Bip001Head"]
        print("RIG_CHEEK", side, [round(v, 4) for v in h], len(near))
    nose = [co[i] for i in face_idx
            if abs(co[i].x) < NOSE_HALF_W_CM and co[i].y < -0.9
            and mouth_z + NOSE_Z_CM[0] < co[i].z < mouth_z + NOSE_Z_CM[1]]
    nh = (sum(nose, Vector()) / len(nose)) if nose else Vector((0.0, -2.4, mouth_z + 3.2))
    eb.new("JX_Nose").head = nh
    eb["JX_Nose"].tail = nh + Vector((0.0, 0.0, 0.9))
    eb["JX_Nose"].parent = eb["Bip001Head"]
    print("RIG_NOSE", [round(v, 4) for v in nh], len(nose))
    bpy.ops.object.mode_set(mode='OBJECT')
    for name in FACE_BONES:
        rot = arm.data.bones[name].matrix_local.to_3x3()
        inv = rot.inverted()
        AXES[name] = (inv @ Vector((1.0, 0.0, 0.0))).normalized()
        DIRS[name] = (inv @ Vector((0.0, 0.0, -1.0))).normalized()
    # 眼球绕拟合球心转动：球心在骨局部坐标下固定，骨架整体旋转后由 rest 矩阵还原
    for side in ("L", "R"):
        name = "JX_Eye_" + side
        EYE_PIVOT_LOCAL[name] = arm.data.bones[name].matrix_local.inverted() @ _eye_pivot(parts, side)
    print("RIG_BONES", [b.name for b in arm.data.bones if b.name.startswith("JX_")])
    return parts


def _lip_falloff(x):
    """横向张口权重：口部中线为 1，到唇线半宽 2.4 厘米处收敛为 0。"""
    u = min(1.0, abs(x) / LIP_HALF_W_CM)
    return math.cos(math.pi * 0.5 * u) ** LIP_FALL_POW


def _lip_up_vert(dz):
    """上唇竖向权重：唇线上方 0.30 厘米内恒为 1，到 0.65 厘米收敛为 0。"""
    return _smooth(1.0 - _ramp(dz, LIP_UP_ZONE_CM, LIP_UP_ZONE_CM + LIP_UP_FADE_CM))


def _collect_weights(mesh, parts):
    co = [v.co.copy() for v in mesh.data.vertices]
    eyeL = _eye_center(parts, "L")
    eyeR = _eye_center(parts, "R")
    names = [m.name for m in mesh.data.materials]
    face_slot = names.index("MI_R2T1JinxiMd10011Face")
    eye_slot = names.index("MI_R2T1JinxiMd10011Eye")
    face_verts = set()
    for p in mesh.data.polygons:
        if p.material_index == face_slot:
            face_verts.update(p.vertices)
    mouth_z = sum(co[i].z for i in parts["mouth_ap"]) / len(parts["mouth_ap"])
    w = {}

    def put(vi, bone, weight):
        if weight <= 0.0:
            return
        w.setdefault(vi, {})
        w[vi][bone] = max(w[vi].get(bone, 0.0), min(1.0, weight))

    for vi in face_verts:
        c = co[vi]
        if c.y < 0.8 and c.z < mouth_z + JAW_Z_TOP_CM and abs(c.x) < 6.2 and c.z > JAW_Z_BOTTOM_CM:
            lat = _lip_falloff(c.x)
            dz = c.z - mouth_z
            if dz >= 0.0:
                put(vi, "JX_LipUp", lat * _lip_up_vert(dz))
            else:
                put(vi, "JX_Jaw", lat)
            band = (_smooth(_ramp(abs(c.x), MOUTH_CORNER_BAND_CM[0], MOUTH_CORNER_BAND_CM[1]))
                    * _smooth(1.0 - _ramp(abs(c.x), MOUTH_CORNER_OUTER_CM[0], MOUTH_CORNER_OUTER_CM[1])))
            if band > 0.0 and abs(dz) < MOUTH_CORNER_ZONE_CM:
                put(vi, "JX_MouthCorner_" + ("L" if c.x < 0.0 else "R"), MOUTH_CORNER_WEIGHT * band)
        for side, ctr in (("L", eyeL), ("R", eyeR)):
            d = (c - ctr).length
            dx = c.x - ctr.x
            drop = ctr.z - c.z
            up_mask = (_smooth(1.0 - _ramp(-drop, LID_UP_FULL_ABOVE_CM, LID_UP_FADE_ABOVE_CM))
                       * _smooth(1.0 - _ramp(abs(dx), LID_UP_FULL_W_CM, LID_UP_FADE_W_CM)))
            if up_mask > 0.0 and c.y < -0.8 and c.z > ctr.z - LID_LO_Z_TOP_CM and d < 3.1:
                put(vi, "JX_LidUp_" + side,
                    _smooth(1.0 - _ramp(d, 0.9, 3.1)) * _lid_taper(dx, ctr.x) * up_mask)
            lo_mask = _smooth(1.0 - _ramp(abs(dx), LID_LO_FULL_W_CM, LID_LO_HALF_W_CM))
            if lo_mask > 0.0 and c.y < -0.8 and LID_LO_Z_TOP_CM <= drop <= LID_LO_Z_BOTTOM_CM:
                put(vi, "JX_LidLo_" + side, _smooth(1.0 - _ramp(d, 0.8, 2.2)) * lo_mask)
            # 上/下睑交界共用一条过渡带：两骨权重按 drop 线性混合，
            # 否则眯眼时交界处只有一条零权重缝，会被撕成尖刺
            if c.y < -0.8 and -0.30 <= drop <= 0.55:
                u = min(1.0, max(0.0, (drop + 0.30) / 0.85))
                band = _smooth(1.0 - _ramp(abs(dx), LID_LO_FULL_W_CM, LID_LO_HALF_W_CM))
                if band > 0.0 and d < 3.1:
                    put(vi, "JX_LidUp_" + side, 0.8 * band * (1.0 - u))
                    put(vi, "JX_LidLo_" + side, 0.8 * band * u)
    # 颊部与鼻部：与睑/口遮罩保留一半重叠——完全让位会在骨边界形成 0/1 硬切换，
    # 大位移时被撕开；保留重叠则由归一化自动形成交叉过渡带
    for vi in face_verts:
        c = co[vi]
        have = sum(w[vi].values()) if vi in w else 0.0
        room = 1.0 - 0.5 * have
        ctr = eyeL if c.x < 0.0 else eyeR
        side = "L" if c.x < 0.0 else "R"
        dx = abs(c.x - ctr.x)
        if (c.y < -0.4 and CHEEK_LATERAL_CM[0] <= dx <= CHEEK_LATERAL_CM[1]
                and mouth_z + 1.0 < c.z < ctr.z + 0.6):
            fade = _smooth(1.0 - _ramp(dx, CHEEK_LATERAL_CM[1] - 0.8, CHEEK_LATERAL_CM[1]))
            put(vi, "JX_Cheek_" + side, CHEEK_WEIGHT * fade * room)
        if (abs(c.x) < NOSE_HALF_W_CM and c.y < -0.9
                and mouth_z + NOSE_Z_CM[0] < c.z < mouth_z + NOSE_Z_CM[1]):
            put(vi, "JX_Nose", NOSE_WEIGHT * room)
    for side, ctr in (("L", eyeL), ("R", eyeR)):
        for vi in parts["lash" + side]:
            put(vi, "JX_LidUp_" + side, _lid_taper(co[vi].x - ctr.x, ctr.x))
        for vi in parts["eyeball"][side]["verts"]:
            put(vi, "JX_Eye_" + side, 1.0)
        for vi in parts["brow" + side]:
            u = BROW_GRAD.get(side, {}).get(vi, 1.0)
            put(vi, "JX_BrowIn_" + side, 0.8 * (1.0 - u))
            put(vi, "JX_Brow_" + side, 0.8 * u)
    print("RIG_WEIGHT_VERTS", len(w), "eye_slot_faces", eye_slot)
    return w


def apply_weights(mesh, parts):
    w = _collect_weights(mesh, parts)
    base = {}
    for vi in w:
        base[vi] = [(g.group, g.weight) for g in mesh.data.vertices[vi].groups]
    for vi, add in w.items():
        added = sum(add.values())
        if added > 1.0:
            # 新骨权重按比例压回 1 以内：眉毛与上睑两套区间重叠时总权重会超过 1，
            # 溢出部分会让该顶点比周围多走 23%，在额头一侧形成鼓包
            add = {bone: val / added for bone, val in add.items()}
        up_w = sum(val for bone, val in add.items() if bone.startswith("JX_LidUp_"))
        lo_w = sum(val for bone, val in add.items() if bone.startswith("JX_LidLo_"))
        if up_w > 0.0 or lo_w > 0.0:
            # 静置基准：睑部静置位移按权重烘进绑定网格，眼睑皮肤平滑过渡
            co = mesh.data.vertices[vi].co
            co.z -= up_w * REST_LID_DOWN_CM
            co.z += lo_w * REST_LID_UP_CM
        keep = 1.0 - sum(add.values())
        src = base[vi]
        total = sum(x for _g, x in src)
        for g, x in src:
            mesh.vertex_groups[g].add([vi], (x / total) * keep, 'REPLACE')
        for bone, val in add.items():
            if bone not in mesh.vertex_groups:
                mesh.vertex_groups.new(name=bone)
            mesh.vertex_groups[bone].add([vi], val, 'REPLACE')
    print("RIG_WEIGHTS_APPLIED", len(w))


def _rigid_local(name, rest, angle_deg):
    rot = rest[name].to_3x3()
    m = rest[name] @ Matrix.Rotation(math.radians(angle_deg), 4, AXES[name]) @ rest[name].inverted()
    return m


def _shift_local(name, rest, dist_cm, axis=None):
    """沿世界轴平移：缺省为竖直向下，传入 axis 时按该世界方向；距离单位厘米。"""
    rot = rest[name].to_3x3()
    direction = DIRS[name] if axis is None else (rot.inverted() @ axis).normalized()
    return Matrix.Translation(rot @ (direction * dist_cm))


def _yaw_about_pivot(name, rest, angle_deg):
    """绕拟合球心、绕竖直轴转动：骨头仍在自己位置上，姿态里的平移量把旋转中心挪到球心。"""
    pivot = rest[name] @ EYE_PIVOT_LOCAL[name]
    spin = Matrix.Rotation(math.radians(angle_deg), 4, Vector(EYE_YAW_AXIS))
    return Matrix.Translation(pivot) @ spin @ Matrix.Translation(-pivot)


def _brow_inner(name, dist_cm):
    """绕眉毛外侧端点转动，内侧端抬起 dist_cm：转角取 asin(位移/臂长)，左右两侧转向相反。"""
    angle = math.degrees(math.asin(min(1.0, dist_cm / BROW_INNER_ARM[name])))
    sign = 1.0 if name.endswith("_R") else -1.0
    pivot = BROW_INNER_PIVOT[name]
    spin = Matrix.Rotation(math.radians(sign * angle), 4, Vector((0.0, 1.0, 0.0)))
    return Matrix.Translation(pivot) @ spin @ Matrix.Translation(-pivot)


def pose_face(pose_world, params, rest):
    base = pose_world.get("Bip001Head", rest["Bip001Head"]) @ rest["Bip001Head"].inverted()
    # 面骨默认随头骨静止：新加的面骨没有参数通道，不在这里归位会残留骨架里的旧姿态
    for bone in FACE_BONES:
        pose_world[bone] = base @ rest[bone]
    jaw = params.get("jaw", 0.0)
    jaw_m = base @ _rigid_local("JX_Jaw", rest, JAW_MAX_DEG * jaw)
    pose_world["JX_Jaw"] = jaw_m @ rest["JX_Jaw"]
    # 嘴角骨沿 ±x 外扩：位移随张口系数线性增长，闭口为 0，满额 0.20 厘米
    for side, sx in (("L", -1.0), ("R", 1.0)):
        name = "JX_MouthCorner_" + side
        out = _shift_local(name, rest, sx * CORNER_OUT_CM * jaw, Vector((1.0, 0.0, 0.0)))
        pose_world[name] = base @ out @ rest[name]
    # JX_LipLo 不再承担张口，保持随头骨的静止姿态，通道值为静止局部变换
    pose_world["JX_LipLo"] = base @ rest["JX_LipLo"]
    # 上唇只有嘴唇轻压通道：张口全部来自 JX_Jaw 的旋转与余弦权重衰减，嘴部横向坐标张口前后保持原值
    pose_world["JX_LipUp"] = base @ _shift_local(
        "JX_LipUp", rest, params.get("lip_press", 0.0)) @ rest["JX_LipUp"]
    for side in ("L", "R"):
        blink = params.get("blink_" + side, 0.0)
        gaze = params.get("gaze_" + side, 0.0)
        yaw = params.get("yaw_" + side, 0.0)
        # 上睑行程：眨眼按满行程 BLINK_DOWN_CM，闭眼姿态按 lid 的厘米数直接叠加
        lid = params.get("lid_" + side, 0.0)
        closed = BLINK_DOWN_CM * blink + lid
        drop = closed - params.get("lift_" + side, 0.0)
        up = _shift_local("JX_LidUp_" + side, rest, drop)
        up = Matrix.Translation(rest["JX_LidUp_" + side].to_3x3()
                                @ Vector((0.0, -BLINK_FORWARD_CM * max(0.0, drop) / BLINK_DOWN_CM, 0.0))) @ up
        pose_world["JX_LidUp_" + side] = base @ up @ rest["JX_LidUp_" + side]
        lo = _shift_local("JX_LidLo_" + side, rest, -closed * LOWER_LID_RATIO)
        pose_world["JX_LidLo_" + side] = base @ lo @ rest["JX_LidLo_" + side]
        eye = _yaw_about_pivot("JX_Eye_" + side, rest, yaw) @ _rigid_local(
            "JX_Eye_" + side, rest, GAZE_MAX_DEG * gaze + params.get("gaze_deg_" + side, 0.0))
        pose_world["JX_Eye_" + side] = base @ eye @ rest["JX_Eye_" + side]
        brow = _shift_local("JX_Brow_" + side, rest, -BROW_UP_CM * params.get("brow_" + side, 0.0))
        inner = _brow_inner("JX_Brow_" + side, params.get("browin_" + side, 0.0))
        pose_world["JX_Brow_" + side] = base @ inner @ brow @ rest["JX_Brow_" + side]
        # 内眉骨共用同一套世界变换，眉的骨驱动不被拆分影响，形态键侧则多一个自由度
        pose_world["JX_BrowIn_" + side] = base @ inner @ brow @ rest["JX_BrowIn_" + side]

