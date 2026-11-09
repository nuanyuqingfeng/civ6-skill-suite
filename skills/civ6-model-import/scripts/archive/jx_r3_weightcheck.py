import os
import sys

import bpy
from mathutils import Matrix

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
sys.path.insert(0, os.path.join(ROOT, "workspace", "_tools"))
import jx_r3_face as rig

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
SCALE = 0.915502
WEAPON = os.path.join(ROOT, "workspace", "gen", "jinhsi_fbx", "weapon_rigged.blend")

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

rig.join_weapon(body, WEAPON)
parts = rig.load_parts()
rig.build_face_rig(arm, body)
rig.apply_weights(body, parts)

for name in ("JX_LidUp_L", "JX_LidUp_R", "JX_Jaw", "JX_Eye_L", "JX_Weapon"):
    vg = body.vertex_groups.get(name)
    if vg is None:
        print("GROUP_MISSING", name)
        continue
    total = 0
    count = 0
    for v in body.data.vertices:
        for g in v.groups:
            if g.group == vg.index:
                total += 1
                count += g.weight
    print("GROUP %s verts=%d weight_sum=%.2f" % (name, total, count))
print("WEIGHTCHECK_DONE")
