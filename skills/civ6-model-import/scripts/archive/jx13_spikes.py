import os
import statistics

import bpy

MODEL_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
PSK = os.path.join(MODEL_DIR, "R2T1JinxiMd10011.psk")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.armatures):
    for item in list(block):
        block.remove(item, do_unlink=True)

bpy.ops.import_scene.psk(filepath=PSK)
body = None
for o in bpy.data.objects:
    if o.type == 'MESH' and len(o.data.vertices) > 100:
        body = o
print("MESH", body.name, "verts", len(body.data.vertices), "polys", len(body.data.polygons),
      "slots", len(body.material_slots))

me = body.data
lengths = []
slot_of_edge = []
for poly in me.polygons:
    ids = list(poly.vertices)
    for i in range(len(ids)):
        a = ids[i]
        b = ids[(i + 1) % len(ids)]
        va = me.vertices[a].co
        vb = me.vertices[b].co
        lengths.append((va - vb).length)
        slot_of_edge.append(poly.material_index)

lengths_sorted = sorted(lengths)
n = len(lengths_sorted)
median = lengths_sorted[n // 2]
print("EDGES", n, "median", round(median, 6),
      "p99", round(lengths_sorted[int(n * 0.99)], 6),
      "max", round(lengths_sorted[-1], 6))

for mult in (10, 20, 50):
    cnt = sum(1 for x in lengths if x > median * mult)
    print("OVER_%dx" % mult, cnt)

limit = median * 20
slot_counts = {}
worst = []
for idx, length in enumerate(lengths):
    if length > limit:
        s = slot_of_edge[idx]
        slot_counts[s] = slot_counts.get(s, 0) + 1
print("SLOT_OVER_20X", sorted(slot_counts.items()))

for poly in me.polygons:
    ids = list(poly.vertices)
    mx = 0.0
    for i in range(len(ids)):
        a = ids[i]
        b = ids[(i + 1) % len(ids)]
        mx = max(mx, (me.vertices[a].co - me.vertices[b].co).length)
    if mx > limit:
        worst.append((round(mx, 4), poly.material_index, poly.index))

worst.sort(reverse=True)
print("WORST_TRIS", worst[:10])
print("SPIKE_DONE")
