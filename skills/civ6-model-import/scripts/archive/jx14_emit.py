import json
import math
import os

import numpy as np
from PIL import Image

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
TMP = os.path.join(ROOT, "workspace", "tmp")
REP = os.path.join(ROOT, "workspace", "gen", "reports")
MODEL = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
FACE_TEX = os.path.join(MODEL, "T_R2T1JinxiMd10011Face_D.png")
EYE_TEX = os.path.join(MODEL, "T_R2T1JinxiMd10011Eye_D.png")

with open(os.path.join(TMP, "jx14_slots.json"), encoding="utf-8") as fh:
    slots = json.load(fh)
with open(os.path.join(TMP, "jx14_parts.json"), encoding="utf-8") as fh:
    parts = json.load(fh)

verts = np.array(slots["vertex_coords"], dtype=np.float64)
face_uv = slots["uv_faces"]["MI_R2T1JinxiMd10011Face"]
eye_uv = slots["uv_faces"]["MI_R2T1JinxiMd10011Eye"]
face_faces = [[c[0] for c in f] for f in face_uv]
main = sorted({v for f in face_faces for v in f})
nbr = {v: set() for v in main}
for f in face_faces:
    for k in range(len(f)):
        a, b = f[k], f[(k + 1) % len(f)]
        nbr[a].add(b)
        nbr[b].add(a)

rimL = [int(v) for v in parts["rimL"]]
rimR = [int(v) for v in parts["rimR"]]
CZ = float(verts[rimL][:, 2].mean())
Z_TOP = 140.56
TRAVEL_Z = 1.348
TRAVEL_Y = 0.20
SCALE = 0.915502
names = list(slots["slots"].keys())

apv = [int(v) for v in parts["mouth_ap"]]
apP = verts[apv]
segs = [(apP[i], apP[(i + 1) % len(apP)]) for i in range(len(apP))]


def dist_to_ring(p):
    best = 1e9
    for a, b in segs:
        ab = b - a
        t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-12), 0.0, 1.0)
        q = a + ab * t
        best = min(best, float(np.linalg.norm(p - q)))
    return best


dist = {v: dist_to_ring(verts[v]) for v in main}
img_f = np.asarray(Image.open(FACE_TEX).convert("RGB"), dtype=np.float64) / 255.0
HF, WF = img_f.shape[0], img_f.shape[1]


def sample_face(u, v):
    x = int(min(WF - 1, max(0, u * (WF - 1))))
    y = int(min(HF - 1, max(0, (1.0 - v) * (HF - 1))))
    return img_f[y, x]


lip_color = set()
for f in face_uv:
    for vidx, uv in f:
        p = sample_face(uv[0], uv[1])
        if p[0] - p[1] > 0.25 and p[0] - p[2] > 0.30 and p[0] < 0.90:
            lip_color.add(vidx)
mouth_region = sorted(v for v in main if dist[v] <= 1.00)
lip_band = sorted(v for v in main if dist[v] <= 0.65)
lip_near = sorted(v for v in lip_color if v in dist and dist[v] <= 1.00)
Pn = verts[lip_near]
mouth_width = float(Pn[:, 0].max() - Pn[:, 0].min())
corner_v = (sorted(lip_near, key=lambda v: verts[v][0])[0], sorted(lip_near, key=lambda v: verts[v][0])[-1])
mouth_z = float(apP[:, 2].mean())
upper_lip = [v for v in lip_band if verts[v][2] >= mouth_z]
lower_lip = [v for v in lip_band if verts[v][2] < mouth_z]
print("MOUTH", "band", len(lip_band), "region", len(mouth_region), "colored", len(lip_near),
      "width", round(mouth_width, 4), "center", [round(float(c), 4) for c in apP.mean(axis=0)],
      "ap_w", round(float(apP[:, 0].max() - apP[:, 0].min()), 4),
      "z", [round(float(apP[:, 2].min()), 4), round(float(apP[:, 2].max()), 4)])


def depth_from(rim, maxd=3):
    depth = {v: 0 for v in rim}
    frontier = set(rim)
    for d in range(1, maxd + 1):
        nxt = set()
        for v in frontier:
            for w in nbr[v]:
                if w not in depth:
                    depth[w] = d
                    nxt.add(w)
        frontier = nxt
    return depth


blink = {}
for tag, rim in (("L", rimL), ("R", rimR)):
    depth = depth_from(rim)
    up = sorted(int(v) for v in parts["upL" if tag == "L" else "upR"])
    lo = sorted(int(v) for v in parts["loL" if tag == "L" else "loR"])
    lash = sorted(int(v) for v in parts["lashL" if tag == "L" else "lashR"])
    margin = sorted([v for v in rim if verts[v][2] > CZ + 0.02], key=lambda v: float(verts[v][0]))
    lower = [v for v in rim if verts[v][2] <= CZ]
    mx = np.array([float(verts[v][0]) for v in margin])
    mw = []
    for v in margin:
        cand = min(lower, key=lambda u: abs(float(verts[u][0]) - float(verts[v][0])))
        mw.append(max(0.0, min(1.0, (float(verts[v][2]) - float(verts[cand][2])) / TRAVEL_Z)))
    mw = np.array(mw)
    mz = np.array([float(verts[v][2]) for v in margin])
    w = {}
    for i, v in enumerate(margin):
        w[v] = round(float(mw[i]), 4)
    for v in up:
        wx = float(np.interp(float(verts[v][0]), mx, mw))
        ztop = float(np.interp(float(verts[v][0]), mx, mz))
        tz = max(0.0, min(1.0, (Z_TOP - float(verts[v][2])) / max(Z_TOP - ztop, 1e-6)))
        w[v] = round(wx * tz, 4)
    for v in lash:
        w[v] = round(float(np.interp(float(verts[v][0]), mx, mw)), 4)
    moved = {v: verts[v] + np.array([0.0, -TRAVEL_Y, -TRAVEL_Z]) * wv for v, wv in w.items()}
    dz = []
    for v in margin:
        cand = min(lower, key=lambda u: abs(float(verts[u][0]) - float(verts[v][0])))
        dz.append(float(moved[v][2] - verts[cand][2]))
    up_rings = {}
    for v in up:
        up_rings.setdefault(depth[v], []).append(v)
    lo_rings = {}
    for v in lo:
        lo_rings.setdefault(depth[v], []).append(v)
    travel = [float(np.linalg.norm(np.array([0.0, -TRAVEL_Y, -TRAVEL_Z]) * wv)) for wv in w.values()]
    blink[tag] = {"weights": w, "margin": margin, "lower": lower,
                  "dz_mean": float(np.mean(dz)), "dz_abs_max": float(np.max(np.abs(dz))),
                  "up_rings": {str(k): len(v) for k, v in up_rings.items()},
                  "lo_rings": {str(k): len(v) for k, v in lo_rings.items()},
                  "w_min": float(mw.min()), "w_max": float(mw.max()),
                  "travel_max": float(max(travel))}
    print("BLINK", tag, "margin_w", round(float(mw.min()), 3), round(float(mw.max()), 3),
          "dz_mean", round(blink[tag]["dz_mean"], 4), "dz_absmax", round(blink[tag]["dz_abs_max"], 4),
          "travel_max", round(blink[tag]["travel_max"], 3),
          "rings_up", blink[tag]["up_rings"], "rings_lo", blink[tag]["lo_rings"])

img_e = np.asarray(Image.open(EYE_TEX).convert("RGB"), dtype=np.float64) / 255.0
HE, WE = img_e.shape[0], img_e.shape[1]


def sample_eye(u, v):
    x = int(min(WE - 1, max(0, u * (WE - 1))))
    y = int(min(HE - 1, max(0, (1.0 - v) * (HE - 1))))
    return img_e[y, x]


dark = {0: set(), 1: set()}
for f in eye_uv:
    for vidx, uv in f:
        if sample_eye(uv[0], uv[1]).max() < 0.35:
            dark[0 if float(verts[vidx][0]) < 0 else 1].add(vidx)
pupil = {}
for side, tag in ((0, "L"), (1, "R")):
    vs = sorted(dark[side])
    P = verts[vs]
    pupil[tag] = {"vertices": vs, "center": [float(x) for x in P.mean(axis=0)],
                  "radius_mean": float(np.mean(np.linalg.norm(P - P.mean(axis=0), axis=1)))}
print("PUPIL", len(pupil["L"]["vertices"]), [round(x, 4) for x in pupil["L"]["center"]],
      round(pupil["L"]["radius_mean"], 4))

head_m = np.array(slots["head_bone"]["matrix_local"], dtype=np.float64)
axes = {"x": head_m[:3, 0].tolist(), "y": head_m[:3, 1].tolist(), "z": head_m[:3, 2].tolist()}
slot_verts = {k: set(v) for k, v in slots["slot_vertex_indices"].items()}
overlap = {}
for a in names:
    for b in names:
        if a < b:
            overlap[a + "|" + b] = len(slot_verts[a] & slot_verts[b])

ear_c = {}
for s, sgn in (("L", -1.0), ("R", 1.0)):
    sel = [v for v in main if abs(verts[v][0]) >= 5.6 and 136.0 <= verts[v][2] <= 143.5
           and np.sign(verts[v][0]) == sgn]
    ear_c[s] = [float(x) for x in np.mean(verts[sel], axis=0)]
half_w = float(max(abs(verts[v][0]) for v in main if 136.0 <= verts[v][2] <= 143.5))
pivot_x = 0.72 * half_w
pivot_y = ear_c["L"][1] - 0.9
pivot_z = mouth_z + 1.8
pivL = np.array([-pivot_x, pivot_y, pivot_z])
pivR = np.array([pivot_x, pivot_y, pivot_z])
inv_head = np.linalg.inv(head_m)
pivL_local = (inv_head @ np.array([pivL[0], pivL[1], pivL[2], 1.0]))[:3]
pivR_local = (inv_head @ np.array([pivR[0], pivR[1], pivR[2], 1.0]))[:3]
axis = (pivR - pivL) / np.linalg.norm(pivR - pivL)
chin_v = [v for v in main if abs(verts[v][0]) < 1.5 and verts[v][2] < 134.5 and verts[v][1] < -1.5]
chin_bottom = verts[chin_v][verts[chin_v][:, 2].argmin()]


def rot_about(p, pivot, ax, ang):
    v = p - pivot
    c, s = math.cos(ang), math.sin(ang)
    return pivot + v * c + np.cross(ax, v) * s + ax * np.dot(ax, v) * (1 - c)


lower_jaw = [v for v in main if verts[v][2] < mouth_z - 0.15 and verts[v][1] < -1.0 and abs(verts[v][0]) < 4.0]
Pj = verts[lower_jaw]
jaw_test = {}
for deg in (8.0, 12.0):
    mv = np.array([rot_about(p, pivL, axis, -math.radians(deg)) for p in Pj])
    disp = np.linalg.norm(mv - Pj, axis=1)
    jaw_test[str(int(deg))] = {"max_disp": float(disp.max()), "chin_disp": float(disp[Pj[:, 2].argmin()])}
print("JAW", [round(float(x), 4) for x in pivL], "test", {k: [round(v["max_disp"], 3), round(v["chin_disp"], 3)]
                                                       for k, v in jaw_test.items()})

out = {
    "schema": "round3_face_regions.v1",
    "source": {
        "psk": os.path.join(MODEL, "R2T1JinxiMd10011.psk"),
        "face_texture": FACE_TEX, "eye_texture": EYE_TEX,
        "vertices": int(slots["verts"]), "triangles": int(slots["polys"]),
        "materials": len(names), "bones": int(slots["bones"]),
    },
    "coordinate_space": {
        "frame": "PSK 导入后的 Blender 世界坐标：+Z 向上，-Y 为面部朝向，+X 为角色左侧",
        "units": "cm", "model_scale": SCALE,
        "note": "以下数值均为缩放前原始值；乘以 0.915502 得到 build5 流水线成品尺度",
    },
    "materials": slots["slots"],
    "slot_vertex_overlap": {"pairs": overlap, "nonzero_pairs": int(sum(1 for v in overlap.values() if v > 0))},
    "head_bone": {
        "name": "Bip001Head", "parent": "Bip001Neck",
        "matrix_local": head_m.tolist(), "origin": head_m[:3, 3].tolist(),
        "axes_world": axes,
        "local_axes_semantics": "局部 X 轴约等于世界 +Z（向上）；局部 Y 轴约等于世界 -Y（面朝方向）；局部 Z 轴约等于世界 +X（角色左侧）",
    },
    "eye_aperture": {
        "rim_L": rimL, "rim_R": rimR,
        "height": float(verts[rimL][:, 2].max() - verts[rimL][:, 2].min()),
        "width": float(verts[rimL][:, 0].max() - verts[rimL][:, 0].min()),
        "center_L": [float(x) for x in verts[rimL].mean(axis=0)],
        "center_R": [float(x) for x in verts[rimR].mean(axis=0)],
        "upper_margin_L": blink["L"]["margin"], "lower_margin_L": blink["L"]["lower"],
        "upper_margin_R": blink["R"]["margin"], "lower_margin_R": blink["R"]["lower"],
    },
    "mouth_vertices": lip_band,
    "mouth_region_vertices": mouth_region,
    "mouth_lip_colored_vertices": lip_near,
    "mouth_upper_lip": upper_lip,
    "mouth_lower_lip": lower_lip,
    "mouth_center": [float(x) for x in apP.mean(axis=0)],
    "mouth_width": mouth_width,
    "mouth_aperture": {
        "rim": apv,
        "width": float(apP[:, 0].max() - apP[:, 0].min()),
        "z_range": [float(apP[:, 2].min()), float(apP[:, 2].max())],
        "y_range": [float(apP[:, 1].min()), float(apP[:, 1].max())],
    },
    "mouth_corners": {
        "left": [float(x) for x in verts[corner_v[0]]],
        "right": [float(x) for x in verts[corner_v[1]]],
        "left_vertex": int(corner_v[0]), "right_vertex": int(corner_v[1]),
    },
    "jaw_pivot": {
        "left": pivL.tolist(), "right": pivR.tolist(), "axis": axis.tolist(),
        "head_local_left": pivL_local.tolist(), "head_local_right": pivR_local.tolist(),
        "derivation": {
            "half_head_width": half_w, "ear_centroid_L": ear_c["L"], "ear_centroid_R": ear_c["R"],
            "mouth_line_z": mouth_z, "chin_bottom": chin_bottom.tolist(),
            "rules": ["pivot_x = 0.72 * half_head_width", "pivot_y = ear_centroid_y - 0.9",
                      "pivot_z = mouth_line_z + 1.8"],
        },
        "rotation_test_deg": jaw_test,
    },
    "upper_lid_vertices_L": sorted(int(v) for v in parts["upL"]),
    "lower_lid_vertices_L": sorted(int(v) for v in parts["loL"]),
    "upper_lid_vertices_R": sorted(int(v) for v in parts["upR"]),
    "lower_lid_vertices_R": sorted(int(v) for v in parts["loR"]),
    "upper_lash_vertices_L": sorted(int(v) for v in parts["lashL"]),
    "upper_lash_vertices_R": sorted(int(v) for v in parts["lashR"]),
    "eye_crease_vertices_L": sorted(int(v) for v in parts["creaseL"]),
    "eye_crease_vertices_R": sorted(int(v) for v in parts["creaseR"]),
    "blink": {
        "direction": [0.0, -TRAVEL_Y, -TRAVEL_Z],
        "direction_note": "世界 -Z 为主（向下），叠加 -Y 0.20 cm 前推，越出眼球球面",
        "amplitude_max": TRAVEL_Z,
        "weights_L": {str(k): v for k, v in sorted(blink["L"]["weights"].items())},
        "weights_R": {str(k): v for k, v in sorted(blink["R"]["weights"].items())},
        "margin_weight_range": [blink["L"]["w_min"], blink["L"]["w_max"]],
        "closure_dz_mean_L": blink["L"]["dz_mean"], "closure_dz_absmax_L": blink["L"]["dz_abs_max"],
        "closure_dz_mean_R": blink["R"]["dz_mean"], "closure_dz_absmax_R": blink["R"]["dz_abs_max"],
        "travel_max_L": blink["L"]["travel_max"], "travel_max_R": blink["R"]["travel_max"],
        "ring_counts_L": blink["L"]["up_rings"], "ring_counts_R": blink["R"]["up_rings"],
        "lower_ring_counts_L": blink["L"]["lo_rings"], "lower_ring_counts_R": blink["R"]["lo_rings"],
    },
    "eyeball_L": {
        "center": parts["eyeball"]["L"]["center_dome"],
        "radius": float(max(np.linalg.norm(verts[v] - np.array(parts["eyeball"]["L"]["center_dome"])) for v in parts["eyeball"]["L"]["verts"])),
        "sphere_fit_radius": parts["eyeball"]["L"]["radius_fit"],
        "vertices": [int(v) for v in parts["eyeball"]["L"]["verts"]],
        "z_range": parts["eyeball"]["L"]["z_range"],
        "y_thickness": parts["eyeball"]["L"]["y_thickness"],
        "pupil": pupil["L"],
    },
    "eyeball_R": {
        "center": parts["eyeball"]["R"]["center_dome"],
        "radius": float(max(np.linalg.norm(verts[v] - np.array(parts["eyeball"]["R"]["center_dome"])) for v in parts["eyeball"]["R"]["verts"])),
        "sphere_fit_radius": parts["eyeball"]["R"]["radius_fit"],
        "vertices": [int(v) for v in parts["eyeball"]["R"]["verts"]],
        "z_range": parts["eyeball"]["R"]["z_range"],
        "y_thickness": parts["eyeball"]["R"]["y_thickness"],
        "pupil": pupil["R"],
    },
}
os.makedirs(REP, exist_ok=True)
path = os.path.join(REP, "round3_face_regions.json")
with open(path, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print("OUT", path, os.path.getsize(path))
