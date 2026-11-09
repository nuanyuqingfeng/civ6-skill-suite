import bpy
from mathutils import Matrix

CN6 = r"E:\SoftWares\civ6_nexus_work\jinhsi_fbx\LEAD_Jinhsi_QYQXP.cn6"

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
    for item in list(block):
        block.remove(item, do_unlink=True)

bpy.ops.import_shape.cn6(filepath=CN6)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
head = arm.data.bones.get('Bip001Head')
print("ROUNDTRIP2 head_world=", [round(c, 2) for c in (arm.matrix_world @ head.head_local)])
print("ROUNDTRIP2 DONE")
