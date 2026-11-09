import json
import os
from collections import deque

import bpy
import numpy as np
from mathutils import Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
TMP = os.path.join(ROOT, "workspace", "tmp", "r5_vcheck")
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r5_vcheck")
RES_X, RES_Y = 1200, 1600

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)

CAMERAS = {
    "01_front_full": ((7.0, -300.0, 78.0), (7.0, 0.0, 78.0), 50.0),
    "02_chest_closeup": ((0.0, -113.0, 107.0), (0.0, -6.8, 107.0), 85.0),
    "03_cuff_closeup": ((30.5, -57.5, 93.0), (30.5, -5.5, 93.0), 85.0),
    "04_chest_alpha_off": ((0.0, -113.0, 107.0), (0.0, -6.8, 107.0), 85.0),
}


def make_camera(loc, target, lens):
    data = bpy.data.cameras.new("C")
    data.lens = lens
    data.sensor_fit = 'VERTICAL'
    data.sensor_height = 36.0
    ob = bpy.data.objects.new("C", data)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()
    return ob


def load_rgba(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(h, w, 4)


def pixel_ray(cam, px, py, w, h):
    half_h = 18.0 / cam.data.lens
    half_w = half_h * w / h
    u = (px + 0.5) / w * 2.0 - 1.0
    v = 1.0 - (py + 0.5) / h * 2.0
    return (cam.matrix_world.to_3x3() @ Vector((u * half_w, v * half_h, -1.0))).normalized()


depsgraph = bpy.context.evaluated_depsgraph_get()


def locate(cam, px, py, w, h):
    hit, loc, normal, index, obj, matrix = bpy.context.scene.ray_cast(
        depsgraph, cam.matrix_world.translation, pixel_ray(cam, px, py, w, h))
    return [round(float(loc.x), 2), round(float(loc.y), 2), round(float(loc.z), 2)] if hit else None


def comps(mask, q=4, min_area=60):
    h, w = mask.shape
    hs, ws = h // q, w // q
    small = mask[:hs * q, :ws * q].reshape(hs, q, ws, q).mean(axis=(1, 3)) > 0.5
    label = np.zeros(small.shape, dtype=np.int32)
    res = []
    cur = 0
    for y in range(hs):
        for x in range(ws):
            if small[y, x] and label[y, x] == 0:
                cur += 1
                label[y, x] = cur
                dq = deque([(y, x)])
                pts = []
                while dq:
                    cy, cx = dq.popleft()
                    pts.append((cy, cx))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < hs and 0 <= nx < ws and small[ny, nx] and label[ny, nx] == 0:
                            label[ny, nx] = cur
                            dq.append((ny, nx))
                if len(pts) >= min_area:
                    arr = np.array(pts)
                    res.append({
                        "area_px": int(len(pts) * q * q),
                        "bbox_px_topleft": [int(arr[:, 1].min() * q), int((hs - 1 - arr[:, 0].max()) * q),
                                             int(arr[:, 1].max() * q), int((hs - 1 - arr[:, 0].min()) * q)],
                        "centroid_px_topleft": [round(float(arr[:, 1].mean() * q), 1), round(float((hs - 1 - arr[:, 0].mean()) * q), 1)],
                    })
    res.sort(key=lambda c: -c["area_px"])
    return res[:6]


report = {}
for tag, (loc, target, lens) in CAMERAS.items():
    cam = make_camera(loc, target, lens)
    bpy.context.scene.camera = cam
    alpha = load_rgba(os.path.join(TMP, tag + "_alpha_opaque.png"))[:, :, 3]
    h, w = alpha.shape
    bg = alpha < 0.02
    visited = np.zeros_like(bg)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if bg[y, x] and not visited[y, x]:
                visited[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if bg[y, x] and not visited[y, x]:
                visited[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and bg[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                dq.append((ny, nx))
    enclosed = bg & ~visited
    entry = {"coverage": round(float((alpha > 0.5).mean()), 4), "enclosed_gap_px": int(enclosed.sum()), "gaps": []}
    for c in comps(enclosed):
        c["world_at_centroid"] = locate(cam, c["centroid_px_topleft"][0], c["centroid_px_topleft"][1], w, h)
        entry["gaps"].append(c)
    report[tag] = entry

with open(os.path.join(TMP, "gaps.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("GAPS " + json.dumps(report, ensure_ascii=False))
