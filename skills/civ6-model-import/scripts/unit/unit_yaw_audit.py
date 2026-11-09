import bpy
import json
import math
import os
import sys

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

def arg(name, default=None):
    if name in ARGV:
        return ARGV[ARGV.index(name) + 1]
    return default

FBX = arg("--fbx")
OUT = arg("--json")
TOL = float(arg("--tolerance", "1.0"))
STANCE = arg("--stance", "IDLE")
STOP = arg("--stop", "RUN_STOP")

assert FBX and os.path.isfile(FBX), FBX

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
acts = {a.name.split("|")[-1]: a for a in bpy.data.actions}
arm.animation_data_create()


def use(action):
    arm.animation_data.action = action
    if len(action.slots):
        arm.animation_data.action_slot = action.slots[0]


def yaw_now():
    lh = arm.pose.bones["Bip001LThigh"].matrix.translation
    rh = arm.pose.bones["Bip001RThigh"].matrix.translation
    return math.degrees(math.atan2(-(rh.x - lh.x), rh.y - lh.y))


def wrap(deg):
    while deg > 180.0:
        deg -= 360.0
    while deg < -180.0:
        deg += 360.0
    return deg


rows = []
for name in sorted(acts):
    act = acts[name]
    use(act)
    f0 = int(round(act.frame_range[0]))
    f1 = int(round(act.frame_range[1]))
    bpy.context.scene.frame_set(f0)
    bpy.context.view_layer.update()
    first = yaw_now()
    prev = first
    path = 0.0
    for f in range(f0 + 1, f1 + 1):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        y = yaw_now()
        path += wrap(y - prev)
        prev = y
    rows.append({"clip": name, "first": round(first, 3), "path": round(path, 3),
                 "last": round(prev, 3), "frames": [f0, f1]})
    print("YAW %-30s first %8.3f path %8.3f last %8.3f" % (name, first, path, prev))

stops = [r for r in rows if STOP.lower() in r["clip"].lower()]
assert stops, "找不到匹配 %s 的基准片段" % STOP
target = stops[-1]["last"]
print("TARGET_FROM %s last %.3f" % (stops[-1]["clip"], target))

bad = 0
for r in rows:
    if STANCE.lower() not in r["clip"].lower():
        continue
    delta = wrap(r["first"] - target)
    ok = abs(delta) <= TOL
    if not ok:
        bad += 1
    print("STANCE %-30s yaw %8.3f delta %8.3f %s" % (r["clip"], r["first"], delta, "PASS" if ok else "FAIL"))

if OUT:
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"fbx": FBX, "target": target, "tolerance": TOL, "rows": rows, "fail": bad},
                  fh, ensure_ascii=False, indent=1)
    print("JSON " + OUT)
print("UNIT_YAW_AUDIT_%s fail=%d" % ("OK" if bad == 0 else "FAIL", bad))
sys.exit(0 if bad == 0 else 1)
