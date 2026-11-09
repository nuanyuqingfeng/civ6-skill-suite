import json
import math
import os

ENVELOPE = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\reports\round3_voice_envelope.json"

# 待机时间线共 1101 帧：1…480 两轮待机、481…520 进入过渡、521…821 插入的待机动作1（源条带第 80…380 帧）、
# 822…861 退出过渡、862…1101 一轮待机；下列帧号与关键帧都按这条时间线编号
BLINKS = {
    # 思考段另加 5 次，其中 626／632 相隔 6 帧构成一次连眨
    "JX_IDLE": [90, 300, 312, 508, 552, 596, 626, 632, 940, 1020],
    "JX_FirstMeet": [26, 96, 168],
    "JX_DeclareWarHuman": [32, 112],
    "JX_DeclareWarAI": [30, 118, 220, 300],
    "JX_Kudos": [],
    "JX_Warning": [26, 96],
    "JX_Defeat": [45, 132, 138, 202],
}

GAZES = {
    "JX_IDLE": [(64, 104, 0.75), (152, 196, -0.85), (880, 920, -0.55), (1000, 1060, 0.4)],
}

# 眼球水平转动：关键帧之间按 smoothstep 插值，角度单位是度，正值转向 +Y（画面右侧），
# 负值转向 -Y（画面左侧，即模型自身右侧）。待机段 226 起先向左 12 度停 18 帧（0.6 秒），
# 再用 10 帧转到右侧 12 度停 24 帧（0.8 秒），末 12 帧（0.4 秒）回到中位，随后是 300／312 的连眨；
# 641…672 段对应插入的待机动作1第 200…231 帧，第 649 帧（源条带第 208 帧）抬头发现有人。
YAW_KEYS = {
    "JX_IDLE": [(226, 0.0), (236, -12.0), (254, -12.0), (264, 12.0), (288, 12.0), (300, 0.0),
                (641, 0.0), (649, -10.0), (664, -10.0), (672, 0.0)],
}

# 祈愿闭眼：上睑下落 0.9 厘米（与眨眼同量级），进入与退出各 8 帧 smoothstep
LID_CLOSED_CM = 0.9
LID_WINDOWS = {"JX_Kudos": (133, 141, 371, 379)}

BROW = {
    "JX_DeclareWarHuman": -0.55,
    "JX_DeclareWarAI": -0.6,
    "JX_Warning": -0.45,
    "JX_Kudos": 0.55,
    "JX_FirstMeet": 0.25,
}

# 思考段：插入的待机动作1 在时间线上第 491…640 帧，首尾各 10 帧淡入淡出；
# 第 641…648 帧留给既有的抬头发现有人，第 649 帧（源条带第 208 帧）进入惊讶，
# 惊讶反应 649…665 共 17 帧，之后 666…675 用 10 帧回到待机表情
THINK_START = 491
THINK_END = 640
THINK_FADE = 10
SURPRISE_START = 649
SURPRISE_END = 665
SURPRISE_RETURN = 10
# 目光偏移：(起帧, 止帧, 水平角, 俯仰角)，单位为度；四次方向互不重复，合成角 4.47…7.21 度
THINK_GAZE = (
    (501, 523, -6.0, 4.0),
    (531, 557, 6.0, 3.0),
    (565, 589, 0.0, 7.0),
    (597, 621, -4.0, -2.0),
)
# 眉内侧微提：(起帧, 止帧, 内端位移厘米)
THINK_BROW_IN = ((503, 535, 0.030), (541, 573, 0.036), (579, 611, 0.024), (615, 636, 0.030))
# 嘴唇轻压：(起帧, 止帧, 上唇下压厘米)
THINK_LIP = ((505, 545, 0.016), (551, 597, 0.020), (603, 635, 0.014))
# 惊讶段关键帧：眉整体上提（通道值，0.75 对应骨位移 0.075 厘米）、上睑抬起（厘米）、下颌张开（口型通道值）
SURPRISE_BROW = ((648, 0.0), (651, 0.75), (656, 0.75), (662, 0.15), (665, 0.0))
SURPRISE_LIFT = ((648, 0.0), (650, 0.055), (654, 0.055), (660, 0.010), (665, 0.0))
SURPRISE_JAW = ((648, 0.0), (651, 0.25), (654, 0.18), (658, 0.0), (665, 0.0))

BLINK_CLOSE = 2.0
BLINK_HOLD = 1.0
BLINK_OPEN = 3.0


FPS = 30
# 语音起始时刻取自 .ast 的 m_fStartTime：04_KUDOS 为 1.300000 s（第 40 帧），其余段为 0.500000 s（第 16 帧）；
# 帧号从 1 开始，故语音首帧 = 1 + 偏移帧，结束帧 = 偏移帧 + ceil(时长×30)
VOICE_OFFSET_FRAMES = {"JX_Kudos": 39}
VOICE_OFFSET_DEFAULT = 15
# 活动区间首尾各 4 帧淡入淡出
FADE_FRAMES = 4


SPEECH_LEVELS = (0.0, 0.45, 1.0)
SPEECH_GATE = 0.12
SPEECH_GAMMA = 1.7
SPEECH_HOLD = 3
SPEECH_HYSTERESIS = 0.15


def _percentile(values, q):
    ordered = sorted(values)
    if not ordered:
        return 1.0
    idx = min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))
    return ordered[idx] or 1.0


def shape_speech(frames):
    """把逐帧响度压成口型曲线：归一、噪声门、伽马、平滑、保持、量化。"""
    keys = sorted(frames)
    if not keys:
        return frames
    peak = _percentile([frames[k] for k in keys], 0.95)
    norm = {k: max(0.0, min(1.0, frames[k] / peak)) for k in keys}

    gated = {k: (0.0 if v < SPEECH_GATE else v) for k, v in norm.items()}
    curved = {k: (0.0 if v <= 0.0 else (v - SPEECH_GATE) / (1.0 - SPEECH_GATE)) for k, v in gated.items()}
    curved = {k: v ** SPEECH_GAMMA for k, v in curved.items()}

    kernel = (1.0, 4.0, 6.0, 4.0, 1.0)
    weight = sum(kernel)
    smoothed = {}
    for i, k in enumerate(keys):
        acc = 0.0
        for offset, w in zip(range(-2, 3), kernel):
            j = i + offset
            if 0 <= j < len(keys):
                acc += curved[keys[j]] * w
        smoothed[k] = acc / weight

    span = 12
    activity = {}
    for i, k in enumerate(keys):
        lo = max(0, i - span // 2)
        hi = min(len(keys), i + span // 2 + 1)
        activity[k] = sum(norm[keys[j]] for j in range(lo, hi)) / (hi - lo)

    held = {}
    hold_until = -1
    hold_value = 0.0
    for k in keys:
        if k <= hold_until:
            held[k] = hold_value
            continue
        value = smoothed[k]
        if activity[k] < 0.18:
            level = 0.0
        elif value < 0.55:
            level = 0.35
        elif value < 0.82:
            level = 0.6
        else:
            level = 1.0
        if abs(level - hold_value) > 0.05:
            hold_until = k + SPEECH_HOLD
            hold_value = level
        held[k] = hold_value
    return held


def _transitions(frames):
    keys = sorted(frames)
    count = 0
    for prev, cur in zip(keys, keys[1:]):
        if (frames[prev] > 0.0) != (frames[cur] > 0.0):
            count += 1
    return count


def voice_ends(path=ENVELOPE):
    """各段语音在动画帧坐标上的结束帧：起始偏移帧 + ceil(时长 × 30)。"""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    ends = {}
    for entry in data["entries"]:
        length = int(math.ceil(entry["duration_s"] * FPS))
        if length > 0:
            ends[entry["action"]] = VOICE_OFFSET_FRAMES.get(
                entry["action"], VOICE_OFFSET_DEFAULT) + length
    return ends


def _fill_to_voice(frames, voice_end):
    """包络表被截断在语音中段时，把已有的活动区间线性铺到语音结束帧。
    表格末个非零帧早于语音结束帧即判定为截断（JX_Defeat 表止于帧 69，语音到帧 152）。"""
    loud = [k for k in sorted(frames) if frames[k] > 0.0]
    if not loud or loud[-1] >= voice_end:
        return frames
    start, last = loud[0], loud[-1]
    span = last - start
    width = voice_end - start
    filled = {}
    for i in range(width + 1):
        pos = start + span * i / width
        lo = int(math.floor(pos))
        hi = min(last, lo + 1)
        frac = pos - lo
        filled[start + i] = frames[lo] * (1.0 - frac) + frames[hi] * frac
    return filled


def _fade_edges(frames, start, end):
    """活动区间首尾各 4 帧线性淡入淡出。"""
    for i in range(FADE_FRAMES):
        frames[start + i] *= (i + 1) / FADE_FRAMES
        frames[end - i] *= (i + 1) / FADE_FRAMES


def load_envelope(path=ENVELOPE, action_frames=None):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    ends = voice_ends(path)
    table = {}
    for entry in data["entries"]:
        action = entry["action"]
        total = entry["frames"] if action_frames is None else action_frames[action]
        total = max(total, ends.get(action, 0))
        raw = {int(k): float(v) for k, v in entry["envelope"].items()}
        shaped = shape_speech(raw)
        if action in ends:
            shaped = _fill_to_voice(shaped, ends[action])
        active = sorted(k for k, v in shaped.items() if v > 0.0)
        trimmed = {k: shaped[k] for k in active}
        if active:
            _fade_edges(trimmed, active[0], active[-1])
        full = {i: trimmed.get(i, 0.0) for i in range(1, total + 1)}
        table[action] = full
        loud = [i for i in range(1, total + 1) if full[i] >= 0.2]
        print("FACE_SPEECH %-20s total=%d voice_end=%s active=%s..%s loud=%s..%s trans=%d mean=%.3f" % (
            action, total, ends.get(action, "-"),
            active[0] if active else "-", active[-1] if active else "-",
            loud[0] if loud else "-", loud[-1] if loud else "-",
            _transitions(full), sum(full.values()) / total))
    return table


def _blink_amount(frame, events):
    for start in events:
        t = frame - start
        if 0 <= t < BLINK_CLOSE:
            v = (t + 1) / BLINK_CLOSE
            return v * v * (3.0 - 2.0 * v)
        if BLINK_CLOSE <= t < BLINK_CLOSE + BLINK_HOLD:
            return 1.0
        if BLINK_CLOSE + BLINK_HOLD <= t < BLINK_CLOSE + BLINK_HOLD + BLINK_OPEN:
            v = 1.0 - (t - BLINK_CLOSE - BLINK_HOLD + 1) / BLINK_OPEN
            return max(0.0, v * v * (3.0 - 2.0 * v))
    return 0.0


def _gaze_amount(frame, windows):
    value = 0.0
    for start, end, target in windows:
        if frame < start or frame > end:
            continue
        span = end - start
        if span <= 0:
            continue
        t = (frame - start) / span
        if t < 0.3:
            v = t / 0.3
        elif t < 0.7:
            v = 1.0
        else:
            v = (1.0 - t) / 0.3
        v = max(0.0, min(1.0, v))
        value += target * v * v * (3.0 - 2.0 * v)
    return value


def _yaw_angle(frame, keys):
    """关键帧之间按 smoothstep 插值；首末关键帧之外一律为中位。"""
    for (f0, a0), (f1, a1) in zip(keys, keys[1:]):
        if f0 <= frame <= f1:
            t = (frame - f0) / (f1 - f0)
            return a0 + (a1 - a0) * t * t * (3.0 - 2.0 * t)
    return 0.0


def _lid_close(frame, window):
    """闭眼量（厘米）：保持段为 LID_CLOSED_CM，进入与退出各按窗口宽度做 smoothstep。"""
    if window is None:
        return 0.0
    start, hold_start, hold_end, end = window
    if frame <= start or frame >= end:
        return 0.0
    if hold_start <= frame <= hold_end:
        return LID_CLOSED_CM
    if frame < hold_start:
        t = (frame - start) / (hold_start - start)
    else:
        t = (end - frame) / (end - hold_end)
    return LID_CLOSED_CM * t * t * (3.0 - 2.0 * t)


def _think_fade(frame):
    """思考段首尾各 10 帧线性淡入淡出，段外为 0。"""
    if frame < THINK_START or frame > THINK_END:
        return 0.0
    return min(1.0, min(frame - THINK_START, THINK_END - frame) / THINK_FADE)


def _keys(frame, keys):
    """关键帧之间 smoothstep 插值，首末关键帧之外取端点值。"""
    if frame <= keys[0][0]:
        return keys[0][1]
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f0 <= frame <= f1:
            t = (frame - f0) / (f1 - f0)
            return v0 + (v1 - v0) * t * t * (3.0 - 2.0 * t)
    return keys[-1][1]


def facial_params(action, frame, envelope):
    jaw = envelope.get(action, {}).get(frame, 0.0)
    blink = _blink_amount(frame, BLINKS[action])
    gaze = _gaze_amount(frame, GAZES.get(action, []))
    brow = BROW.get(action, 0.0)
    yaw = _yaw_angle(frame, YAW_KEYS.get(action, []))
    lid = _lid_close(frame, LID_WINDOWS.get(action))
    brow_in = 0.0
    lip = 0.0
    lift = 0.0
    gaze_deg = 0.0
    if action == "JX_IDLE":
        fade = _think_fade(frame)
        yaw += _gaze_amount(frame, tuple((s, e, y) for s, e, y, _p in THINK_GAZE)) * fade
        gaze_deg = _gaze_amount(frame, tuple((s, e, p) for s, e, _y, p in THINK_GAZE)) * fade
        brow_in = _gaze_amount(frame, THINK_BROW_IN) * fade
        lip = _gaze_amount(frame, THINK_LIP) * fade
        # 惊讶段：思考段的眉唇偏移随淡出归零，眉整体上提、上睑抬起、下颌张开在此叠加
        brow += _keys(frame, SURPRISE_BROW)
        lift = _keys(frame, SURPRISE_LIFT)
        jaw = max(jaw, _keys(frame, SURPRISE_JAW))
    return {
        "jaw": jaw,
        "blink_L": blink,
        "blink_R": blink,
        "gaze_L": gaze,
        "gaze_R": gaze,
        "gaze_deg_L": gaze_deg,
        "gaze_deg_R": gaze_deg,
        "yaw_L": yaw,
        "yaw_R": yaw,
        "lid_L": lid,
        "lid_R": lid,
        "lift_L": lift,
        "lift_R": lift,
        "brow_L": brow,
        "brow_R": brow,
        "browin_L": brow_in,
        "browin_R": brow_in,
        "lip_press": lip,
    }
