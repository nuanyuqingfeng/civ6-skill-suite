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
ACTION_FBX = os.path.join(ROOT, "workspace", "gen", "jinhsi_fbx", os.environ.get("R3_ACTION", "JX_DeclareWarHuman") + ".fbx")
VIEW = os.environ.get("R3_VIEW", "full")
WEAPON = os.path.join(ROOT, "workspace", "gen", "jinhsi_fbx", "weapon_rigged.blend")
FRAME = int(os.environ.get("R3_FRAME", "60"))

MAP = {
    "MI_R2T1JinxiMd10011Bangs": ("JINHSI_BANGS_BASECOLOR", "JINHSI_BANGS_OPACITY"),
    "MI_R2T1JinxiMd10011Hair": ("MI_R2T1JinxiMd10011Hair_BaseColor", None),
    "MI_R2T1JinxiMd10011Face": ("MI_R2T1JinxiMd10011Face_BaseColor", None),
    "MI_R2T1JinxiMd10011Down": ("MI_R2T1JinxiMd10011Down_BaseColor", None),
    "MI_R2T1JinxiMd10011Skirt": ("MI_R2T1JinxiMd10011Skirt_BaseColor", "JINHSI_LEADER_OPACITY_CLOTH"),
    "MI_R2T1JinxiMd10011Eye": ("MI_R2T1JinxiMd10011Eye_BaseColor", None),
    "MI_R2T1JinxiMd10011Weapon": ("MI_R2T1JinxiMd10011Weapon_BaseColor", None),
    "MI_6XingStar": (None, None),
}

os.makedirs(OUT, exist_ok=True)
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

rig.join_weapon(body, WEAPON)
parts = rig.load_parts()
rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)

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

bpy.ops.import_scene.fbx(filepath=ACTION_FBX)
anim_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o is not arm][0]
action = anim_arm.animation_data.action
slot = anim_arm.animation_data.action_slot
bpy.data.objects.remove(anim_arm, do_unlink=True)
if arm.animation_data is None:
    arm.animation_data_create()
arm.animation_data.action = action
if slot is not None:
    arm.animation_data.action_slot = slot

scene = bpy.context.scene
scene.frame_set(FRAME)
bpy.context.view_layer.update()

scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.film_transparent = False
scene.render.resolution_x = 1100
scene.render.resolution_y = 1100
scene.view_settings.view_transform = 'Standard'
world = bpy.data.worlds.new("R3W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.06, 0.06, 0.07, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
for pos, energy in (((-60, -120, 170), 900), ((60, -120, 160), 600), ((0, -160, 130), 400)):
    light = bpy.data.lights.new("L", 'AREA')
    light.energy = energy
    light.size = 60
    lamp = bpy.data.objects.new("L", light)
    lamp.location = pos
    lamp.rotation_euler = (Vector((0, 0, 126)) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(lamp)
cam_data = bpy.data.cameras.new("C")
cam_data.type = 'ORTHO'
cam = bpy.data.objects.new("C", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
if VIEW == "face":
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    idx = {g.index for g in body.vertex_groups if g.name in ("JX_Eye_L", "JX_Eye_R")}
    pts = [ev.matrix_world @ v.co for v in me.vertices if any(g.group in idx and g.weight > 0.5 for g in v.groups)]
    ev.to_mesh_clear()
    mid = sum(pts, Vector((0.0, 0.0, 0.0))) / len(pts)
    cam_data.ortho_scale = 0.16
    target = mid
    cam.location = target + Vector((0.0, -0.6, 0.0))
else:
    cam_data.ortho_scale = 1.7
    target = Vector((0.0, 0.0, 0.78))
    cam.location = target + Vector((0.0, -3.2, 0.06))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = os.path.join(OUT, "r3_%s_%s_%d.png" % (os.environ.get("R3_ACTION", "JX_DeclareWarHuman"), VIEW, FRAME))
bpy.ops.render.render(write_still=True)
print("WAR_RENDER_DONE", scene.render.filepath)
