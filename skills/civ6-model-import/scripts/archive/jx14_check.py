import json
import os

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
PATH = os.path.join(ROOT, "workspace", "gen", "reports", "round3_face_regions.json")
with open(PATH, encoding="utf-8") as fh:
    data = json.load(fh)

fails = []


def check(tag, cond, detail):
    print(("PASS " if cond else "FAIL ") + tag + " " + str(detail))
    if not cond:
        fails.append(tag)


required = ["mouth_vertices", "mouth_center", "mouth_width", "jaw_pivot",
            "upper_lid_vertices_L", "lower_lid_vertices_L",
            "upper_lid_vertices_R", "lower_lid_vertices_R",
            "eyeball_L", "eyeball_R", "head_bone"]
for key in required:
    check("key:" + key, key in data, "present" if key in data else "missing")

nverts = data["source"]["vertices"]
check("vertices", nverts == 37013, nverts)
check("triangles", data["source"]["triangles"] == 56483, data["source"]["triangles"])
check("bones", data["source"]["bones"] == 204, data["source"]["bones"])
check("materials", len(data["materials"]) == 7, list(data["materials"].keys()))
check("overlap_zero", data["slot_vertex_overlap"]["nonzero_pairs"] == 0,
      data["slot_vertex_overlap"]["nonzero_pairs"])

lists = ["mouth_vertices", "mouth_region_vertices", "mouth_lip_colored_vertices",
         "mouth_upper_lip", "mouth_lower_lip", "mouth_aperture",
         "upper_lid_vertices_L", "lower_lid_vertices_L", "upper_lid_vertices_R", "lower_lid_vertices_R",
         "upper_lash_vertices_L", "upper_lash_vertices_R",
         "eye_crease_vertices_L", "eye_crease_vertices_R"]
for key in lists:
    v = data[key]
    if key == "mouth_aperture":
        v = data[key]["rim"]
    ok_range = all(isinstance(i, int) and 0 <= i < nverts for i in v)
    ok_uniq = len(set(v)) == len(v)
    check("range:" + key, ok_range, len(v))
    check("unique:" + key, ok_uniq, len(v))

for side in ("L", "R"):
    eb = data["eyeball_" + side]
    check("eyeball_verts:" + side, len(eb["vertices"]) == 109, len(eb["vertices"]))
    check("eyeball_pupil:" + side, len(eb["pupil"]["vertices"]) == 87, len(eb["pupil"]["vertices"]))
    check("eyeball_sym:" + side, abs(abs(eb["center"][0]) - 3.0615) < 0.01, eb["center"])

check("mouth_count", len(data["mouth_vertices"]) == 404, len(data["mouth_vertices"]))
check("mouth_region_count", len(data["mouth_region_vertices"]) == 517, len(data["mouth_region_vertices"]))
check("lip_split", len(data["mouth_upper_lip"]) + len(data["mouth_lower_lip"]) == len(data["mouth_vertices"]),
      [len(data["mouth_upper_lip"]), len(data["mouth_lower_lip"])])
check("mouth_width", abs(data["mouth_width"] - 3.0059) < 0.001, data["mouth_width"])
check("mouth_center", abs(data["mouth_center"][2] - 135.417) < 0.001, data["mouth_center"])

for side in ("L", "R"):
    rim = data["eye_aperture"]["rim_" + side]
    check("rim_count:" + side, len(rim) == 33, len(rim))
    w = data["blink"]["weights_" + side]
    margin = set(data["eye_aperture"]["upper_margin_" + side])
    lash = set(data["upper_lash_vertices_" + side])
    lid = set(data["upper_lid_vertices_" + side])
    allowed = margin | lash | lid
    check("weights_subset:" + side, set(int(k) for k in w) <= allowed, len(w))
    check("weights_range:" + side, all(0.0 <= float(v) <= 1.0 for v in w.values()), len(w))
    check("closure:" + side, data["blink"]["closure_dz_absmax_" + side] < 0.001,
          data["blink"]["closure_dz_absmax_" + side])

check("jaw_axis", abs(data["jaw_pivot"]["axis"][0] - 1.0) < 1e-6, data["jaw_pivot"]["axis"])
check("jaw_x", abs(data["jaw_pivot"]["left"][0] + 5.4762) < 0.001, data["jaw_pivot"]["left"])
check("jaw_headlocal", len(data["jaw_pivot"]["head_local_left"]) == 3, data["jaw_pivot"]["head_local_left"])
check("head_axes", len(data["head_bone"]["axes_world"]) == 3, list(data["head_bone"]["axes_world"].keys()))
check("apex_height", abs(data["eye_aperture"]["height"] - 1.348) < 0.001, data["eye_aperture"]["height"])
check("apex_width", abs(data["eye_aperture"]["width"] - 2.928) < 0.001, data["eye_aperture"]["width"])
check("lid_counts", [len(data["upper_lid_vertices_L"]), len(data["lower_lid_vertices_L"]),
                     len(data["upper_lid_vertices_R"]), len(data["lower_lid_vertices_R"])] == [57, 23, 62, 24],
      [len(data["upper_lid_vertices_L"]), len(data["lower_lid_vertices_L"]),
       len(data["upper_lid_vertices_R"]), len(data["lower_lid_vertices_R"])])

print("FAILS", fails)
raise SystemExit(1 if fails else 0)
