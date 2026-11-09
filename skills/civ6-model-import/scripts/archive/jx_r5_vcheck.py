import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r5_vcheck")
os.makedirs(OUT, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
body = max([o for o in bpy.data.objects if o.type == 'MESH'], key=lambda o: len(o.data.vertices))
print("VCHECK mesh verts=%d slots=%d" % (len(body.data.vertices), len(body.data.materials)))

for slot in body.material_slots:
    mat = slot.material
    nodes = list(mat.node_tree.nodes) if mat and mat.use_nodes else []
    kinds = [n.type for n in nodes]
    tex = [n for n in nodes if n.type == 'TEX_IMAGE']
    has_alpha = any(n.type == 'BSDF_PRINCIPLED' and any(i.is_linked for i in n.inputs if i.name == 'Alpha') for n in nodes)
    print("VCHECK MAT %-34s nodes=%s images=%d alpha_link=%s" % (
        mat.name if mat else "None", ",".join(sorted(set(kinds))) or "-", len(tex), has_alpha))

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 900
scene.render.resolution_y = 1200
scene.render.film_transparent = False
cam_data = bpy.data.cameras.new("VCAM")
cam = bpy.data.objects.new("VCAM", cam_data)
scene.collection.objects.link(cam)
cam.location = Vector((0.0, -105.0, 108.0))
cam.rotation_euler = (1.5708, 0.0, 0.0)
cam_data.lens = 85
scene.camera = cam
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.06, 1.0)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = 1.2
bpy.ops.object.light_add(type='AREA', location=(0.0, -80.0, 160.0))
bpy.context.object.data.energy = 40000
bpy.context.object.data.size = 80
scene.render.filepath = os.path.join(OUT, "import_check.png")
bpy.ops.render.render(write_still=True)
print("VCHECK_DONE", scene.render.filepath)
