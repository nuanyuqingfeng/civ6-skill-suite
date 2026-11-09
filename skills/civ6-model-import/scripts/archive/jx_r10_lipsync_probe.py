import json
import math
import os
import sys

import bpy

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_anim as face_anim

FBX = os.path.join(ROOT, "workspace", "gen", "jinhsi_fbx", "%s.fbx")
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r10_lipsync_stats.tsv")
NAMES = ["JX_IDLE", "JX_FirstMeet", "JX_DeclareWarHuman", "JX_DeclareWarAI",
         "JX_Kudos", "JX_Warning", "JX_Defeat"]
# 开口幅度 0.2 对应 15° × 0.2 = 3°，与 workspace/gen/reports/voice_sync.md 同口径
THRESHOLD_DEG = 3.0
# 补齐前的动画帧数：用于核对补齐段保持最后一帧姿态
BASE_FRAMES = {"JX_Kudos": 240, "JX_Warning": 150}

with open(face_anim.ENVELOPE, encoding="utf-8") as fh:
    DURATION = {e["action"]: e["duration_s"] for e in json.load(fh)["entries"]}


def jaw_angle(arm, quat0, frame):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    q = arm.pose.bones["JX_Jaw"].rotation_quaternion.copy()
    return math.degrees(quat0.rotation_difference(q).angle)


def spans_of(frames):
    spans = []
    for f in frames:
        if spans and f == spans[-1][1] + 1:
            spans[-1][1] = f
        else:
            spans.append([f, f])
    return spans


def hold_deviation(arm, base, total):
    """补齐段的骨架姿态偏差，面部骨骼（JX_ 前缀）由口型包络驱动，不计入。"""
    body = [pb for pb in arm.pose.bones if not pb.name.startswith("JX_")]
    bpy.context.scene.frame_set(base)
    bpy.context.view_layer.update()
    ref = {pb.name: pb.matrix.copy() for pb in body}
    worst = 0.0
    for f in range(base + 1, total + 1):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        for pb in body:
            a = ref[pb.name]
            dev = max(abs(a[i][j] - pb.matrix[i][j]) for i in range(4) for j in range(4))
            worst = max(worst, dev)
    return worst


ends = face_anim.voice_ends()
head = ("动画\t帧数\t语音s\t语音换算帧\t语音结束帧\t活动区间\t活动帧数\t占整段\t"
        "末次开口帧\t距语音结束\t峰值角\t补齐段姿态偏差")
lines = [head]
for name in NAMES:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=FBX % name)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    act = arm.animation_data.action
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    total = f1 - f0 + 1
    bpy.context.scene.frame_set(f0)
    bpy.context.view_layer.update()
    quat0 = arm.pose.bones["JX_Jaw"].rotation_quaternion.copy()
    loud = []
    peak = 0.0
    for f in range(f0, f1 + 1):
        a = jaw_angle(arm, quat0, f)
        peak = max(peak, a)
        if a > THRESHOLD_DEG:
            # fbx 导入后关键帧整体比导出帧号大 1，换回导出帧号
            loud.append(f - 1)
    spans = spans_of(loud)
    hold = hold_deviation(arm, f0 + BASE_FRAMES[name] - 1, f1) if name in BASE_FRAMES else 0.0
    duration = DURATION[name]
    voice_frames = int(math.ceil(duration * face_anim.FPS))
    voice_end = ends.get(name)
    last = spans[-1][1] if spans else None
    lines.append("%s\t%d\t%s\t%s\t%s\t%s\t%d\t%.1f%%\t%s\t%s\t%.2f\t%.9f" % (
        name, total,
        "%.3f" % duration if duration else "-",
        voice_frames if voice_frames else "-",
        voice_end if voice_end else "-",
        " / ".join("%d～%d" % (a, b) for a, b in spans) if spans else "无",
        len(loud), 100.0 * len(loud) / total,
        last if last else "-",
        (voice_end - last) if (voice_end and last) else "-",
        peak, hold))

with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines) + "\n")
print("LIPSYNC_STATS", OUT)
for line in lines:
    print(line)
print("PROBE_DONE")
