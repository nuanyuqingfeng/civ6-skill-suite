import os

import bpy

import sys

CN6 = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else r"E:\SoftWares\civ6_nexus_work\ysj2_stage\LEAD_Jinhsi_QYQXP.cn6"
TEX = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Yusanjia\Jinzhou_Yusanjia\Textures"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()
for block in list(bpy.data.meshes):
    bpy.data.meshes.remove(block)

bpy.ops.preferences.addon_enable(module="io_import_cn6")
bpy.ops.import_shape.cn6(filepath=CN6)

hooked = 0
for ob in bpy.data.objects:
    if ob.type != "MESH":
        continue
    for slot in ob.material_slots:
        mat = slot.material
        if mat is None:
            continue
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        path = os.path.join(TEX, mat.name + "_BaseColor.dds")
        if not os.path.exists(path):
            continue
        image = bpy.data.images.load(path, check_existing=True)
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        hooked += 1

for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.shading.type = "MATERIAL"

print("GUI_IMPORT hooked", hooked, "objects", len(bpy.data.objects))
