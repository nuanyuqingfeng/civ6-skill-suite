import math
import os

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
import sys
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_face as rig

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
TEX = os.path.join(ROOT, "Jinzhou_Jinhsi", "Textures")
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r9")
SCALE = 0.915502
LEVELS = ((0.35, "035"), (0.70, "070"), (1.00, "100"))
os.makedirs(OUT, exist_ok=True)

TEXTURE_MAP = {
    "Bangs": ("MI_R2T1JinxiMd10011Bangs_BaseColor.dds", "JINHSI_BANGS_OPACITY.dds"),
    "Hair": ("MI_R2T1JinxiMd10011Hair_BaseColor.dds", "MI_R2T1JinxiMd10011Hair_Opacity.dds"),
    "Face": ("MI_R2T1JinxiMd10011Face_BaseColor.dds", None),
    "Down": ("MI_R2T1JinxiMd10011Down_BaseColor.dds", None),
    "Skirt": ("MI_R2T1JinxiMd10011Skirt_BaseColor.dds", "JINHSI_LEADER_OPACITY_CLOTH.dds"),
    "Eye": ("MI_R2T1JinxiMd10011Eye_BaseColor.dds", None),
    "6XingStar": ("MI_6XingStar_BaseColor.dds", None),
}

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = max([o for o in bpy.data.objects if o.type == 'MESH'], key=lambda o: len(o.data.vertices))

bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
arm.scale = (SCALE, SCALE, SCALE)
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
body.data.transform(Matrix.Scale(SCALE, 4))
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()

parts = rig.load_parts()
rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)

rest_all = {b.name: b.matrix_local.copy() for b in arm.data.bones}
gname = {g.index: g.name for g in body.vertex_groups}
rest_co = [v.co.copy() for v in body.data.vertices]
shape_key = body.data.shape_keys.key_blocks["MORPH_BASE"]
pose_world = {n: rest_all[n].copy() for n in rest_all if n.startswith("JX_")}
base_world = {n: pose_world[n].copy() for n in pose_world}
for m in list(body.modifiers):
    if m.type == 'ARMATURE':
        body.modifiers.remove(m)

for slot in body.material_slots:
    mat = slot.material
    key = mat.name[len("MI_R2T1JinxiMd10011"):] if mat.name.startswith("MI_R2T1JinxiMd10011") else mat.name[3:]
    base_name, opacity_name = TEXTURE_MAP[key]
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.55
    bsdf.location = (220, 0)
    out.location = (520, 0)
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.location = (-320, 120)
    tex.image = bpy.data.images.load(os.path.join(TEX, base_name), check_existing=True)
    tex.image.colorspace_settings.name = 'sRGB'
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    alpha_out = tex.outputs['Alpha']
    if opacity_name:
        optex = nt.nodes.new('ShaderNodeTexImage')
        optex.location = (-320, -220)
        optex.image = bpy.data.images.load(os.path.join(TEX, opacity_name), check_existing=True)
        optex.image.colorspace_settings.name = 'Non-Color'
        mul = nt.nodes.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        nt.links.new(tex.outputs['Alpha'], mul.inputs[0])
        nt.links.new(optex.outputs['Alpha'], mul.inputs[1])
        alpha_out = mul.outputs[0]
    nt.links.new(alpha_out, bsdf.inputs['Alpha'])
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 64
scene.cycles.use_adaptive_sampling = True
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.cycles.transparent_max_bounces = 16
scene.render.resolution_x = 1200
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
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


add_area("KEY", (26, -42, 130), (0, -2.9, 124), 45, 1100)
add_area("FILL", (-30, -40, 126), (0, -2.9, 124), 60, 460)
add_area("RIM", (-8, 26, 140), (0, 0, 126), 40, 600)

cam_data = bpy.data.cameras.new("CAM_MOUTH")
cam_data.lens = 85.0
cam_data.sensor_fit = 'VERTICAL'
cam_data.sensor_height = 36.0
cam = bpy.data.objects.new("CAM_MOUTH", cam_data)
scene.collection.objects.link(cam)
cam.location = Vector((0.0, -27.0, 124.9))
aim(cam, (0.0, -2.9, 123.95))
scene.camera = cam
print("IMG_CAM", [round(v, 4) for v in cam.location])

for level, tag in LEVELS:
    for n in pose_world:
        pose_world[n] = base_world[n].copy()
    rig.pose_face(pose_world, {"jaw": level}, rest_all)
    dl = {n: pose_world[n] @ rest_all[n].inverted() for n in pose_world}
    for i, v in enumerate(body.data.vertices):
        w = [(gname[g.group], g.weight) for g in v.groups]
        keep = 1.0 - sum(x for k, x in w if k in dl)
        p = rest_co[i] * keep
        for k, x in w:
            if k in dl:
                p = p + (dl[k] @ rest_co[i]) * x
        shape_key.data[i].co = p
    body.data.update()
    bpy.context.view_layer.update()
    zs = [shape_key.data[i].co.z for i in (6264, 5824, 7686, 7683)]
    print("IMG_DBG", tag, level, [round(v, 4) for v in zs],
          "bbox_z", round(min(v.co.z for v in body.data.vertices), 3),
          round(max(v.co.z for v in body.data.vertices), 3))
    path = os.path.join(OUT, "mouth_%s.png" % tag)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("IMG_DONE", tag, level, path)
print("IMG_ALL_DONE")
