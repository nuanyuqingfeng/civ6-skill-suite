import bpy
import math
import sys

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FBX = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx\JX_IDLE.fbx"
if ARGV and not ARGV[0].startswith("--"):
    FBX = ARGV[0]
LO, HI = (int(x) for x in (ARGV[ARGV.index("--range") + 1].split(",") if "--range" in ARGV else ("505,560")))
BONES = (ARGV[ARGV.index("--bones") + 1].split(",") if "--bones" in ARGV else
         ("Bip001LHand", "Bip001RHand", "Bip001Head", "Bip001Pelvis"))
OFF = 1

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
act = arm.animation_data.action
curves = {}
for fc in act.fcurves:
    if 'pose.bones' not in fc.data_path or not fc.data_path.endswith('rotation_quaternion'):
        continue
    name = fc.data_path.split('"')[1]
    if name in BONES:
        curves.setdefault(name, {})[fc.array_index] = fc
print("TRACK bones", sorted(curves))
prev = {}
for f in range(LO + OFF, HI + OFF + 1):
    parts = []
    for name, ch in curves.items():
        q = [ch[i].evaluate(f) for i in (0, 1, 2, 3)]
        n = math.sqrt(sum(v * v for v in q))
        q = [v / n for v in q]
        p = prev.get(name)
        if p is not None:
            d = abs(sum(q[i] * p[i] for i in range(4)))
            parts.append("%s=%.2f" % (name[3:] or name, math.degrees(2.0 * math.acos(min(1.0, d)))))
        prev[name] = q
    print("T %d %s" % (f - OFF, " ".join(parts)))
