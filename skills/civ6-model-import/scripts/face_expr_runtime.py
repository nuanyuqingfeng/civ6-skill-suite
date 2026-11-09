#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""表情运行时层：官方逐帧权重表 → blink 通道 / 长短闭眼分层 / 互补混合 /
下睑保底 / 合成后限幅 / 口型与眉部让位。

实现逐行为等价移植自御三家已验证链（ysj2_morph.py:282-411、ysj2_face.py:375-462），
常量与骨名前缀参数化；与项目侧的差异只有参数来源（configure / set_code）。

铁律（references/expression-route.md、blink-and-eyelids.md §二）：
  1) E_Close 的逐帧权重绝不进入 morph_fit.pose() 拟合层——它 delta 约 1cm、
     被分摊 6 骨，走拟合层 LidUp 只有约 0.4 倍行程（半闭）、LidLo 反向
     （实测 0.659cm vs 应有 1.549cm）。本模块的 expression_weights() 硬性剔除
     E_Close，由 curve_blink() 注入 blink 通道做完整闭眼。
  2) 同一帧同一眼睑只允许一条通路主导：姿态层（blink 通道）先算，
     形态键拟合层做残差，之后 ensure_lid_close 补下睑、clamp_lids 统一限幅。

调用顺序（ysj2_anim.py 帧循环同款）：
  pose_face(...)            # 项目侧姿态层（blink 通道在这里消费 curve_blink 的值）
  morph_fit.pose(...)       # 项目侧形态键拟合层（表已由 expression_weights 剔除 E_Close）
  ensure_lid_close(...)     # 下睑保底（只补不足）
  clamp_lids(...)           # 合成后限幅（放最后）
"""
import math

try:
    from mathutils import Matrix, Vector
except ImportError:            # 离线自检（无 Blender）时才允许桩
    Matrix = Vector = None

# ---- 长短闭眼分层阈值（P0 数值口径，不得擅改）----
EXPRESSION_CLOSE_MIN_LEN = 20   # 官方短眨眼脉冲最长 15 帧；>20 帧按表情性闭合复刻
EXPRESSION_CLOSE_MIN_W = 0.02
BLINK_PEAK_MIN = 0.05           # 整段峰值低于此 = 官方没有眨眼，交回人工 blink_plan
MANUAL_GAIN = 0.55              # 人工预置层降权系数（互补混合）
CURVE_EPS = 1e-4
# 2026-11-06 用户点名授权的口径变更（仅新领袖启用，御三家默认 False 不受影响）：
# True 时官方短脉冲不再交回 blink_plan，与长闭眼一样按官方逐帧权重驱动 blink 通道；
# 官方非活跃帧仍由 blink_plan 补位（保持密度、无双重叠加）。
SHORT_PULSES_DRIVE = False

# ---- 眼睑几何常量（与 ysj2_face.py 逐值一致）----
LOWER_LID_RATIO = 0.40
BLINK_FORWARD_CM = 0.10
LID_CLAMP_UP = 1.18
LID_CLAMP_LO = 1.80
LID_LO_MIN_RATIO = 0.75
BLINK_FALLBACK_GAIN = 0.60      # 保护窗外人工眨眼补位降权（御三家同值）

_VISEMES = frozenset(("Aa", "A", "E", "I", "O", "U"))

_CODE = "LEAD"
_BLINK_DOWN_CM = 1.55           # configure(blink_down_cm) 覆盖；0.75 * eye_v
_CURVE_TABLES = {}
_PARTS = None


def set_code(code):
    global _CODE
    _CODE = code


def configure(blink_down_cm):
    """blink_down_cm = 0.75 * eye_v（御三家实测 1.462/1.520/1.187）。"""
    global _BLINK_DOWN_CM
    _BLINK_DOWN_CM = float(blink_down_cm)


def bone(suffix):
    return "%s_%s" % (_CODE, suffix)


# ---------------------------------------------------------------------------
# 权重表注入与 E_Close 长短分层（等价 ysj2_morph.set_curve_tables/_close_segments）
# ---------------------------------------------------------------------------
def set_short_pulses_drive(flag):
    """2026-11-06 用户点名授权：官方短脉冲接管眨眼（新领袖 True，御三家 False）。"""
    global SHORT_PULSES_DRIVE
    SHORT_PULSES_DRIVE = bool(flag)


def _close_segments(t):
    """把 E_Close 轨迹拆成「短眨眼脉冲」与「表情性闭合」两类连续段。

    SHORT_PULSES_DRIVE=True 时全部段进入表情性闭合（短脉冲按官方逐帧权重
    驱动 blink 通道）；False 维持御三家口径（短脉冲交回 blink_plan）。"""
    col = t.get("_blink_col")
    if col is None:
        return [], []
    vals = [r[col] for r in t["frames"]]
    segs, start = [], None
    for i, v in enumerate(vals + [0.0]):
        if v > EXPRESSION_CLOSE_MIN_W and start is None:
            start = i
        elif v <= EXPRESSION_CLOSE_MIN_W and start is not None:
            segs.append((start, i))
            start = None
    blinks = [(a, b) for a, b in segs if b - a <= EXPRESSION_CLOSE_MIN_LEN]
    expr = list(segs) if SHORT_PULSES_DRIVE else \
        [(a, b) for a, b in segs if b - a > EXPRESSION_CLOSE_MIN_LEN]
    return blinks, expr


def set_curve_tables(tables):
    """注入 {完整片段名: 权重表}，并预计算 E_Close 列与表情性闭合段。

    权重表本身保留 E_Close 列（morph_curves.py 不剔除），剔除发生在
    expression_weights() 的返回值里——保证 blink 通道是唯一消费者。"""
    global _CURVE_TABLES
    _CURVE_TABLES = tables or {}
    for clip in sorted(_CURVE_TABLES):
        t = _CURVE_TABLES[clip]
        col = t["morphs"].index("E_Close") if "E_Close" in t["morphs"] else None
        t["_blink_col"] = col
        n = len(t["frames"])
        close = [0.0] * n
        blinks, expr = _close_segments(t)
        if col is not None:
            vals = [r[col] for r in t["frames"]]
            for a, b in expr:
                for j in range(a, b):
                    close[j] = vals[j]
        t["_expression_close"] = close
        print("MORPH_CURVES", clip, "frames", n,
              "morphs", len(t["morphs"]), "peak", t.get("peak", 0.0),
              "blink_peak", t.get("blink_peak", 0.0),
              "blink_pulses", len(blinks),
              "expression_close", [(a + 1, b, round(max(close[a:b]), 2)) for a, b in expr])


def has_curve_table(clip):
    return clip in _CURVE_TABLES


def curve_blink(clip, frame, total, manual_blink=0.0):
    """官方 E_Close 的**表情性闭合**关键帧 → blink 通道（完整闭眼行程）。

    返回 None = 该帧完全交还项目原有 blink_plan（短脉冲与无曲线段）。
    分层口径：>20 帧的闭合段按官方逐帧权重忠实复刻（演出的一部分）；
    整段 blink_peak < BLINK_PEAK_MIN 或 f > source 的冻结段同样交回人工，
    避免「瞪眼数秒」。
    """
    t = _CURVE_TABLES.get(clip)
    if t is None:
        return None
    if t.get("blink_peak", 1.0) < BLINK_PEAK_MIN:
        return None
    close = t.get("_expression_close")
    if close is None:
        return None
    f = int(frame)
    source = min(t.get("source", len(close)), total)
    if f < 1 or f > source or f > len(close):
        return None
    w = close[f - 1]
    if w > EXPRESSION_CLOSE_MIN_W:
        return max(w, manual_blink)
    return None


def blink_protected(clip, frame):
    """官方短脉冲 ±10 帧保护窗内返回 True（人工补位在此窗内让位/降权）。"""
    t = _CURVE_TABLES.get(clip)
    if t is None:
        return False
    col = t.get("_blink_col")
    if col is None:
        return False
    f = int(frame)
    rows = t["frames"]
    lo = max(0, f - 11)
    hi = min(len(rows), f + 10)
    return any(rows[j][col] > EXPRESSION_CLOSE_MIN_W for j in range(lo, hi))


# ---------------------------------------------------------------------------
# 曲线为底 + 人工层互补混合（等价 ysj2_morph.expression_weights/_manual_weights）
# ---------------------------------------------------------------------------
def blend_complementary(a, b):
    """1-(1-a)(1-b)：结果天然 ≤1，同键叠加不溢出；单边出现时等价直接采用。"""
    return 1.0 - (1.0 - a) * (1.0 - b)


def manual_weights(clip, frame, total, presets, expressions, gain=MANUAL_GAIN):
    """人工 PRESETS/EXPRESSIONS 时间窗 ramp × gain。presets: {clip后缀: [(preset,(lo,hi))]}，
    (lo,hi) 为占 total 的比例，与御三家 ysj2_morph._manual_weights 同口径。"""
    out = {}
    for preset, (lo, hi) in presets.get(clip.split("_", 1)[1], ()):
        w = _ramp(frame, lo, hi, total) * gain
        if w <= 0.0:
            continue
        for morph, base in expressions[preset].items():
            out[morph] = max(out.get(morph, 0.0), base * w)
    return out


def _ramp(frame, lo, hi, total):
    """smoothstep 时间窗（逐行等价 ysj2_morph._ramp，勿改口径）。"""
    start = lo * total
    end = hi * total
    edge = max(1.0, 0.08 * total)
    if frame <= start or frame > end:
        return 0.0
    t = 1.0
    if frame < start + edge:
        t = (frame - start) / edge
    elif frame > end - edge:
        t = (end - frame) / edge
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def expression_weights(clip, frame, total, presets, expressions):
    """曲线为底、人工层 MANUAL_GAIN 降权互补混合；**硬性剔除 E_Close**。

    E_Close 只允许 curve_blink() → blink 通道消费（铁律 2）。"""
    table = _CURVE_TABLES.get(clip)
    if table is None:
        return manual_weights(clip, frame, total, presets, expressions)
    f = int(frame)
    rows = table["frames"]
    if f < 1 or f > len(rows):
        return {}
    out = {n: w for n, w in zip(table["morphs"], rows[f - 1])
           if w > CURVE_EPS and n != "E_Close"}
    for n, w in manual_weights(clip, frame, total, presets, expressions).items():
        out[n] = blend_complementary(out.get(n, 0.0), w)
    return {n: w for n, w in out.items() if w > CURVE_EPS}


def takes_over_brow(clip, frame, total, presets, expressions):
    """曲线层 B_* 有权重时，骨驱动眉高让位（避免同骨双重驱动）。"""
    return any(w > CURVE_EPS for n, w in
               expression_weights(clip, frame, total, presets, expressions).items()
               if n.startswith("B_"))


def takes_over_jaw(clip, frame, total, presets, expressions):
    """官方口型（元音 VISEMES）有权重的帧，Jaw 语音包络让位。

    只在官方口型关键帧触发，不做任何语音适配/音素对齐/时长拉伸。"""
    return any(w > CURVE_EPS for n, w in
               expression_weights(clip, frame, total, presets, expressions).items()
               if n in _VISEMES)


# ---------------------------------------------------------------------------
# 眼睑合成（等价 ysj2_face.py ensure_lid_close / clamp_lids，BLINK_DOWN_CM 参数化）
# ---------------------------------------------------------------------------
def ensure_lid_close(pose_world, rest, blink, blink_down_cm=None,
                     lower_lid_ratio=LOWER_LID_RATIO, lo_min_ratio=LID_LO_MIN_RATIO):
    """blink 明确要求闭眼时，保证下眼睑世界 +Z 抬升 ≥ 行程×0.40×blink×0.75。

    只补不足，已满足的片段零改动；上限由 clamp_lids 兜住。"""
    if blink <= 0.05:
        return
    bd = blink_down_cm if blink_down_cm is not None else _BLINK_DOWN_CM
    head_rest = rest.get("Bip001Head")
    if head_rest is None:
        return
    base = pose_world.get("Bip001Head", head_rest) @ head_rest.inverted()
    need = bd * lower_lid_ratio * blink * lo_min_ratio
    for side in ("L", "R"):
        name = bone("LidLo_" + side)
        m = pose_world.get(name)
        if m is None:
            continue
        ref = (base @ rest[name]).translation
        dz = m.translation.z - ref.z
        if dz < need:
            m.translation = m.translation + Vector((0.0, 0.0, need - dz))


def clamp_lids(pose_world, rest, blink_down_cm=None,
               lower_lid_ratio=LOWER_LID_RATIO, up_mul=LID_CLAMP_UP, lo_mul=LID_CLAMP_LO):
    """形态键拟合层叠加之后，裁剪眼睑骨相对 rest 的总位移（方向不变）。

    必须在 pose_face() 与 morph_fit.pose() 都执行完之后调用。"""
    bd = blink_down_cm if blink_down_cm is not None else _BLINK_DOWN_CM
    head_rest = rest.get("Bip001Head")
    if head_rest is None:
        return
    base = pose_world.get("Bip001Head", head_rest) @ head_rest.inverted()
    limits = ((bone("LidUp_"), bd * up_mul),
              (bone("LidLo_"), bd * lower_lid_ratio * lo_mul))
    for prefix, limit in limits:
        for side in ("L", "R"):
            m = pose_world.get(prefix + side)
            if m is None:
                continue
            ref = (base @ rest[prefix + side]).translation.copy()
            delta = m.translation - ref
            length = math.sqrt(delta.x ** 2 + delta.y ** 2 + delta.z ** 2)
            if length > limit:
                m.translation = ref + delta * (limit / length)
