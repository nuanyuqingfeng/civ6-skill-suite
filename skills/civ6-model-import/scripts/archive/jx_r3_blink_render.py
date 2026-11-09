import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_face as rig

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
TEX = os.path.join(ROOT, "Jinzhou_Jinhsi", "Textures")
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r3render")
SCALE = 0.915502
DOWN = float(os.environ.get("R3_BLINK_CM", "1.55"))
rig.BLINK_DOWN_CM = DOWN

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
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()

parts = rig.load_parts()
rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)
rig.pose_face(arm, {"blink_L": 1.0, "blink_R": 1.0})
bpy.context.view_layer.update()

for idx, slot in enumerate(body.data.materials):
    base, opa = MAP.get(slot.name, (None, None))
    mat = bpy.data.materials.new("R3_" + slot.name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.65
    if base and os.path.exists(os.path.join(TEX, base + ".dds")):
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
scene.render.resolution_x = 1100
scene.render.resolution_y = 1100
scene.view_settings.view_transform = 'Standard'
world = bpy.data.worlds.new("R3W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.06, 0.06, 0.07, 1)
for pos, energy in (((-0.6, -1.2, 1.7), 900), ((0.6, -1.2, 1.6), 600), ((0.0, -1.6, 1.3), 400)):
    light = bpy.data.lights.new("L", 'AREA')
    light.energy = energy
    light.size = 0.6
    lamp = bpy.data.objects.new("L", light)
    lamp.location = pos
    lamp.rotation_euler = (Vector((0, 0, 1.3)) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(lamp)

dg = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(dg)
me = ev.to_mesh()
idx = {g.index for g in body.vertex_groups if g.name in ("JX_Eye_L", "JX_Eye_R")}
pts = [ev.matrix_world @ v.co for v in me.vertices if any(g.group in idx and g.weight > 0.5 for g in v.groups)]
ev.to_mesh_clear()
mid = sum(pts, Vector((0.0, 0.0, 0.0))) / len(pts)

cam_data = bpy.data.cameras.new("C")
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 0.16
cam = bpy.data.objects.new("C", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam.location = mid + Vector((0.0, -0.6, 0.0))
cam.rotation_euler = (mid - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = os.path.join(OUT, "blink_%0.2f.png" % DOWN)
bpy.ops.render.render(write_still=True)
print("BLINK_RENDER_DONE", scene.render.filepath)
