import json
import os

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
md = open(os.path.join(ROOT, "workspace", "gen", "reports", "round3_face_geometry.md"), encoding="utf-8").read()
d = json.load(open(os.path.join(ROOT, "workspace", "gen", "reports", "round3_face_regions.json"), encoding="utf-8"))
pairs = []
pairs.append(("姿态", "眼睛中心L", ["%.4f" % x for x in d["eyeball_L"]["center"]]))
pairs.append(("ap", "眼裂高度", ["%.4f" % d["eye_aperture"]["height"], "%.3f" % d["eye_aperture"]["height"]]))
pairs.append(("ap", "眼裂宽度", ["%.4f" % d["eye_aperture"]["width"], "%.3f" % d["eye_aperture"]["width"]]))
pairs.append(("mo", "嘴中心", ["%.4f" % x for x in d["mouth_center"]]))
pairs.append(("mo", "嘴宽", ["%.4f" % d["mouth_width"], "%.3f" % d["mouth_width"]]))
pairs.append(("mo", "口裂宽", ["%.4f" % d["mouth_aperture"]["width"]]))
pairs.append(("jaw", "颌关节", ["%.4f" % abs(x) for x in d["jaw_pivot"]["left"]]))
pairs.append(("bl", "闭合", ["%.4f" % d["blink"]["closure_dz_absmax_L"] if d["blink"]["closure_dz_absmax_L"] > 1e-4 else "0.0001"]))
pairs.append(("cnt", "上睑L", [str(len(d["upper_lid_vertices_L"])), str(len(d["upper_lid_vertices_R"]))]))
pairs.append(("cnt", "下睑", [str(len(d["lower_lid_vertices_L"])), str(len(d["lower_lid_vertices_R"]))]))
pairs.append(("cnt", "嘴", [str(len(d["mouth_vertices"])), str(len(d["mouth_region_vertices"]))]))
pairs.append(("cnt", "瞳孔", [str(len(d["eyeball_L"]["pupil"]["vertices"]))]))
bad = []
for tag, label, variants in pairs:
    if not any(v in md for v in variants):
        bad.append((label, variants))
print("MD_CROSSCHECK", "items", len(pairs), "missing", bad)
raise SystemExit(1 if bad else 0)
