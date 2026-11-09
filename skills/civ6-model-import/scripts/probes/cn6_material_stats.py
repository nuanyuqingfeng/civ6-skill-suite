import sys

import bpy

PATH = r"E:\SoftWares\civ6_nexus_work\ysj2_stage\LEAD_Jinhsi_QYQXP.cn6"
bpy.ops.preferences.addon_enable(module="io_import_cn6")
bpy.ops.import_shape.cn6(filepath=PATH)

for ob in bpy.data.objects:
    if ob.type != "MESH":
        continue
    me = ob.data
    names = [m.name for m in me.materials]
    print("OBJ", ob.name, "verts", len(me.vertices), "faces", len(me.polygons), "mats", len(names))
    stats = {}
    for p in me.polygons:
        nm = names[p.material_index] if p.material_index < len(names) else "?"
        s = stats.setdefault(nm, {"faces": 0, "zmin": 1e9, "zmax": -1e9, "zsum": 0.0, "n": 0, "away": 0})
        s["faces"] += 1
        n = p.normal
        if n.y > 0.0:
            s["away"] += 1
        for vi in p.vertices:
            z = me.vertices[vi].co.z
            s["zmin"] = min(s["zmin"], z)
            s["zmax"] = max(s["zmax"], z)
            s["zsum"] += z
            s["n"] += 1
    for nm, s in stats.items():
        print("MAT %-38s faces=%5d zmin=%.2f zmax=%.2f zmean=%.2f backfaces=%d" % (
            nm, s["faces"], s["zmin"], s["zmax"], s["zsum"] / s["n"], s["away"]))
    break
