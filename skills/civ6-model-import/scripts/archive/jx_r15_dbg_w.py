import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_face as rig

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
SCALE = 0.915502
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
rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)
gname = {g.index: g.name for g in body.vertex_groups}
for vi in (7060, 7075, 5718, 6391, 7061):
    v = body.data.vertices[vi]
    print("DBG", vi, [round(c, 3) for c in v.co],
          {gname[g.group]: round(g.weight, 4) for g in v.groups}, flush=True)
print("DBG_EYE", [round(c, 4) for c in rig._eye_center(parts, "L")],
      [round(c, 4) for c in rig._eye_center(parts, "R")], flush=True)
