import json
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
MODE = os.environ.get("R3_POSE", "all")

MAP = {
    "MI_R2T1JinxiMd10011Bangs": ("JINHSI_BANGS_BASECOLOR", "JINHSI_BANGS_OPACITY"),
    "MI_R2T1JinxiMd10011Hair": ("MI_R2T1JinxiMd10011Hair_BaseColor", None),
    "MI_R2T1JinxiMd10011Face": ("MI_R2T1JinxiMd10011Face_BaseColor", None),
    "MI_R2T1JinxiMd10011Down": ("MI_R2T1JinxiMd10011Down_BaseColor", None),
    "MI_R2T1JinxiMd10011Skirt": ("MI_R2T1JinxiMd10011Skirt_BaseColor", "JINHSI_LEADER_OPACITY_CLOTH"),
    "MI_R2T1JinxiMd10011Eye": ("MI_R2T1JinxiMd10011Eye_BaseColor", None),
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
body.data.transform(Matrix.Scale(SCALE, 4))
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()

parts = rig.build_face_rig(arm, body)
BIND = {pb.name: pb.matrix.copy() for pb in arm.pose.bones}
rig.apply_weights(body, parts)
rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
eyeL = rig._eye_center(parts, "L")
eyeR = rig._eye_center(parts, "R")
centers = {
    "eye_L": eyeL, "eye_R": eyeR,
    "brow_center_L": sum((body.data.vertices[i].co for i in parts["browL"]), Vector()) / len(parts["browL"]),
    "brow_center_R": sum((body.data.vertices[i].co for i in parts["browR"]), Vector()) / len(parts["browR"]),
}

for idx, slot in enumerate(body.data.materials):
    base, opa = MAP.get(slot.name, (None, None))
    mat = bpy.data.materials.new("R3_" + slot.name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.62
    if base:
        img = bpy.data.images.load(os.path.join(TEX, base + ".dds"))
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        if opa and not (os.environ.get("R3_SOLID_BANGS") and "Bangs" in slot.name):
            override = os.environ.get("R3_BANGS_DDS") if "Bangs" in slot.name else None
            io = bpy.data.images.load(override or os.path.join(TEX, opa + ".dds"))
            to = nt.nodes.new("ShaderNodeTexImage")
            to.image = io
            nt.links.new(to.outputs["Color"], bsdf.inputs["Alpha"])
            mat.blend_method = 'CLIP'
            mat.alpha_threshold = 0.5
    body.data.materials[idx] = mat

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'Standard'
world = bpy.data.worlds.new("R3W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.12, 0.12, 0.13, 1)
for pos, energy in (((-50, -90, 160), 2600), ((50, -90, 155), 1600), ((0, -120, 120), 1100)):
    light = bpy.data.lights.new("L", 'AREA')
    light.energy = energy
    light.size = 50
    lamp = bpy.data.objects.new("L", light)
    lamp.location = pos
    lamp.rotation_euler = (Vector((0, 0, 126)) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(lamp)
cam_data = bpy.data.cameras.new("C")
cam_data.type = 'ORTHO'
cam_data.ortho_scale = float(os.environ.get("R3_ORTHO", "13.5"))
cam = bpy.data.objects.new("C", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
target = Vector((float(os.environ.get("R3_TX", "0.0")), -2.6, float(os.environ.get("R3_TZ", "126.4"))))
cam.location = target + Vector((0.0, -60.0, 0.0))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()

POSES = {
    "rest": {},
    "blink": {"blink_L": 1.0, "blink_R": 1.0},
    "jaw": {"jaw": 1.0},
    "gaze": {"gaze_L": 1.0, "gaze_R": 1.0},
    "talk": {"jaw": 0.55, "brow_L": 0.5, "brow_R": 0.5},
}


def skinned(pose_world):
    inv = {b.name: b.matrix_local.inverted() for b in arm.data.bones}
    out = []
    for v in body.data.vertices:
        acc = Vector()
        for g in v.groups:
            name = body.vertex_groups[g.group].name
            m = pose_world.get(name)
            acc += g.weight * (v.co if m is None else ((m @ inv[name]) @ v.co))
        out.append(acc)
    return out


def deform(params):
    pose_world = {b.name: b.matrix_local.copy() for b in arm.data.bones if b.name.startswith("JX_")}
    rig.pose_face(pose_world, params, rest)
    for pb in arm.pose.bones:
        if pb.name.startswith("JX_"):
            delta = pose_world[pb.name] @ rest[pb.name].inverted()
            pb.matrix = delta @ BIND[pb.name]
        else:
            pb.matrix = BIND[pb.name]
    bpy.context.view_layer.update()
    return skinned(pose_world)


def frame_camera(coords):
    pts = [coords[i] for i in parts["eyeball"]["L"]["verts"]]
    c = sum(pts, Vector()) / len(pts)
    size = (max(p.z for p in pts) - min(p.z for p in pts))
    target = Vector((0.0, c.y, c.z))
    cam_data.ortho_scale = float(os.environ.get("R3_ORTHO", "0")) or (size * 14.0)
    cam.location = target + Vector((0.0, -60.0, 0.0))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()


def report(name, coords):
    ap = [coords[i] for i in parts["mouth_ap"]]
    mid = sum(q.z for q in ap) / len(ap)
    upper = [p for p in ap if p.z >= mid]
    lower = [p for p in ap if p.z < mid]
    gap = sum(p.z for p in upper) / len(upper) - sum(p.z for p in lower) / len(lower)
    cov = []
    for side, ctr in (("L", eyeL), ("R", eyeR)):
        edge = [coords[i] for i in parts["upL" if side == "L" else "upR"] if abs(coords[i].x - ctr.x) < 0.6]
        cov.append(min(p.z for p in edge) - ctr.z if edge else 99.0)
    eb = [coords[i] for i in parts["eyeball"]["L"]["verts"]]
    front = min(eb, key=lambda p: p.y)
    print("CHECK", name, "mouth_gap", round(gap, 4),
          "lid_edge_minus_center_L", round(cov[0], 3), "R", round(cov[1], 3),
          "iris_front", [round(v, 3) for v in front])


for name, params in POSES.items() if MODE == "all" else [(MODE, POSES[MODE])]:
    c = deform(params)
    report(name, c)
    frame_camera(c)
    scene.render.filepath = os.path.join(OUT, "pose_" + name + ".png")
    bpy.ops.render.render(write_still=True)
print("FACE_TEST_DONE")