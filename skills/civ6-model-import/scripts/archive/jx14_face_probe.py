import bpy
import json
import math
import os

from mathutils import Vector

MODEL_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
PSK = os.path.join(MODEL_DIR, "R2T1JinxiMd10011.psk")
TMP = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\tmp"
OUT = os.path.join(TMP, "jx14_slots.json")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
    for item in list(block):
        block.remove(item, do_unlink=True)

bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
mesh = None
for o in bpy.data.objects:
    if o.type == 'MESH' and len(o.data.vertices) > 100:
        mesh = o
print("PROBE_OBJECTS", [(o.name, o.type) for o in bpy.data.objects])
print("PROBE_COUNTS", len(mesh.data.vertices), len(mesh.data.polygons), len(arm.data.bones))
print("PROBE_MESH_WORLD", [round(c, 6) for row in mesh.matrix_world for c in row])
print("PROBE_ARM_WORLD", [round(c, 6) for row in arm.matrix_world for c in row])

names = [m.name for m in mesh.data.materials]
print("PROBE_MATERIALS", names)
verts = [v.co.copy() for v in mesh.data.vertices]
slot_faces = {i: [] for i in range(len(names))}
for p in mesh.data.polygons:
    slot_faces[p.material_index].append(tuple(p.vertices))

uv_layer = mesh.data.uv_layers.active
print("PROBE_UV_LAYERS", [(l.name, l.active_render) for l in mesh.data.uv_layers])

slot_verts = {}
for i in range(len(names)):
    s = set()
    for f in slot_faces[i]:
        s.update(f)
    slot_verts[i] = sorted(s)

report = {"materials": names, "verts": len(mesh.data.vertices), "polys": len(mesh.data.polygons),
          "bones": len(arm.data.bones), "slots": {}}
for i, name in enumerate(names):
    pts = [verts[v] for v in slot_verts[i]]
    lo = [min(p[k] for p in pts) for k in range(3)]
    hi = [max(p[k] for p in pts) for k in range(3)]
    cen = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
    report["slots"][name] = {
        "index": i,
        "verts": len(slot_verts[i]),
        "faces": len(slot_faces[i]),
        "bbox_min": [round(v, 4) for v in lo],
        "bbox_max": [round(v, 4) for v in hi],
        "centroid": [round(v, 4) for v in cen],
    }
    print("PROBE_SLOT", i, name, "verts", len(slot_verts[i]), "faces", len(slot_faces[i]),
          "bbox", [round(v, 3) for v in lo], [round(v, 3) for v in hi])

share = {}
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        common = sorted(set(slot_verts[i]) & set(slot_verts[j]))
        share[names[i] + "|" + names[j]] = len(common)
print("PROBE_SHARE", json.dumps(share))

head = arm.data.bones["Bip001Head"]
parent = head.parent.name if head.parent else "-"
print("PROBE_HEAD_BONE", "parent", parent, "length", round(head.length, 4),
      "head_local", [round(v, 4) for v in head.head_local], "tail_local", [round(v, 4) for v in head.tail_local])
print("PROBE_HEAD_MATRIX", [[round(head.matrix_local[r][c], 6) for c in range(4)] for r in range(4)])

gidx = {g.index: g.name for g in mesh.vertex_groups}
head_group = [g.index for g in mesh.vertex_groups if g.name == "Bip001Head"]
print("PROBE_HEAD_GROUP", head_group, [gidx[i] for i in head_group])
hw = [0.0] * len(verts)
for v in mesh.data.vertices:
    for ge in v.groups:
        if ge.group in head_group:
            hw[v.index] = ge.weight
buckets = {"1.00": 0, "0.9-1.0": 0, "0.5-0.9": 0, "0.1-0.5": 0, "0.0-0.1": 0}
for w in hw:
    if w >= 0.999:
        buckets["1.00"] += 1
    elif w >= 0.9:
        buckets["0.9-1.0"] += 1
    elif w >= 0.5:
        buckets["0.5-0.9"] += 1
    elif w >= 0.1:
        buckets["0.1-0.5"] += 1
    elif w > 0.0:
        buckets["0.0-0.1"] += 1
print("PROBE_HEAD_WEIGHT_BUCKETS", buckets)
head_verts = [v.index for v in mesh.data.vertices if hw[v.index] >= 0.5]
hp = [verts[v] for v in head_verts]
print("PROBE_HEAD_REGION", len(head_verts),
      "bbox", [round(min(p[k] for p in hp), 3) for k in range(3)],
      [round(max(p[k] for p in hp), 3) for k in range(3)])

report["head_bone"] = {
    "name": "Bip001Head",
    "parent": parent,
    "length": round(head.length, 6),
    "head_local": [round(v, 6) for v in head.head_local],
    "tail_local": [round(v, 6) for v in head.tail_local],
    "matrix_local": [[round(head.matrix_local[r][c], 9) for c in range(4)] for r in range(4)],
}
report["head_region"] = {"count": len(head_verts), "buckets": buckets}

uv_faces = {}
loops = uv_layer.data
for i in range(len(names)):
    rec = []
    for p in mesh.data.polygons:
        if p.material_index != i:
            continue
        rec.append([[p.vertices[k], [round(loops[p.loop_start + k].uv[0], 6), round(loops[p.loop_start + k].uv[1], 6)]] for k in range(p.loop_total)])
    uv_faces[names[i]] = rec

face_name = "MI_R2T1JinxiMd10011Face"
eye_name = "MI_R2T1JinxiMd10011Eye"

def islands(slot_name):
    idx = names.index(slot_name)
    parent_uf = {}

    def find(a):
        while parent_uf[a] != a:
            parent_uf[a] = parent_uf[parent_uf[a]]
            a = parent_uf[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent_uf[rb] = ra

    for v in slot_verts[idx]:
        parent_uf[v] = v
    edge_set = set()
    for p in mesh.data.polygons:
        if p.material_index != idx:
            continue
        vs = list(p.vertices)
        for k in range(len(vs)):
            e = (vs[k], vs[(k + 1) % len(vs)])
            edge_set.add((min(e), max(e)))
    for a, b in edge_set:
        union(a, b)
    groups = {}
    for v in slot_verts[idx]:
        groups.setdefault(find(v), []).append(v)
    out = []
    for root, members in groups.items():
        pts = [verts[v] for v in members]
        lo = [min(p[k] for p in pts) for k in range(3)]
        hi = [max(p[k] for p in pts) for k in range(3)]
        cen = Vector((sum(p[k] for p in pts) / len(pts) for k in range(3)))
        radii = sorted((p - cen).length for p in pts)
        out.append({
            "verts": len(members),
            "index_min": min(members),
            "index_max": max(members),
            "bbox_min": [round(x, 4) for x in lo],
            "bbox_max": [round(x, 4) for x in hi],
            "centroid": [round(x, 4) for x in cen],
            "radius_mean": round(sum(radii) / len(radii), 4),
            "radius_max": round(radii[-1], 4),
        })
    out.sort(key=lambda r: -r["verts"])
    return out

for slot in (face_name, eye_name):
    isl = islands(slot)
    report.setdefault("islands", {})[slot] = isl
    print("PROBE_ISLANDS", slot, json.dumps(isl[:6]))

report["uv_faces"] = uv_faces
report["slot_vertex_indices"] = {names[i]: slot_verts[i] for i in range(len(names))}
report["vertex_coords"] = [[round(c.x, 5), round(c.y, 5), round(c.z, 5)] for c in verts]
report["head_weights"] = [round(w, 5) for w in hw]

with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(report, fh)
print("PROBE_OUT", OUT, os.path.getsize(OUT))
print("PROBE_DONE")