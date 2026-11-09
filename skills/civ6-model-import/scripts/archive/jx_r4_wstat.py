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

for bone in ("JX_LidUp_L", "JX_LidUp_R", "JX_LipUp", "JX_LidLo_L", "JX_LidLo_R"):
    if bone not in body.vertex_groups:
        print("WSTAT %s missing" % bone)
        continue
    idx = body.vertex_groups[bone].index
    total = 0
    span = 0.0
    for v in body.data.vertices:
        for g in v.groups:
            if g.group == idx and g.weight > 0.0:
                total += 1
                if bone.startswith("JX_Lid"):
                    span = max(span, abs(v.co.x))
                break
    print("WSTAT %-12s verts=%4d max_abs_x=%.2f" % (bone, total, span))
print("WSTAT_DONE")
