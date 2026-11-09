import bpy

PATH = r"E:\SoftWares\civ6_nexus_work\ysj2_stage\LEAD_Jinhsi_QYQXP.cn6"
bpy.ops.preferences.addon_enable(module="io_import_cn6")
bpy.ops.import_shape.cn6(filepath=PATH)

for ob in bpy.data.objects:
    if ob.type != "MESH" or ob.name.startswith("Cube"):
        continue
    me = ob.data
    print("OBJ", ob.name, "has_custom_normals", me.has_custom_normals)
    names = [m.name for m in me.materials]
    me.calc_loop_triangles()
    stats = {}
    for p in me.polygons:
        nm = names[p.material_index]
        s = stats.setdefault(nm, {"faces": 0, "flip": 0})
        s["faces"] += 1
        if p.loop_total:
            dot = 0.0
            for li in range(p.loop_start, p.loop_start + p.loop_total):
                n = me.loops[li].normal
                dot += n.x * p.normal.x + n.y * p.normal.y + n.z * p.normal.z
            dot /= p.loop_total
            if dot < 0.0:
                s["flip"] += 1
    for nm, s in stats.items():
        print("NORM %-38s faces=%5d corner_normal_opposite=%5d ratio=%.3f" % (nm, s["faces"], s["flip"], s["flip"] / s["faces"]))
    break
