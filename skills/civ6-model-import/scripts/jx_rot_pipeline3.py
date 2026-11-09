import os
import shutil
import subprocess

FBXDIR = r"E:\SoftWares\civ6_nexus_work\jinhsi_fbx"
GEN = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx"
STAGE = r"E:\SoftWares\civ6_nexus_work\probe3_fgx"
EXE = r"E:\SoftWares\civ6_nexus_work\CivNexus6\NexusBatch.exe"
DUMPER = r"E:\SoftWares\civ6_nexus_work\CivNexus6\NexusDumpQin.exe"

VARIANTS = [("X", 90), ("X", -90), ("Y", 90), ("Y", -90), ("Z", 90), ("Z", -90)]

os.makedirs(STAGE, exist_ok=True)
for f in os.listdir(STAGE):
    os.remove(os.path.join(STAGE, f))

fixed = os.path.join(FBXDIR, "PROBE2.cn6")
for axis, deg in VARIANTS:
    name = "PROBE3_%s%+.0f" % (axis, deg)
    shutil.copy2(os.path.join(GEN, name + ".cn6"), fixed)
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
    lines = [l.strip() for l in d.stdout.splitlines()
             if "Bip001Head invWorld" in l or "Bip001Pelvis invWorld" in l]
    print("==", name)
    print("\n".join(lines))
