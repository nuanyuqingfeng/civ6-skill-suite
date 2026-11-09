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
print("BEFORE_BBOX", [round(min(v.co[i] for v in body.data.vertices), 3) for i in range(3)],
      [round(max(v.co[i] for v in body.data.vertices), 3) for i in range(3)])
print("PARENT", body.parent.name if body.parent else None, "MW", [[round(c, 4) for c in r] for r in body.matrix_world])
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
arm.scale = (SCALE, SCALE, SCALE)
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
print("AFTER_ARM_SCALE_MW", [[round(c, 4) for c in r] for r in body.matrix_world])
body.data.transform(Matrix.Scale(SCALE, 4))
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()
print("FINAL_BBOX", [round(min(v.co[i] for v in body.data.vertices), 3) for i in range(3)],
      [round(max(v.co[i] for v in body.data.vertices), 3) for i in range(3)])
print("OBJECT_SCALE", tuple(arm.scale), "BONE_HEAD", [round(v, 3) for v in arm.data.bones["Bip001Head"].head_local])
