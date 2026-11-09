# 可调参数：只改下面两个常量即可
SCALE_FACTOR = 1.0   # 整体缩放系数：模型相对固定取景框的大小倍数
YAW_DEG = 0.0        # 朝向角：模型绕垂直轴旋转的角度（度），正值自俯视看逆时针
USE_MATERIAL_OPACITY = True  # 开关：按材质 .mtl 引用的 Opacity 贴图决定透明度

import bpy
import bmesh
import json
import math
import numpy
import os
from xml.etree import ElementTree
from mathutils import Vector

PROJECT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi"
OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\reports\render2"
MTL_DIR = os.path.join(PROJECT_DIR, "Materials")
OPACITY_TEX_DIR = os.path.join(PROJECT_DIR, "Textures")
MODEL_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
TEX_ROOT = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role"
PSK = os.path.join(MODEL_DIR, "R2T1JinxiMd10011.psk")

RES_X = 1024
RES_Y = 1536
ASPECT = RES_Y / RES_X
BG_GRAY = 0.86
MARGIN = 1.12             # 取景框相对被摄范围的外扩倍数
CUTOUT_MIN = 0.05         # 贴图透明占比下限：低于该值的贴图按不透明渲染
CUTOUT_MAX = 0.95         # 透明占比上限：高于该值的贴图 alpha 与可见性无关，按不透明渲染
WIRE_THICKNESS = 0.12     # 贴图缺失时的线框粗细（厘米）

# 视图：方位角自正前方（-Y 一侧）起算，正值转向角色右侧
VIEWS = (
    ("front", "正面", 0.0, "body"),
    ("right45", "右侧 45 度", 45.0, "body"),
    ("side", "正侧面", 90.0, "body"),
    ("head", "头肩特写", 0.0, "head"),
)
LIGHT_DIRS = (
    ((0.55, 0.75, -0.65), 4.0),   # 主光：自前左上方照向模型
    ((-0.80, 0.25, -0.30), 1.6),  # 辅光：自右侧补光
    ((0.10, -0.85, -0.45), 2.6),  # 轮廓光：自后方顶部
)

os.makedirs(OUT_DIR, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
    for item in list(block):
        block.remove(item, do_unlink=True)

bpy.ops.import_scene.psk(filepath=PSK)
arm_a = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = None
for o in bpy.data.objects:
    if o.type == 'MESH' and len(o.data.vertices) > 100:
        body = o
body.name = "JinhsiBody"
if body.data.shape_keys:
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.shape_key_remove(all=True)

VERT_COUNT = len(body.data.vertices)
BONE_COUNT = len(arm_a.data.bones)

# 贴图索引：材质名 MI_xxx 对应 T_xxx_D.png
TEXTURES = {}
for folder, _, files in os.walk(TEX_ROOT):
    for f in files:
        if f.lower().endswith(".png"):
            TEXTURES[f] = os.path.join(folder, f)


def texture_of(mat_name):
    stem = mat_name[len("MI_"):] if mat_name.startswith("MI_") else mat_name
    return TEXTURES.get("T_" + stem + "_D.png") or TEXTURES.get(stem + "_D.png")


def opacity_texture_of(mat_name):
    path = os.path.join(MTL_DIR, mat_name + ".mtl")
    if not os.path.exists(path):
        return None
    for value in ElementTree.parse(path).getroot().iter("Element"):
        if value.find("m_ParamName").get("text") == "Opacity":
            name = value.find("m_ObjectName").get("text")
            return os.path.join(OPACITY_TEX_DIR, name + ".dds") if name else None
    return None


def opacity_image(path):
    loaded = bpy.data.images.load(path, check_existing=True)
    loaded.colorspace_settings.name = 'Non-Color'
    buf = numpy.empty(len(loaded.pixels), dtype=numpy.float32)
    loaded.pixels.foreach_get(buf)
    source = buf.reshape(-1, 4)
    # 单通道贴图的值只落在红色通道，颜色转数值时按亮度取用，需要先把三个颜色通道写成同值
    rgba = numpy.empty_like(source)
    rgba[:, 0] = source[:, 0]
    rgba[:, 1] = source[:, 0]
    rgba[:, 2] = source[:, 0]
    rgba[:, 3] = 1.0
    # EEVEE 采样 DDS 原始数据时取到全黑，改把解码结果写进内存图像后再接入节点
    image = bpy.data.images.new(os.path.basename(path), width=loaded.size[0],
                                height=loaded.size[1], alpha=False)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(rgba.ravel())
    image.update()
    return image


def transparent_fraction(image):
    buf = numpy.empty(len(image.pixels), dtype=numpy.float32)
    image.pixels.foreach_get(buf)
    return float((buf[3::4] < 0.5).mean())


def solid_material(name, rgba):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    out = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.9
    mat.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def cut_mask(links, nodes, socket):
    cut = nodes.new("ShaderNodeMath")
    cut.operation = 'GREATER_THAN'
    cut.inputs[1].default_value = 0.5
    links.new(socket, cut.inputs[0])
    return cut.outputs["Value"]


def textured_material(name, path, fraction, opacity):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.75
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    links = mat.node_tree.links
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    masks = []
    if CUTOUT_MIN < fraction < CUTOUT_MAX:
        # 发片类贴图用二值截断保留硬边，半透明不产生噪点
        masks.append(cut_mask(links, nodes, tex.outputs["Alpha"]))
    if opacity is not None:
        opa = nodes.new("ShaderNodeTexImage")
        opa.image = opacity
        masks.append(cut_mask(links, nodes, opa.outputs["Color"]))
    if masks:
        mask = masks[0]
        for value in masks[1:]:
            mult = nodes.new("ShaderNodeMath")
            mult.operation = 'MULTIPLY'
            links.new(mask, mult.inputs[0])
            links.new(value, mult.inputs[1])
            mask = mult.outputs["Value"]
        links.new(mask, bsdf.inputs["Alpha"])
        mat.surface_render_method = 'DITHERED'
    return mat, bool(masks)


MISSING = []
MATERIAL_ROWS = []
for index, slot in enumerate(body.material_slots):
    old = slot.material
    path = texture_of(old.name)
    if path is None:
        MISSING.append(index)
        slot.material = solid_material(old.name, (0.62, 0.36, 0.72, 1.0))
        MATERIAL_ROWS.append((old.name, "缺失", "-", "-", "纯色加线框"))
        continue
    fraction = transparent_fraction(bpy.data.images.load(path, check_existing=True))
    opacity_path = opacity_texture_of(old.name) if USE_MATERIAL_OPACITY else None
    opacity = None
    if opacity_path is not None:
        opacity = opacity_image(opacity_path)
    slot.material, cut = textured_material(old.name, path, fraction, opacity)
    MATERIAL_ROWS.append((old.name, os.path.basename(path), "%.4f" % fraction,
                          os.path.basename(opacity_path) if opacity_path else "-",
                          "alpha 截断" if cut else "不透明"))


def add_wire_overlay(mat_index):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    dead = [f for f in bm.faces if f.material_index != mat_index]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    wire_mesh = bpy.data.meshes.new(body.data.name + "_wire")
    bm.to_mesh(wire_mesh)
    bm.free()
    wire = bpy.data.objects.new("JxWire", wire_mesh)
    bpy.context.collection.objects.link(wire)
    wire.matrix_world = body.matrix_world.copy()
    mod = wire.modifiers.new("wire", 'WIREFRAME')
    mod.thickness = WIRE_THICKNESS
    mod.use_replace = True
    wire_mesh.materials.clear()
    wire_mesh.materials.append(solid_material("JxWireMat", (0.05, 0.05, 0.05, 1.0)))
    return wire


root = bpy.data.objects.new("JxRoot", None)
bpy.context.collection.objects.link(root)
for ob in (arm_a, body):
    ob.parent = root
    ob.parent_type = 'OBJECT'

for direction, energy in LIGHT_DIRS:
    lamp = bpy.data.lights.new("JxSun", 'SUN')
    lamp.energy = energy
    lamp.angle = math.radians(12.0)
    ob = bpy.data.objects.new("JxSun", lamp)
    bpy.context.collection.objects.link(ob)
    ob.rotation_euler = Vector(direction).normalized().to_track_quat('-Z', 'Y').to_euler()
    ob.parent = root
    ob.parent_type = 'OBJECT'

world = bpy.data.worlds.new("JxWorld")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (BG_GRAY, BG_GRAY, BG_GRAY, 1.0)
bg.inputs["Strength"].default_value = 0.9

for index in MISSING:
    add_wire_overlay(index)

root.rotation_euler = (0.0, 0.0, math.radians(YAW_DEG))
root.scale = (SCALE_FACTOR, SCALE_FACTOR, SCALE_FACTOR)
bpy.context.view_layer.update()

LOCAL = [v.co.copy() for v in body.data.vertices]
base_lo = [min(v[i] for v in LOCAL) for i in range(3)]
base_hi = [max(v[i] for v in LOCAL) for i in range(3)]
base_h = base_hi[2] - base_lo[2]


def frame_height(low, high):
    span = [high[i] - low[i] for i in range(3)]
    horiz = math.hypot(span[0], span[1])
    return max(span[2], horiz * ASPECT) * MARGIN


# 全身取景：以缩放系数 1.0 的包围盒为准，模型按 SCALE_FACTOR 缩放后落在框内
body_center = Vector([(base_lo[i] + base_hi[i]) * 0.5 for i in range(3)])
body_frame_h = frame_height(base_lo, base_hi)

# 头肩取景：头骨位置以上的全部顶点构成头部范围，取景框按该范围外扩
head_bone_z = arm_a.data.bones["Bip001Head"].head_local.z
head_lo = [min(v[i] for v in LOCAL if v[2] >= head_bone_z) for i in range(3)]
head_hi = [max(v[i] for v in LOCAL if v[2] >= head_bone_z) for i in range(3)]
head_center = Vector([(head_lo[i] + head_hi[i]) * 0.5 for i in range(3)])
head_frame_h = max(head_hi[2] - head_lo[2],
                   max(head_hi[0] - head_lo[0], head_hi[1] - head_lo[1]) * ASPECT) * MARGIN

cam_data = bpy.data.cameras.new("JxCam")
cam_data.type = 'ORTHO'
cam_data.clip_start = 1.0
cam_data.clip_end = 5000.0
cam = bpy.data.objects.new("JxCam", cam_data)
bpy.context.collection.objects.link(cam)

scene = bpy.context.scene
scene.camera = cam
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = RES_X
scene.render.resolution_y = RES_Y
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.compression = 15
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.eevee.taa_render_samples = 64
# 关闭时间戳类元数据，使重复运行得到字节一致的 PNG
for flag in ("use_stamp", "use_stamp_date", "use_stamp_time", "use_stamp_render_time",
             "use_stamp_frame", "use_stamp_frame_range", "use_stamp_camera", "use_stamp_lens",
             "use_stamp_scene", "use_stamp_marker", "use_stamp_note", "use_stamp_filename",
             "use_stamp_hostname", "use_stamp_memory", "use_stamp_sequencer_strip",
             "use_stamp_labels"):
    setattr(scene.render, flag, False)

DIST = 800.0
SHOTS = []
for key, label, azimuth, kind in VIEWS:
    az = math.radians(azimuth)
    local_target = body_center if kind == "body" else head_center
    target = root.matrix_world @ local_target
    cam_data.ortho_scale = body_frame_h if kind == "body" else head_frame_h
    cam.location = target + Vector((math.sin(az) * DIST, -math.cos(az) * DIST, 0.0))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    path = os.path.join(OUT_DIR, key + ".png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    SHOTS.append((key, label, azimuth, kind, path, os.path.getsize(path)))

SCALED = [(body.matrix_world @ v).to_tuple() for v in LOCAL]
cur_lo = [min(v[i] for v in SCALED) for i in range(3)]
cur_hi = [max(v[i] for v in SCALED) for i in range(3)]

cmd = "BLENDER_USER_RESOURCES=E:/SoftWares/blender45/userres " \
      "E:/SoftWares/blender45/blender-4.5.9-windows-x64/blender.exe -b --python-exit-code 1 " \
      "--python workspace/_tools/jx_render.py"

lines = [
    "# 今汐模型渲染",
    "",
    "| 项目 | 数值 |",
    "| --- | --- |",
    "| 顶点数 | %d |" % VERT_COUNT,
    "| 骨数 | %d |" % BONE_COUNT,
    "| 包围盒 X 跨度（厘米，缩放系数 1.0） | %.3f |" % (base_hi[0] - base_lo[0]),
    "| 包围盒 Y 跨度（厘米，缩放系数 1.0） | %.3f |" % (base_hi[1] - base_lo[1]),
    "| 包围盒 Z 跨度（厘米，缩放系数 1.0） | %.3f |" % (base_hi[2] - base_lo[2]),
    "| 包围盒 X 跨度（厘米，缩放后） | %.3f |" % (cur_hi[0] - cur_lo[0]),
    "| 包围盒 Y 跨度（厘米，缩放后） | %.3f |" % (cur_hi[1] - cur_lo[1]),
    "| 包围盒 Z 跨度（厘米，缩放后） | %.3f |" % (cur_hi[2] - cur_lo[2]),
    "| 当前缩放系数 | %s |" % SCALE_FACTOR,
    "| 当前朝向角（度） | %s |" % YAW_DEG,
    "| 取景框高度（全身，厘米） | %.3f |" % body_frame_h,
    "| 取景框高度（头肩特写，厘米） | %.3f |" % head_frame_h,
    "| 分辨率 | %d × %d |" % (RES_X, RES_Y),
    "| 渲染引擎 | EEVEE |",
    "| 缺贴图材质 | %s |" % (", ".join(r[0] for r in MATERIAL_ROWS if r[1] == "缺失") or "无"),
    "| 按材质读取 Opacity 贴图 | %s |" % ("开启" if USE_MATERIAL_OPACITY else "关闭"),
    "",
    "## 材质与贴图",
    "",
    "| 材质 | 贴图 | alpha 透明占比 | Opacity 贴图 | 处理方式 |",
    "| --- | --- | --- | --- | --- |",
]
for name, tex, fraction, opacity, decision in MATERIAL_ROWS:
    lines.append("| %s | %s | %s | %s | %s |" % (name, tex, fraction, opacity, decision))
lines += [
    "",
    "## 视图",
    "",
    "| 视图 | 方位角 | 取景框高度（厘米） | 文件名 | 字节数 |",
    "| --- | --- | --- | --- | --- |",
]
for key, label, azimuth, kind, path, size in SHOTS:
    frame = body_frame_h if kind == "body" else head_frame_h
    lines.append("| %s | %g 度 | %.3f | %s | %d |" % (label, azimuth, frame, os.path.basename(path), size))
lines += [
    "",
    "## 复现",
    "",
    "渲染与退出码记录分成两步：第二步把本次运行的退出码追加到本文件末尾。",
    "",
    "```bash",
    "cd \"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi\"",
    cmd + "; printf '%s\\n' $? >> workspace/gen/reports/render2/index.md",
    "```",
    "",
    "退出码：",
]
with open(os.path.join(OUT_DIR, "index.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

print("RENDER_STATS " + json.dumps({
    "verts": VERT_COUNT,
    "bones": BONE_COUNT,
    "base_spans": [round(base_hi[i] - base_lo[i], 3) for i in range(3)],
    "scaled_spans": [round(cur_hi[i] - cur_lo[i], 3) for i in range(3)],
    "scale": SCALE_FACTOR,
    "yaw": YAW_DEG,
    "body_frame_h": round(body_frame_h, 3),
    "head_frame_h": round(head_frame_h, 3),
    "materials": MATERIAL_ROWS,
    "shots": {k: s for k, _, _, _, _, s in SHOTS},
}))
