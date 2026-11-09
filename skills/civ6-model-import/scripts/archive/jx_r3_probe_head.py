import json

import bpy
from mathutils import Matrix, Vector

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
PARTS = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\tmp\jx14_parts.json"
SCALE = 0.915502

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = max([o for o in bpy.data.objects if o.type == 'MESH'], key=lambda o: len(o.data.vertices))
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
arm.scale = (SCALE, SCALE, SCALE)
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
body.data.transform(Matrix.Scale(SCALE, 4))
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()
parts = json.load(open(PARTS, encoding="utf-8"))
co = [v.co.copy() for v in body.data.vertices]


def stats(name, idxs):
    pts = [co[i] for i in idxs]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = sum(pts, Vector()) / len(pts)
    print("PART", name, len(idxs), "c", [round(v, 4) for v in c], "lo", [round(v, 4) for v in lo], "hi", [round(v, 4) for v in hi])


for key in ("mouth_ap", "lip", "upL", "upR", "loL", "loR", "lashL", "lashR", "creaseL", "creaseR", "browL", "browR"):
    stats(key, parts[key])
for side in ("L", "R"):
    e = parts["eyeball"][side]
    stats("eyeball_" + side, e["verts"])
    print("EYE", side, "center_dome", [round(v * SCALE, 4) for v in e["center_dome"]], "r", round(e["radius_fit"] * SCALE, 4),
          "center_fit", [round(v * SCALE, 4) for v in e["center_fit"]])
head = arm.data.bones["Bip001Head"]
print("HEAD head", [round(v, 4) for v in head.head_local], "tail", [round(v, 4) for v in head.tail_local])
print("HEAD matrix", [[round(c, 5) for c in row] for row in head.matrix_local])
neck = arm.data.bones["Bip001Neck"]
print("NECK head", [round(v, 4) for v in neck.head_local], "tail", [round(v, 4) for v in neck.tail_local])
face_idx = [i for p in body.data.polygons if body.data.materials[p.material_index].name == "MI_R2T1JinxiMd10011Face" for i in p.vertices]
stats("face_slot", sorted(set(face_idx)))
eye_idx = [i for p in body.data.polygons if body.data.materials[p.material_index].name == "MI_R2T1JinxiMd10011Eye" for i in p.vertices]
stats("eye_slot", sorted(set(eye_idx)))
print("REST_ARM", arm.name, "bones", len(arm.data.bones))
