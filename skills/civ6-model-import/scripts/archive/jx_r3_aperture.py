import os
import sys

import bpy
from mathutils import Matrix

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
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
arm.scale = (SCALE, SCALE, SCALE)
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()
parts = rig.load_parts()
rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)

for name in ("JX_Eye_L", "JX_LidUp_L"):
    idx = body.vertex_groups[name].index
    zs = []
    for v in body.data.vertices:
        for g in v.groups:
            if g.group == idx and g.weight > 0.5:
                zs.append((body.matrix_world @ v.co).z)
                break
    print("APERTURE %s verts=%d z %.2f..%.2f span=%.2f" % (name, len(zs), min(zs), max(zs), max(zs) - min(zs)))
print("APERTURE_DONE")
