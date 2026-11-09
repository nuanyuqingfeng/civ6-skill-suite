import bpy
p = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx\JX_IDLE.fbx"
bpy.ops.import_scene.fbx(filepath=p)
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
print("ARMS", [(a.name, len(a.data.bones)) for a in arms])
print("JX", [b.name for a in arms for b in a.data.bones if b.name.startswith("JX_")])
