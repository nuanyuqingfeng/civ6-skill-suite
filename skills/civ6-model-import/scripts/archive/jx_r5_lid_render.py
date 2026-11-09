import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_face as rig

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
TEX = os.path.join(ROOT, "Jinzhou_Jinhsi", "Textures")
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r5_vcheck")
SCALE = 0.915502
NAME = os.environ.get("R5_OUT", "blink_after.png")
os.makedirs(OUT, exist_ok=True)

if os.environ.get("R5_TAPER") == "off":
    rig._lid_taper = lambda dx, ctr_x: 1.0
    rig.LOWER_LID_RATIO = 0.18

MAP = {
    "MI_R2T1JinxiMd10011Bangs": ("JINHSI_BANGS_BASECOLOR", "JINHSI_BANGS_OPACITY"),
    "MI_R2T1JinxiMd10011Hair": ("MI_R2T1JinxiMd10011Hair_BaseColor", None),
    "MI_R2T1JinxiMd10011Face": ("MI_R2T1JinxiMd10011Face_BaseColor", None),
    "MI_R2T1JinxiMd10011Down": ("MI_R2T1JinxiMd10011Down_BaseColor", None),
    "MI_R2T1JinxiMd10011Skirt": ("MI_R2T1JinxiMd10011Skirt_BaseColor", "JINHSI_LEADER_OPACITY_CLOTH"),
    "MI_R2T1JinxiMd10011Eye": ("MI_R2T1JinxiMd10011Eye_BaseColor", None),
    "MI_6XingStar": (None, None),
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

parts = rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)
rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}

pose_world = {b.name: b.matrix_local.copy() for b in arm.data.bones if b.name.startswith("JX_")}
rig.pose_face(pose_world, {"blink_L": 1.0, "blink_R": 1.0}, rest)
inv = {b.name: b.matrix_local.inverted() for b in arm.data.bones}
for v in body.data.vertices:
    acc = Vector()
    for g in v.groups:
        name = body.vertex_groups[g.group].name
        m = pose_world.get(name)
        acc += g.weight * (v.co if m is None else ((m @ inv[name]) @ v.co))
    v.co = acc
for mod in body.modifiers:
    mod.show_render = False
    mod.show_viewport = False
print("SKIN_SUM_Z", round(sum(v.co.z for v in body.data.vertices), 3))
if os.environ.get("R5_FACE_ONLY") == "1":
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(body.data)
    keep = {i for i, m in enumerate(body.data.materials) if "Face" in m.name or "Eye" in m.name}
    bmesh.ops.delete(bm, geom=[fc for fc in bm.faces if fc.material_index not in keep], context='FACES')
    bm.to_mesh(body.data)
    bm.free()
body.data.update()
bpy.context.view_layer.update()

for idx, slot in enumerate(body.data.materials):
    base, opa = MAP.get(slot.name, (None, None))
    mat = bpy.data.materials.new("R5_" + slot.name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.62
    if base:
        img = bpy.data.images.load(os.path.join(TEX, base + ".dds"))
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        if opa:
            io = bpy.data.images.load(os.path.join(TEX, opa + ".dds"))
            to = nt.nodes.new("ShaderNodeTexImage")
            to.image = io
            nt.links.new(to.outputs["Color"], bsdf.inputs["Alpha"])
            mat.blend_method = 'CLIP'
            mat.alpha_threshold = 0.5
    body.data.materials[idx] = mat

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.eevee.taa_render_samples = 48
scene.render.resolution_x = 1200
scene.render.resolution_y = 600
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'Standard'
world = bpy.data.worlds.new("R5W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.10, 0.10, 0.11, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.8

eyeL = rig._eye_center(parts, "L")
eyeR = rig._eye_center(parts, "R")
mid = (eyeL + eyeR) * 0.5
for pos, energy in (((mid.x - 22.0, mid.y - 40.0, mid.z + 26.0), 900),
                    ((mid.x + 22.0, mid.y - 40.0, mid.z + 18.0), 600),
                    ((mid.x, mid.y - 30.0, mid.z - 16.0), 420)):
    light = bpy.data.lights.new("L", 'AREA')
    light.energy = energy
    light.size = 22
    lamp = bpy.data.objects.new("L", light)
    lamp.location = pos
    lamp.rotation_euler = (mid - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(lamp)

cam_data = bpy.data.cameras.new("R5CAM")
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 10.4
cam = bpy.data.objects.new("R5CAM", cam_data)
scene.collection.objects.link(cam)
target = Vector((0.0, mid.y, mid.z))
cam.location = target + Vector((0.0, -50.0, 0.0))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam
scene.render.filepath = os.path.join(OUT, NAME)
bpy.ops.render.render(write_still=True)
print("LID_RENDER_DONE", scene.render.filepath, "ortho", cam_data.ortho_scale, "target", [round(v, 3) for v in target])
