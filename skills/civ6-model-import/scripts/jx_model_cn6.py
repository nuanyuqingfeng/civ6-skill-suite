import bpy
import os

OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx"
MODEL_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
PSK = os.path.join(MODEL_DIR, "R2T1JinxiMd10011.psk")

os.makedirs(OUT_DIR, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
    for item in list(block):
        block.remove(item, do_unlink=True)

bpy.ops.import_scene.psk(filepath=PSK)
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
arm = arms[0]
body_mesh = None
for o in bpy.data.objects:
    if o.type == 'MESH' and len(o.data.vertices) > 100:
        body_mesh = o
print("MODEL_IN: bones=%d verts=%d" % (len(arm.data.bones), len(body_mesh.data.vertices)))

bpy.ops.object.select_all(action='DESELECT')
body_mesh.select_set(True)
bpy.context.view_layer.objects.active = body_mesh
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.separate(type='MATERIAL')
bpy.ops.object.mode_set(mode='OBJECT')

meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in meshes:
    slot = o.material_slots[0].name if o.material_slots else "NONE"
    short = slot.replace("MI_R2T1JinxiMd10011", "").replace("MI_", "")
    o.name = short if short else slot
    if o.data.shape_keys:
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.shape_key_remove(all=True)
print("MESH_SPLIT:", [(o.name, len(o.data.vertices)) for o in meshes])

cn6_path = os.path.join(OUT_DIR, "LEAD_Jinhsi_QYQXP.cn6")
bpy.ops.export_shape.cn6(filepath=cn6_path)
print("CN6_EXPORTED:", cn6_path)
