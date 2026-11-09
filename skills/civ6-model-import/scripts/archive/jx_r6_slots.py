import bpy
import os
from mathutils import Vector

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
print("PSK_EXISTS", os.path.exists(PSK))

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials):
    for item in list(block):
        block.remove(item, do_unlink=True)

bpy.ops.import_scene.psk(filepath=PSK)
body = None
for o in bpy.data.objects:
    if o.type == 'MESH' and len(o.data.vertices) > 100:
        body = o
print("BODY", body.name, len(body.data.vertices), len(body.data.polygons))
print("SLOTS", [s.material.name if s.material else None for s in body.material_slots])

me = body.data
mw = body.matrix_world
for idx, slot in enumerate(body.material_slots):
    name = slot.material.name if slot.material else "-"
    polys = [p for p in me.polygons if p.material_index == idx]
    if not polys:
        print("MAT", idx, name, "polys=0")
        continue
    vs = set()
    xs = []
    ys = []
    zs = []
    for p in polys:
        for vi in p.vertices:
            vs.add(vi)
    for vi in vs:
        co = mw @ me.vertices[vi].co
        xs.append(co.x)
        ys.append(co.y)
        zs.append(co.z)
    print("MAT", idx, name, "polys=", len(polys), "verts=", len(vs),
          "x=", round(min(xs), 2), round(max(xs), 2),
          "y=", round(min(ys), 2), round(max(ys), 2),
          "z=", round(min(zs), 2), round(max(zs), 2))
print("PROBE_OK")
