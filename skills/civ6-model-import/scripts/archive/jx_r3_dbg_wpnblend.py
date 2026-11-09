import bpy
path = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx\weapon_rigged.blend"
with bpy.data.libraries.load(path) as (src, dst):
    print("OBJECTS", src.objects)
    print("MESHES", src.meshes)
    print("MATERIALS", src.materials)
    print("ARMATURES", src.armatures)
