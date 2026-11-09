import bpy
import os
from mathutils import Matrix

CN6 = r"E:\SoftWares\civ6_nexus_work\jinhsi_fbx\LEAD_Jinhsi_QYQXP.cn6"

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
    for item in list(block):
        block.remove(item, do_unlink=True)

bpy.ops.import_shape.cn6(filepath=CN6)

arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
print("CN6_IN arms:", [(a.name, len(a.data.bones)) for a in arms])
print("CN6_IN meshes:", [(m.name, len(m.data.vertices),
                          [s.name for s in m.material_slots][:2]) for m in meshes])
for a in arms:
    print("ARMATURE_OBJ matrix_world row-major:")
    for row in a.matrix_world:
        print("   ", [round(c, 4) for c in row])
    for bn in ("R2T1JinxiMd10011", "Root", "Bip001", "Bip001Pelvis", "Bip001Head"):
        b = a.data.bones.get(bn)
        if b:
            loc, rot, sc = b.matrix_local.decompose()
            print("BONE", bn, "local_pos=", [round(c, 3) for c in loc],
                  "local_quat=", [round(c, 4) for c in rot])
print("CN6_IMPORT_TEST_DONE")
