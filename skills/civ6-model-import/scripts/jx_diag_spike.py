import bpy
import math
import sys

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FBX = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx\JX_IDLE.fbx"
if ARGV and not ARGV[0].startswith("--"):
    FBX = ARGV[0]
LO, HI = (int(x) for x in (ARGV[ARGV.index("--range") + 1].split(",") if "--range" in ARGV else ("505,525")))
OFF = 1

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
act = arm.animation_data.action
curves = {}
for fc in act.fcurves:
    if 'pose.bones' in fc.data_path and fc.data_path.endswith('rotation_quaternion'):
        name = fc.data_path.split('"')[1]
        curves.setdefault(name, {})[fc.array_index] = fc
prev = None
worst_bone = None
for f in range(LO + OFF, HI + OFF + 1):
    cur = {n: [ch[i].evaluate(f) for i in (0, 1, 2, 3)] for n, ch in curves.items()}
    if prev is not None:
        best = (0.0, "-")
        for n, q in cur.items():
            p = prev.get(n)
            if p is None:
                continue
            d = abs(sum(q[i] * p[i] for i in range(4)))
            ang = math.degrees(2.0 * math.acos(min(1.0, d)))
            if ang > best[0]:
                best = (ang, n)
        print("SPIKE %d %.2f %s" % (f - OFF, best[0], best[1]))
        if worst_bone is None or best[0] > worst_bone[0]:
            worst_bone = (best[0], best[1], f - OFF)
    prev = cur
print("SPIKE_WORST", worst_bone)
name = worst_bone[1]
for f in range(worst_bone[2] - 4 + OFF, worst_bone[2] + 5 + OFF):
    q = [curves[name][i].evaluate(f) for i in (0, 1, 2, 3)]
    n = math.sqrt(sum(v * v for v in q))
    q = [v / n for v in q]
    print("Q %d %s" % (f - OFF, " ".join("%.4f" % v for v in q)))
