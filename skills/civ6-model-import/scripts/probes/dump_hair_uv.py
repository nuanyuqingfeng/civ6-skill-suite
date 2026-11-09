import sys
import bpy
import addon_utils

# 用法：blender -b --python dump_hair_uv.py -- <cn6 路径> <输出 tsv> <材质名片段> <组名:骨骼1,骨骼2,...> [<组名:骨骼...> ...]
args = sys.argv[sys.argv.index("--") + 1:]
cn6, out, mat_key = args[0], args[1], args[2]
groups = {}
for spec in args[3:]:
    name, bones = spec.split(":", 1)
    for bone in bones.split(","):
        groups[bone.strip()] = name

bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("io_import_cn6", default_set=True, persistent=True)
bpy.ops.import_shape.cn6(filepath=cn6)

count = 0
with open(out, "w", encoding="utf-8") as fh:
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        slots = [s.material.name if s.material else "" for s in ob.material_slots]
        want = [i for i, n in enumerate(slots) if mat_key in n]
        if not want:
            continue
        me = ob.data
        layer = me.uv_layers.active
        if layer is None:
            continue
        uv = layer.data
        vgn = {g.index: g.name for g in ob.vertex_groups}
        for poly in me.polygons:
            if poly.material_index not in want or len(poly.loop_indices) < 3:
                continue
            acc = {}
            for vi in poly.vertices:
                for g in me.vertices[vi].groups:
                    acc[g.group] = acc.get(g.group, 0.0) + g.weight
            if not acc:
                continue
            bone = vgn.get(max(acc, key=acc.get), "")
            group = groups.get(bone)
            if group is None:
                continue
            pts = [uv[li].uv for li in poly.loop_indices]
            for t in range(1, len(pts) - 1):
                tri = (pts[0], pts[t], pts[t + 1])
                fh.write("%s\t%.6f\t%.6f\t%.6f\t%.6f\t%.6f\t%.6f\n" % (
                    group, tri[0].x, tri[0].y, tri[1].x, tri[1].y, tri[2].x, tri[2].y))
                count += 1
print("UV_TRIS", count, out)
