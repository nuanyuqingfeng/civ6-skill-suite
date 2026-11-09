import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_face as rig

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
SCALE = 0.915502
OUT = os.path.join(ROOT, "workspace", "gen", "reports", "r15_parts_geom.json")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = max([o for o in bpy.data.objects if o.type == 'MESH'], key=lambda o: len(o.data.vertices))
arm.scale = (SCALE, SCALE, SCALE)
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
body.data.transform(Matrix.Scale(SCALE, 4))
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()

parts = rig.load_parts()
co = [v.co.copy() for v in body.data.vertices]
names = [m.name for m in body.data.materials]
face_slot = names.index("MI_R2T1JinxiMd10011Face")
face_verts = set()
for p in body.data.polygons:
    if p.material_index == face_slot:
        face_verts.update(p.vertices)

report = {}
for key in ("rimL", "rimR", "upL", "upR", "loL", "loR", "lashL", "lashR", "creaseL", "creaseR", "browL", "browR"):
    idx = parts[key]
    pts = [co[i] for i in idx]
    report[key] = {
        "count": len(idx),
        "in_face": sum(1 for i in idx if i in face_verts),
        "bbox": [[round(min(p[k] for p in pts), 3) for k in range(3)],
                 [round(max(p[k] for p in pts), 3) for k in range(3)]],
    }
print("PARTS", json.dumps(report), flush=True)

# 面材质顶点到眼球中心的距离分布（只看前方 y<-0.8 的部分）
for side, ctr in (("L", Vector(parts["eyeball"]["L"]["center_fit"]) * SCALE),
                  ("R", Vector(parts["eyeball"]["R"]["center_fit"]) * SCALE)):
    bins = {}
    for i in face_verts:
        c = co[i]
        if c.y >= -0.8:
            continue
        d = (c - ctr).length
        if d > 3.0:
            continue
        b = round(math.floor(d * 4.0) / 4.0, 2)
        bins[b] = bins.get(b, 0) + 1
    print("DIST_HIST", side, json.dumps({str(k): bins[k] for k in sorted(bins)}), flush=True)

for side, ctr in (("L", Vector(parts["eyeball"]["L"]["center_fit"]) * SCALE),
                  ("R", Vector(parts["eyeball"]["R"]["center_fit"]) * SCALE)):
    lid = set(parts["up" + side]) | set(parts["lo" + side]) | set(parts["rim" + side]) | set(parts["crease" + side])
    ds = sorted(round((co[i] - ctr).length, 3) for i in lid if i in face_verts)
    print("LIDSET_D", side, len(ds), ds[:5], ds[-5:], flush=True)

print("PARTS_DONE", flush=True)
