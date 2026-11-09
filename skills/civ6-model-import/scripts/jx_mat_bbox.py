import bpy
import os

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
body = [o for o in bpy.data.objects if o.type == 'MESH' and len(o.data.vertices) > 100][0]
names = [m.name for m in body.data.materials]
print("MATS", names)

verts = body.data.vertices
slot = {n: [] for n in names}
for poly in body.data.polygons:
    n = names[poly.material_index]
    for vi in poly.vertices:
        slot[n].append(vi)

allz = [v.co.z for v in verts]
print("MESH_Z", round(min(allz), 4), round(max(allz), 4), round(max(allz) - min(allz), 4))
for n in names:
    idx = sorted(set(slot[n]))
    zs = [verts[i].co.z for i in idx]
    xs = [verts[i].co.x for i in idx]
    print("SLOT", n, "verts", len(idx),
          "Z", round(min(zs), 4), round(max(zs), 4),
          "X", round(min(xs), 4), round(max(xs), 4))
print("MAT_BBOX_DONE")
