import bpy
import math
import sys

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FBX = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx\JX_IDLE.fbx"
if ARGV and not ARGV[0].startswith("--"):
    FBX = ARGV[0]
OFF = int(ARGV[ARGV.index("--off") + 1]) if "--off" in ARGV else 1
WATCH = ("Bip001", "Bip001Pelvis", "Bip001Head", "Bip001LHand", "Bip001RHand")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
act = arm.animation_data.action
lo = int(act.frame_range[0])
hi = int(act.frame_range[1])
print("DIAG_ACTION", act.name, (lo, hi), "frames", hi - lo + 1, "fps", bpy.context.scene.render.fps)

pos = {}
for f in range(lo, hi + 1):
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    pos[f - OFF] = {n: (arm.matrix_world @ arm.pose.bones[n].matrix).to_translation()
                    for n in WATCH}

first, last = 2, hi - OFF
acc = {}
for f in range(first + 1, last):
    acc[f] = max((pos[f + 1][n] - 2.0 * pos[f][n] + pos[f - 1][n]).length for n in WATCH) * 100.0
rank = sorted(acc.items(), key=lambda kv: -kv[1])[:12]
print("DIAG_ACC_TOP", " ".join("%d:%.3f" % (f, v) for f, v in rank))
step = {f: max((pos[f][n] - pos[f - 1][n]).length for n in WATCH) * 100.0 for f in range(first + 1, last + 1)}
rank = sorted(step.items(), key=lambda kv: -kv[1])[:12]
print("DIAG_STEP_TOP", " ".join("%d:%.3f" % (f, v) for f, v in rank))
for lo2, hi2 in ((470, 560), (730, 800), (830, 900)):
    print("DIAG_RANGE", lo2, hi2)
    for f in range(lo2, hi2 + 1, 2):
        print("F %d step=%.3f acc=%.3f head_step=%.3f pelvis_step=%.3f handR_step=%.3f" % (
            f, step[f], acc[f],
            (pos[f]["Bip001Head"] - pos[f - 1]["Bip001Head"]).length * 100.0,
            (pos[f]["Bip001Pelvis"] - pos[f - 1]["Bip001Pelvis"]).length * 100.0,
            (pos[f]["Bip001RHand"] - pos[f - 1]["Bip001RHand"]).length * 100.0))
