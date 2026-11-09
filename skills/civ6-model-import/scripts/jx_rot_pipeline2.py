import os
import shutil
import subprocess

BLENDER = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\_tools\blender45\blender-4.5.9-windows-x64\blender.exe"
SCRIPT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\_tools\jx_rot_probe2.py"
ENV = dict(os.environ)
ENV["BLENDER_USER_RESOURCES"] = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\_tools\blender45\userres"
FBXDIR = r"E:\SoftWares\civ6_nexus_work\jinhsi_fbx"
GEN = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx"
STAGE = r"E:\SoftWares\civ6_nexus_work\probe2_fgx"
EXE = r"E:\SoftWares\civ6_nexus_work\CivNexus6\NexusBatch.exe"
DUMPER = r"E:\SoftWares\civ6_nexus_work\CivNexus6\NexusDumpQin.exe"

VARIANTS = [("X", 90), ("X", -90), ("Y", 90), ("Y", -90), ("Z", 90), ("Z", -90)]

os.makedirs(STAGE, exist_ok=True)
for f in os.listdir(STAGE):
    os.remove(os.path.join(STAGE, f))

for axis, deg in VARIANTS:
    r = subprocess.run([BLENDER, "-b", "--python", SCRIPT, "--", axis, str(deg)],
                       env=ENV, capture_output=True, text=True, timeout=900)
    tail = [l for l in (r.stdout + r.stderr).splitlines() if "PROBE2" in l or "Error" in l]
    print("\n".join(tail[-2:]))

    name = "PROBE2_%s%+.0f" % (axis, deg)
    shutil.copy2(os.path.join(GEN, name + ".cn6"), os.path.join(FBXDIR, name + ".cn6"))

fixed = os.path.join(FBXDIR, "PROBE2.cn6")
model_fbx = os.path.join(FBXDIR, "LEAD_Jinhsi_QYQXP_Model.fbx")
model_fbx_bak = model_fbx + ".bak"
if os.path.exists(model_fbx) and not os.path.exists(model_fbx_bak):
    shutil.copy2(model_fbx, model_fbx_bak)

for axis, deg in VARIANTS:
    name = "PROBE2_%s%+.0f" % (axis, deg)
    shutil.copy2(os.path.join(FBXDIR, name + ".cn6"), fixed)
    r = subprocess.run([EXE, FBXDIR, STAGE, "R2T1JinxiMd10011"],
                       capture_output=True, text=True, timeout=600, cwd=os.path.dirname(EXE))
    src = os.path.join(STAGE, "LEAD_Jinhsi_QYQXP.fgx")
    dst = os.path.join(STAGE, name + ".fgx")
    if os.path.exists(src):
        shutil.move(src, dst)
    for f in os.listdir(STAGE):
        if f.endswith(("_src.fgx", ".geo", ".anm", ".wig")):
            os.remove(os.path.join(STAGE, f))
    d = subprocess.run([DUMPER, dst], capture_output=True, text=True, timeout=300,
                       cwd=os.path.dirname(EXE))
    lines = [l for l in d.stdout.splitlines() if "Head" in l or "Model" in l or "placement" in l]
    print("==", name)
    print("\n".join(lines))
