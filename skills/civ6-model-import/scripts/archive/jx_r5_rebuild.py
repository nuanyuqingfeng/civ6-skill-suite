import json
import os
from collections import deque

import bpy
import numpy as np
from mathutils import Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
TEX = os.path.join(ROOT, "Jinzhou_Jinhsi", "Textures")
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r5_vcheck")
TMP = os.path.join(ROOT, "workspace", "tmp", "r5_vcheck")
os.makedirs(OUT, exist_ok=True)
os.makedirs(TMP, exist_ok=True)
RES_X, RES_Y = 1200, 1600

TEXTURE_MAP = {
    "Bangs": ("MI_R2T1JinxiMd10011Bangs_BaseColor.dds", "JINHSI_BANGS_OPACITY.dds"),
    "Hair": ("MI_R2T1JinxiMd10011Hair_BaseColor.dds", "MI_R2T1JinxiMd10011Hair_Opacity.dds"),
    "Face": ("MI_R2T1JinxiMd10011Face_BaseColor.dds", None),
    "Down": ("MI_R2T1JinxiMd10011Down_BaseColor.dds", None),
    "Skirt": ("MI_R2T1JinxiMd10011Skirt_BaseColor.dds", "JINHSI_LEADER_OPACITY_CLOTH.dds"),
    "Eye": ("MI_R2T1JinxiMd10011Eye_BaseColor.dds", None),
    "6XingStar": ("MI_6XingStar_BaseColor.dds", None),
}
CLOTH_KEYS = {"Skirt", "Down"}

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
body = max([o for o in bpy.data.objects if o.type == 'MESH'], key=lambda o: len(o.data.vertices))


def material_key(mat):
    if mat.name.startswith("MI_R2T1JinxiMd10011"):
        return mat.name[len("MI_R2T1JinxiMd10011"):]
    return mat.name[len("MI_"):]


def alpha_stats(image):
    w, h = image.size
    px = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(px)
    a = px.reshape(-1, 4)[:, 3]
    return {"size": [w, h], "min": round(float(a.min()), 4), "max": round(float(a.max()), 4),
            "mean": round(float(a.mean()), 4), "below_0.5": round(float((a < 0.5).mean()), 4)}


wired = []
texture_stats = {}
for slot in body.material_slots:
    mat = slot.material
    key = material_key(mat)
    base_name, opacity_name = TEXTURE_MAP[key]
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.location = (520, 0)
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (220, 0)
    bsdf.inputs['Roughness'].default_value = 0.55
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.location = (-320, 120)
    tex.image = bpy.data.images.load(os.path.join(TEX, base_name), check_existing=True)
    tex.image.colorspace_settings.name = 'sRGB'
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    alpha_out = tex.outputs['Alpha']
    alpha_desc = "BaseColor.Alpha"
    texture_stats[base_name] = alpha_stats(tex.image)
    if opacity_name:
        optex = nt.nodes.new('ShaderNodeTexImage')
        optex.location = (-320, -220)
        optex.image = bpy.data.images.load(os.path.join(TEX, opacity_name), check_existing=True)
        optex.image.colorspace_settings.name = 'Non-Color'
        mul = nt.nodes.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        mul.location = (-40, -80)
        nt.links.new(tex.outputs['Alpha'], mul.inputs[0])
        nt.links.new(optex.outputs['Alpha'], mul.inputs[1])
        alpha_out = mul.outputs[0]
        alpha_desc = "BaseColor.Alpha * %s.Alpha" % opacity_name
        texture_stats[opacity_name] = alpha_stats(optex.image)
    nt.links.new(alpha_out, bsdf.inputs['Alpha'])
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    mat.blend_method = 'BLEND'
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = 'BLENDED'
    if hasattr(mat, "use_transparency_overlap"):
        mat.use_transparency_overlap = False
    links = []
    for lk in nt.links:
        links.append("%s.%s -> %s.%s" % (lk.from_node.type, lk.from_socket.name, lk.to_node.type, lk.to_socket.name))
    wired.append({
        "slot": slot.name,
        "material": mat.name,
        "basecolor": base_name,
        "opacity": opacity_name,
        "alpha_expr": alpha_desc,
        "blend_method": mat.blend_method,
        "links": links,
    })
print("WIRE " + json.dumps(wired, ensure_ascii=False))

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 64
scene.cycles.use_adaptive_sampling = True
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.cycles.transparent_max_bounces = 16
scene.render.resolution_x = RES_X
scene.render.resolution_y = RES_Y
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = 0.0

scene.world.use_nodes = True
bg = scene.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.16, 0.16, 0.17, 1.0)
bg.inputs[1].default_value = 1.0


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def add_area(name, loc, target, size, energy):
    data = bpy.data.lights.new(name, type='AREA')
    data.shape = 'SQUARE'
    data.size = size
    data.energy = energy
    ob = bpy.data.objects.new(name, data)
    scene.collection.objects.link(ob)
    ob.location = loc
    aim(ob, target)
    return ob


add_area("KEY", (70, -150, 190), (0, 0, 105), 110, 14000)
add_area("FILL", (-90, -140, 110), (0, 0, 100), 160, 6000)
add_area("RIM", (-20, 130, 180), (0, 0, 120), 90, 9000)


def add_camera(name, loc, target, lens):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.sensor_fit = 'VERTICAL'
    data.sensor_height = 36.0
    ob = bpy.data.objects.new(name, data)
    scene.collection.objects.link(ob)
    ob.location = loc
    aim(ob, target)
    return ob


CAM_FULL = ((7.0, -300.0, 78.0), (7.0, 0.0, 78.0), 50.0)
CAM_CHEST = ((0.0, -113.0, 107.0), (0.0, -6.8, 107.0), 85.0)
CAM_CUFF = ((30.5, -57.5, 93.0), (30.5, -5.5, 93.0), 85.0)
cam_full = add_camera("CAM_FULL", *CAM_FULL)
cam_chest = add_camera("CAM_CHEST", *CAM_CHEST)
cam_cuff = add_camera("CAM_CUFF", *CAM_CUFF)
VIEWS = [("01_front_full", cam_full), ("02_chest_closeup", cam_chest), ("03_cuff_closeup", cam_cuff)]


def frame_extent(cam):
    target = Vector(CAM_FULL[1]) if cam is cam_full else Vector(CAM_CHEST[1]) if cam is cam_chest else Vector(CAM_CUFF[1])
    d = (target - cam.location).length
    half_h = 18.0 / cam.data.lens * d
    return {"distance": round(d, 1), "height_world": round(2 * half_h, 1), "width_world": round(2 * half_h * RES_X / RES_Y, 1)}


def render(path, cam, transparent, samples):
    scene.camera = cam
    scene.render.film_transparent = transparent
    scene.cycles.samples = samples
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


out_files = []
for tag, cam in VIEWS:
    render(os.path.join(OUT, tag + ".png"), cam, False, 96)
    out_files.append(tag + ".png")
alpha_blend = {}
for tag, cam in VIEWS:
    alpha_blend[tag] = render(os.path.join(TMP, tag + "_alpha_blend.png"), cam, True, 16)

for slot in body.material_slots:
    nt = slot.material.node_tree
    bsdf = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    for lk in list(nt.links):
        if lk.to_node == bsdf and lk.to_socket.name == 'Alpha':
            nt.links.remove(lk)
    bsdf.inputs['Alpha'].default_value = 1.0
    slot.material.blend_method = 'OPAQUE'
    if hasattr(slot.material, "surface_render_method"):
        slot.material.surface_render_method = 'DITHERED'

render(os.path.join(OUT, "04_chest_alpha_off.png"), cam_chest, False, 96)
out_files.append("04_chest_alpha_off.png")
alpha_off = {}
for tag, cam in VIEWS + [("04_chest_alpha_off", cam_chest)]:
    alpha_off[tag] = render(os.path.join(TMP, tag + "_alpha_opaque.png"), cam, True, 16)

for slot in body.material_slots:
    if material_key(slot.material) in CLOTH_KEYS:
        continue
    nt = slot.material.node_tree
    out_node = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    for lk in list(nt.links):
        if lk.to_node == out_node:
            nt.links.remove(lk)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    nt.links.new(tr.outputs[0], out_node.inputs['Surface'])

cloth_mask = {}
for tag, cam in VIEWS:
    cloth_mask[tag] = render(os.path.join(TMP, tag + "_cloth_mask.png"), cam, True, 16)


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
    d_cam = Vector((u * half_w, v * half_h, -1.0))
    return (cam.matrix_world.to_3x3() @ d_cam).normalized()


depsgraph = bpy.context.evaluated_depsgraph_get()


def locate(cam, px, py, w, h):
    origin = cam.matrix_world.translation
    direction = pixel_ray(cam, px, py, w, h)
    hit, loc, normal, index, obj, matrix = scene.ray_cast(depsgraph, origin, direction)
    if not hit:
        return None
    return [round(float(loc.x), 2), round(float(loc.y), 2), round(float(loc.z), 2)]


def components(mask, q=4, min_area=50):
    h, w = mask.shape
    hs, ws = h // q, w // q
    small = mask[:hs * q, :ws * q].reshape(hs, q, ws, q).mean(axis=(1, 3)) > 0.5
    label = np.zeros(small.shape, dtype=np.int32)
    comps = []
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
                    comps.append({
                        "area_px": int(len(pts) * q * q),
                        "bbox_px_topleft": [int(arr[:, 1].min() * q), int((hs - 1 - arr[:, 0].max()) * q),
                                             int(arr[:, 1].max() * q), int((hs - 1 - arr[:, 0].min()) * q)],
                        "centroid_px_topleft": [round(float(arr[:, 1].mean() * q), 1), round(float((hs - 1 - arr[:, 0].mean()) * q), 1)],
                    })
    comps.sort(key=lambda c: -c["area_px"])
    return comps[:8]


analysis = {}
for tag, cam in VIEWS:
    blend = load_rgba(alpha_blend[tag])
    opaque = load_rgba(alpha_off[tag])
    cloth = load_rgba(cloth_mask[tag])
    h, w = blend.shape[0], blend.shape[1]
    ab = blend[:, :, 3]
    ao = opaque[:, :, 3]
    ac = cloth[:, :, 3]
    body_cov = ao > 0.5
    alpha_holes = (ao > 0.9) & (ab < 0.5)
    missing_cloth = body_cov & (ac < 0.5)
    entry = {
        "frame": frame_extent(cam),
        "coverage_body": round(float(body_cov.mean()), 4),
        "coverage_cloth": round(float((ac > 0.5).mean()), 4),
        "alpha_hole_px": int(alpha_holes.sum()),
        "alpha_partial_px": int(((ao > 0.9) & (ab >= 0.5) & (ab < 0.95)).sum()),
        "missing_cloth_px": int(missing_cloth.sum()),
        "missing_cloth_comps": [],
        "alpha_hole_comps": [],
    }
    for c in components(missing_cloth, min_area=100):
        c["world_at_centroid"] = locate(cam, c["centroid_px_topleft"][0], c["centroid_px_topleft"][1], w, h)
        entry["missing_cloth_comps"].append(c)
    for c in components(alpha_holes, min_area=30):
        c["world_at_centroid"] = locate(cam, c["centroid_px_topleft"][0], c["centroid_px_topleft"][1], w, h)
        entry["alpha_hole_comps"].append(c)
    analysis[tag] = entry

color_b = load_rgba(os.path.join(OUT, "02_chest_closeup.png"))
color_o = load_rgba(os.path.join(OUT, "04_chest_alpha_off.png"))
diff_rgb = np.abs(color_b[:, :, :3] - color_o[:, :, :3]).mean(axis=2)
mask = diff_rgb > 0.02
hc, wc = mask.shape
cmp_entry = {
    "pixels_diff_gt_0.02": int(mask.sum()),
    "max_color_diff": round(float(diff_rgb.max()), 4),
    "mean_color_diff": round(float(diff_rgb.mean()), 5),
    "coverage_px_delta": int(((load_rgba(alpha_blend["02_chest_closeup"])[:, :, 3] > 0.5) != (load_rgba(alpha_off["02_chest_closeup"])[:, :, 3] > 0.5)).sum()),
}
if mask.any():
    rows, cols = np.nonzero(mask)
    cmp_entry["diff_bbox_px_topleft"] = [int(cols.min()), int(hc - 1 - rows.max()), int(cols.max()), int(hc - 1 - rows.min())]
    cmp_entry["diff_centroid_world"] = locate(cam_chest, float(cols.mean()), float(hc - 1 - rows.mean()), wc, hc)
analysis["chest_compare"] = cmp_entry

stats = {
    "resolution": [RES_X, RES_Y],
    "engine": scene.render.engine,
    "samples": 96,
    "materials": wired,
    "texture_alpha": texture_stats,
    "alpha_analysis": analysis,
    "outputs": out_files,
}
with open(os.path.join(TMP, "measure.json"), "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)
print("ANALYSIS " + json.dumps(analysis, ensure_ascii=False))
print("REBUILD_DONE")
