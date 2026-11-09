"""把《鸣潮》RibbonAnim 二次运动层完整叠加到今汐的七段动画。

Rib 轨道存的是相对 RefPose 的绝对局部姿态（见 workspace/gen/reports/
ribbon_additive_semantics.md）。本工程基座发丝恒为 RefPose，因此 Rib 的局部旋转
可直接覆盖全部发丝骨骼（31 根 Bone_Hair*）的旋转轨道，按源数据 1:1 播放，不再做
增益缩放或逐节整形。
"""
import math
import os

import bpy
from mathutils import Quaternion, Vector

RIB_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\rib"

CHAINS = (
    ("Bone_Hair009_L", "Bone_Hair010_L", "Bone_Hair011_L", "Bone_Hair012_L",
     "Bone_Hair013_L", "Bone_Hair015_L", "Bone_Hair016_L", "Bone_Hair017_L"),
    ("Bone_Hair019_R", "Bone_Hair020_R", "Bone_Hair021_R", "Bone_Hair022_R",
     "Bone_Hair023_R", "Bone_Hair025_R", "Bone_Hair026_R", "Bone_Hair027_R"),
)
CHAIN_BONES = tuple(name for chain in CHAINS for name in chain)
HEAD_BONE = "Bip001Head"
HAIR_PREFIX = "Bone_Hair"

_IDLE_PERIOD = 240
_IDLE_LOOPS_BEFORE = 2
_IDLE_TRANSITION = 56
_INSERT_RANGE = (80, 380)


def action_by_name(name):
    for act in bpy.data.actions:
        if act.name == name:
            return act
        # ueanim 导入器偶尔追加后缀
        if act.name.startswith(name + ".") and act.name[len(name) + 1:].isdigit():
            return act
    return None


def import_actions(arm, names):
    """导入 Rib ueanim，返回 {action_name: action}。"""
    missing = [n for n in names if action_by_name(n) is None]
    if missing:
        files = [{"name": n + ".ueanim"} for n in missing]
        before = set(a.name for a in bpy.data.actions)
        bpy.ops.object.select_all(action='DESELECT')
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.uf.import_ueanim(directory=RIB_DIR, files=files)
        after = set(a.name for a in bpy.data.actions)
        print("RIB_IMPORT", sorted(after - before))
    out = {}
    for n in names:
        act = action_by_name(n)
        assert act is not None, "RIB_ACTION_MISSING " + n
        out[n] = act
    return out


_CURVE_CACHE = {}


def _rot_fcurves(action, bone):
    key = (action.name, bone)
    cached = _CURVE_CACHE.get(key)
    if cached is not None:
        return cached
    path = 'pose.bones["%s"].rotation_quaternion' % bone
    curves = {}
    for fc in action.fcurves:
        if fc.data_path == path:
            curves[fc.array_index] = fc
    _CURVE_CACHE[key] = curves
    return curves


def _eval_quat(action, bone, frame):
    curves = _rot_fcurves(action, bone)
    if len(curves) < 4:
        return Quaternion()
    # Blender 的 rotation_quaternion 通道序为 0=w, 1=x, 2=y, 3=z
    q = Quaternion((curves[0].evaluate(frame),
                    curves[1].evaluate(frame),
                    curves[2].evaluate(frame),
                    curves[3].evaluate(frame)))
    if q.magnitude < 1e-8:
        return Quaternion()
    return q.normalized()


def _action_first(action):
    return int(round(action.frame_range[0]))


def _action_len(action):
    return max(1, int(round(action.frame_range[1] - action.frame_range[0])))


def _q_neg(q):
    return Quaternion((-q.w, -q.x, -q.y, -q.z))


def _slerp(a, b, t):
    if a.dot(b) < 0.0:
        b = _q_neg(b)
    return a.slerp(b, t)


def _idle_map(frame):
    """返回 ('single', rib_action, frame) 或 ('blend', a, fa, b, fb, t)。"""
    head = _IDLE_PERIOD * _IDLE_LOOPS_BEFORE
    trans = _IDLE_TRANSITION
    insert_len = _INSERT_RANGE[1] - _INSERT_RANGE[0] + 1
    if frame <= head:
        return ("single", "Rib_Ui_Nature_Loop",
                _action_first(action_by_name("Rib_Ui_Nature_Loop")) + (frame - 1) % _IDLE_PERIOD)
    if frame <= head + trans:
        t = (frame - head) / float(trans)
        return ("blend", "Rib_Ui_Nature_Loop",
                _action_first(action_by_name("Rib_Ui_Nature_Loop")) + _IDLE_PERIOD - 1,
                "Rib_Stand1_Action01",
                _action_first(action_by_name("Rib_Stand1_Action01")) + _INSERT_RANGE[0] - 1,
                t)
    if frame <= head + trans + insert_len:
        local = frame - (head + trans + 1)
        return ("single", "Rib_Stand1_Action01",
                _action_first(action_by_name("Rib_Stand1_Action01")) + _INSERT_RANGE[0] + local)
    tail = head + trans + insert_len
    if frame <= tail + trans:
        t = (frame - tail) / float(trans)
        return ("blend", "Rib_Stand1_Action01",
                _action_first(action_by_name("Rib_Stand1_Action01")) + _INSERT_RANGE[1],
                "Rib_Ui_Nature_Loop",
                _action_first(action_by_name("Rib_Ui_Nature_Loop")),
                t)
    return ("single", "Rib_Ui_Nature_Loop",
            _action_first(action_by_name("Rib_Ui_Nature_Loop")) + (frame - tail - trans - 1) % _IDLE_PERIOD)


def _clip_map(frame, segments):
    """按 compose_on_a 的 NLA 条带口径映射：段长取 action.frame_range 差。"""
    offset = frame - 1
    last = None
    for base, repeat in segments:
        base_action = action_by_name(base)
        assert base_action is not None, "BASE_ACTION_MISSING " + base
        length = _action_len(base_action)
        block = length * repeat
        rib = action_by_name("Rib_" + base)
        assert rib is not None, "RIB_MISSING " + base
        last = (rib, length)
        if offset < block:
            local = offset % length
            return ("single", rib.name, _action_first(rib) + local)
        offset -= block
    # 超过源长度：保持最后一帧
    rib, length = last
    return ("single", rib.name, _action_first(rib) + length - 1)


def _raw_quats(mapping, frame, bones):
    if mapping[0] == "single":
        _, act_name, rib_frame = mapping
        act = action_by_name(act_name)
        out = {}
        for bone in bones:
            if len(_rot_fcurves(act, bone)) >= 4:
                out[bone] = _eval_quat(act, bone, rib_frame)
        return out
    _, a_name, fa, b_name, fb, t = mapping
    a_act = action_by_name(a_name)
    b_act = action_by_name(b_name)
    out = {}
    for bone in bones:
        if len(_rot_fcurves(a_act, bone)) < 4 or len(_rot_fcurves(b_act, bone)) < 4:
            continue
        qa = _eval_quat(a_act, bone, fa)
        qb = _eval_quat(b_act, bone, fb)
        out[bone] = _slerp(qa, qb, t)
    return out


def _build_series(arm, action, clip, total, segments, bones, q_ref, window=None, damp=None, ramp=60):
    mapping_fn = (lambda f: _idle_map(f)) if clip == "JX_IDLE" else (lambda f: _clip_map(f, segments))
    series = {}
    bend = {}
    prev = {}
    # 减幅基准取"常态段"的均值姿态：单帧做基准会让减幅后的整理姿态整体偏移，
    # 均值做基准才能只砍摆幅、不改中位，窗口边缘再平滑过渡回 1.0
    ref_src = {}
    if damp is not None and window is not None:
        acc = {}
        for frame in range(1, max(2, window[0])):
            for bone, q in _raw_quats(mapping_fn(frame), frame, bones).items():
                q = q.normalized()
                if bone in acc:
                    if acc[bone].dot(q) < 0.0:
                        q = _q_neg(q)
                    acc[bone] += q
                else:
                    acc[bone] = q.copy()
        ref_src = {bone: (q.normalized() if q.magnitude > 1e-8 else Quaternion())
                   for bone, q in acc.items()}
    for frame in range(1, total + 1):
        raw = _raw_quats(mapping_fn(frame), frame, bones)
        for bone in bones:
            if bone not in raw:
                continue
            q = raw[bone].normalized()
            if damp is not None and window is not None and bone in ref_src:
                # 思考窗口外把相对源首帧的姿态偏移按 damp 缩放，窗口边缘平滑过渡回 1.0，
                # 既压幅度又不破坏与思考段的衔接
                if frame < window[0]:
                    s = damp + (1.0 - damp) * max(0.0, 1.0 - (window[0] - frame) / float(ramp))
                elif frame > window[1]:
                    s = damp + (1.0 - damp) * max(0.0, 1.0 - (frame - window[1]) / float(ramp))
                else:
                    s = 1.0
                if s < 1.0:
                    d = (ref_src[bone].inverted() @ q).normalized()
                    if d.w < 0.0:
                        # 四元数双覆盖：不先取短弧会把 >180° 的偏移当成大角度，
                        # 折半后反而变成另一个方向的整圈旋转，发丝会被甩飞
                        d = _q_neg(d)
                    axis, angle = d.to_axis_angle()
                    q = (ref_src[bone] @ Quaternion(axis, angle * s)).normalized()
            delta = (q_ref[bone].inverted() @ q).normalized()
            if delta.w < 0.0:
                delta = _q_neg(delta)
            bend.setdefault(bone, {})[frame] = math.degrees(
                2.0 * math.acos(min(1.0, abs(delta.w))))
            qout = q
            if bone in prev and qout.dot(prev[bone]) < 0.0:
                qout = _q_neg(qout)
            prev[bone] = qout
            series.setdefault(bone, {})[frame] = qout
    return series, bend


def _write_series(action, series, total):
    for bone, frames in series.items():
        path = 'pose.bones["%s"].rotation_quaternion' % bone
        for fc in [c for c in action.fcurves if c.data_path == path]:
            action.fcurves.remove(fc)
        for index in range(4):
            fc = action.fcurves.new(path, index=index, action_group=bone)
            fc.keyframe_points.add(total)
            for kp, frame in zip(fc.keyframe_points, range(1, total + 1)):
                kp.co = (float(frame), frames[frame][index])
                kp.interpolation = 'LINEAR'
            fc.update()


def _sample_heads(arm, action, total):
    """返回逐帧发丝骨位置（头部局部系，剔除身体摆动的影响）。"""
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = action
    scene = bpy.context.scene
    out = []
    for frame in range(1, total + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        ref = arm.pose.bones[HEAD_BONE].matrix.copy()
        out.append({bone: (ref.inverted() @ arm.pose.bones[bone].head).copy()
                    for bone in CHAIN_BONES})
    return out


def _amplitude(actual, frames):
    """逐节摆动幅度（cm）：相对窗口内平均姿态的最大位移。"""
    frames = list(frames)
    out = {}
    for bone in CHAIN_BONES:
        xs = [actual[f - 1][bone] for f in frames]
        mean = sum(xs, Vector()) / len(xs)
        out[bone] = max((p - mean).length for p in xs)
    return out


def _bend_swing(bend, frames):
    frames = list(frames)
    return {bone: max(bend[bone][f] for f in frames) - min(bend[bone][f] for f in frames)
            for bone in CHAIN_BONES}


def overlay(arm, action, clip, total, segments, window=None, damp=None):
    """把 Rib 发丝层完整写入源动作的 rotation_quaternion。返回摆动幅度诊断。"""
    bones = sorted(b.name for b in arm.data.bones if b.name.startswith(HAIR_PREFIX))
    assert len(bones) == 31, bones
    q_ref = {bone: _eval_quat(action, bone, 1) for bone in bones}

    series, bend = _build_series(arm, action, clip, total, segments, bones, q_ref, window, damp)
    _write_series(action, series, total)
    print("RIB_BONES", clip, len(bones), len(series))
    actual = _sample_heads(arm, action, total)
    disp = _amplitude(actual, range(1, total + 1))
    print("RIB_AMP", clip,
          " ".join("%s=%.1f" % (b.replace("Bone_Hair", "H"), disp[b]) for b in CHAINS[0])
          + " | " + " ".join("%.1f" % disp[b] for b in CHAINS[1]))
    if window is not None:
        head_frames = range(1, window[0])
        head = _amplitude(actual, head_frames)
        print("RIB_AMP_HEAD", clip,
              " ".join("%s=%.1f" % (b.replace("Bone_Hair", "H"), head[b]) for b in CHAINS[0])
              + " | " + " ".join("%.1f" % head[b] for b in CHAINS[1]))
        think_frames = range(window[0], window[1] + 1)
        think = _amplitude(actual, think_frames)
        swing = _bend_swing(bend, think_frames)
        print("RIB_AMP_THINK", clip,
              " ".join("%s=%.1f" % (b.replace("Bone_Hair", "H"), think[b]) for b in CHAINS[0])
              + " | " + " ".join("%.1f" % think[b] for b in CHAINS[1]))
        print("RIB_BEND_THINK", clip,
              " ".join("%.1f" % swing[b] for b in CHAINS[0])
              + " | " + " ".join("%.1f" % swing[b] for b in CHAINS[1]))
    return disp
