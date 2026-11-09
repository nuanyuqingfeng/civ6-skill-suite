import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx\JX_IDLE.fbx")
print("OBJ", [(o.name, o.type, len(o.data.vertices) if o.type == 'MESH' else '-') for o in bpy.data.objects], flush=True)
print("MESHES", [(m.name, len(m.vertices)) for m in bpy.data.meshes], flush=True)
print("ARMS", [(a.name, len(a.bones)) for a in bpy.data.armatures], flush=True)
