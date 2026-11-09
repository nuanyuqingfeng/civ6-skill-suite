import os
import shutil
import subprocess
import sys

BLENDER = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\_tools\blender45\blender-4.5.9-windows-x64\blender.exe"
SCRIPT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\_tools\jx_rot_probe.py"
ENV = dict(os.environ)
ENV["BLENDER_USER_RESOURCES"] = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\_tools\blender45\userres"
FBXDIR = r"E:\SoftWares\civ6_nexus_work\jinhsi_fbx"
GEN = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx"
STAGE = r"E:\SoftWares\civ6_nexus_work\probe_fgx"

VARIANTS = [("X", 90), ("X", -90), ("Y", 90), ("Z", 90), ("Z", -90)]

os.makedirs(STAGE, exist_ok=True)
for f in os.listdir(STAGE):
    os.remove(os.path.join(STAGE, f))

for axis, deg in VARIANTS:
    r = subprocess.run([BLENDER, "-b", "--python", SCRIPT, "--", axis, str(deg)],
                       env=ENV, capture_output=True, text=True, timeout=600)
    tail = [l for l in (r.stdout + r.stderr).splitlines() if "PROBE" in l or "Error" in l]
    print("\n".join(tail[-3:]))

    name = "PROBE_%s%+.0f" % (axis, deg)
    shutil.copy2(os.path.join(GEN, name + ".cn6"), os.path.join(FBXDIR, name + ".cn6"))

os.chdir(r"E:\SoftWares\civ6_nexus_work\CivNexus6")
exe = os.path.join(r"E:\SoftWares\civ6_nexus_work\CivNexus6", "NexusBatch.exe")
fixed_cn6 = os.path.join(FBXDIR, "LEAD_Jinhsi_QYQXP.cn6")
for axis, deg in VARIANTS:
    name = "PROBE_%s%+.0f" % (axis, deg)
    src_cn6 = os.path.join(FBXDIR, name + ".cn6")
    shutil.copy2(src_cn6, fixed_cn6)
    r = subprocess.run([exe, FBXDIR, STAGE, "R2T1JinxiMd10011"],
                       capture_output=True, text=True, timeout=600)
    dst = os.path.join(STAGE, name + ".fgx")
    shutil.move(os.path.join(STAGE, "LEAD_Jinhsi_QYQXP.fgx"), dst)
    geo = os.path.join(STAGE, "LEAD_Jinhsi_QYQXP.geo")
    if os.path.exists(geo):
        os.remove(geo)
    for f in os.listdir(STAGE):
        if f.endswith("_src.fgx"):
            os.remove(os.path.join(STAGE, f))
    print("CONVERTED", name, r.returncode)

dump = subprocess.run([os.path.join(r"E:\SoftWares\civ6_nexus_work\CivNexus6", "NexusDump.exe")] +
                      [os.path.join(STAGE, "PROBE_%s%+.0f.fgx" % (a, d)) for a, d in VARIANTS],
                      capture_output=True, text=True, timeout=600, cwd=r"E:\SoftWares\civ6_nexus_work\CivNexus6")
print(dump.stdout)
