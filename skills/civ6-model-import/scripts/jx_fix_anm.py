import os
import re

ANIM_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi\Animations"
NAMES = ["JX_IDLE", "JX_FirstMeet", "JX_DeclareWarHuman", "JX_DeclareWarAI",
         "JX_Kudos", "JX_Warning", "JX_Defeat"]

pattern = re.compile(r"<Element>\s*<m_ID text=\"WIG\"/>\s*<m_RelativePath text=\"[^\"]+\"/>\s*</Element>\s*")

for name in NAMES:
    path = os.path.join(ANIM_DIR, name + ".anm")
    text = open(path, encoding="utf-8").read()
    new_text = pattern.sub("", text)
    if new_text == text:
        print("NO_WIG_FOUND", name)
        continue
    open(path, "w", encoding="utf-8", newline="\n").write(new_text)
    wig = os.path.join(ANIM_DIR, name + ".wig")
    if os.path.exists(wig):
        os.remove(wig)
    print("ANM_FIXED", name)
print("DONE")
