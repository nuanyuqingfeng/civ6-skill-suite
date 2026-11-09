import bpy, os
PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
body = None
for o in bpy.data.objects:
    if o.type == 'MESH' and len(o.data.vertices) > 100:
        body = o
names = [m.name for m in body.data.materials]
print("MATS", len(names))
for i, n in enumerate(names):
    vs = set()
    for p in body.data.polygons:
        if p.material_index == i:
            for vi in p.vertices:
                vs.add(vi)
    zs = [body.data.vertices[v].co.z for v in vs]
    ys = [body.data.vertices[v].co.y for v in vs]
    print("MAT", i, n, "verts", len(vs), "Z", round(min(zs), 4), round(max(zs), 4), "Ymin", round(min(ys), 4))
allz = [v.co.z for v in body.data.vertices]
print("BBOX_Z", round(min(allz), 4), round(max(allz), 4), "SPAN", round(max(allz) - min(allz), 4))
print("BONES", len([b for b in bpy.data.objects if b.type == 'ARMATURE'][0].data.bones))
print("MATZ_DONE")
