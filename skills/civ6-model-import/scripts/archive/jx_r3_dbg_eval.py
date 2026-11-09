import json
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
SCALE = 0.915502
parts = json.load(open(os.path.join(ROOT, "workspace", "tmp", "jx14_parts.json"), encoding="utf-8"))
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
bpy.context.view_layer.update()
print("OBJ_MATRIX", [[round(c, 4) for c in row] for row in body.matrix_world])
for i in (parts["upL"][0], parts["loL"][0], parts["mouth_ap"][0], parts["eyeball"]["L"]["verts"][0]):
    print("ORIG", i, [round(v, 3) for v in body.data.vertices[i].co],
          "GROUPS", [(body.vertex_groups[g.group].name, round(g.weight, 3)) for g in body.data.vertices[i].groups])
deps = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(deps)
me = ev.to_mesh()
same = sum(1 for i in range(len(me.vertices)) if (me.vertices[i].co - body.data.vertices[i].co).length < 1e-4)
print("EVAL_SAME", same, len(me.vertices))
print("EVAL", [round(v, 3) for v in me.vertices[parts["upL"][0]].co])
ev.to_mesh_clear()
