import json
import sys

SRC = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/pmx/pmx_forensics.json"

FACE_KEYS = ["左目", "右目", "両目", "あ", "口", "眉", "舌", "目", "顎", "頬", "歯", "まばたき", "笑い", "ウィンク", "じと目", "Cheek", "Eye", "Mouth", "Jaw", "Brow", "Tongue"]

with open(SRC, "r", encoding="utf-8") as f:
    data = json.load(f)

lines = []
for r in data:
    lines.append("FILE " + r["path"])
    lines.append("  model_name " + r["name"])
    lines.append("  bones " + str(r["bone_count"]))
    lines.append("  morphs " + str(r["morph_count"]))
    lines.append("  FACE_BONES " + str(r["face_bone_count"]) + " -> " + " | ".join(r["face_bones"]))
    lines.append("  ALL_BONES " + " | ".join(r["bone_names"]))
    lines.append("  MORPH_LIST")
    for m in r["morphs"]:
        lines.append("    t%d c%d off%-5d %s" % (m["type"], m["category"], m["offsets"], m["name"]))

dst = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/pmx/pmx_summary.txt"
with open(dst, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("SUMMARY_DONE", dst, len(lines))
for r in data:
    print(r["name"], "bones", r["bone_count"], "face", r["face_bone_count"], "morphs", r["morph_count"])
