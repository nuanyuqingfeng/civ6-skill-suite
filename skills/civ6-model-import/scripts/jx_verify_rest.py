import bpy
from mathutils import Matrix

CN6_JX = r"E:\SoftWares\civ6_nexus_work\jinhsi_fbx\LEAD_Jinhsi_QYQXP.cn6"
CN6_DNY = r"D:\desktop\mods-CIV6\others\Denia_Pack\Denia_Pack\Geometries\DaniyaModelGeo.fgx"


def clean():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for blk in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
        for it in list(blk):
            blk.remove(it, do_unlink=True)


def report(cn6_path, tag):
    clean()
    bpy.ops.import_shape.cn6(filepath=cn6_path)
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    head = arm.data.bones.get('Bip001Head')
    pelvis = arm.data.bones.get('Bip001Pelvis')
    root = arm.data.bones.get('Root')
    hw = arm.matrix_world @ head.head_local
    pw = arm.matrix_world @ pelvis.head_local
    print(tag, "arm_name=", arm.name, "scale=", [round(c, 4) for c in arm.scale])
    print(tag, "head_world=", [round(c, 2) for c in hw])
    print(tag, "pelvis_world=", [round(c, 2) for c in pw])
    # Root 骨的方向（rest）：head->tail 向量
    print(tag, "root_vec=", [round(c, 2) for c in (root.tail_local - root.head_local)])
    # 全骨包围盒
    import mathutils
    mn = mathutils.Vector((1e9, 1e9, 1e9))
    mx = mathutils.Vector((-1e9, -1e9, -1e9))
    for b in arm.data.bones:
        w = arm.matrix_world @ b.head_local
        for i in range(3):
            mn[i] = min(mn[i], w[i])
            mx[i] = max(mx[i], w[i])
    print(tag, "bounds_min=", [round(c, 1) for c in mn], "bounds_max=", [round(c, 1) for c in mx])
    print(tag, "DONE")


report(CN6_DNY, "DENIA")
report(CN6_JX, "JINXI")
