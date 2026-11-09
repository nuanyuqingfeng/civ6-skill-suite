import bpy
import math

from mathutils import Vector, Matrix

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"
CLIPS = ["Ui_Weapon_Start", "Ui_Weapon_Loop", "Ui_Weapon_End"]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
for clip in CLIPS:
    bpy.ops.uf.import_ueanim(directory=ANIM_DIR, files=[{'name': clip + '.ueanim'}])

for bn in ("Bip001LHand", "WeaponProp01"):
    b = arm.data.bones[bn]
    m = b.matrix_local
    print("REST", bn, "parent", b.parent.name if b.parent else "-",
          "head", [round(c, 4) for c in b.head_local],
          "X", [round(c, 4) for c in (m.to_3x3() @ Vector((1, 0, 0)))],
          "Y", [round(c, 4) for c in (m.to_3x3() @ Vector((0, 1, 0)))],
          "Z", [round(c, 4) for c in (m.to_3x3() @ Vector((0, 0, 1)))])
rel = arm.data.bones["Bip001LHand"].matrix_local.inverted() @ arm.data.bones["WeaponProp01"].matrix_local
print("REL_WP01_IN_LHAND translation", [round(c, 4) for c in rel.translation])
for i, nm in enumerate(("X", "Y", "Z")):
    print("REL_WP01_AXIS", nm, [round(rel[i][k], 4) for k in range(3)])
handY = Vector((0, 1, 0))
for nm, v in (("X", Vector((1, 0, 0))), ("-X", Vector((-1, 0, 0))), ("Y", Vector((0, 1, 0))),
              ("-Y", Vector((0, -1, 0))), ("Z", Vector((0, 0, 1))), ("-Z", Vector((0, 0, -1)))):
    ang = math.degrees(v.angle(handY))
    print("ANGLE_PROP_TO_HANDY", nm, round(ang, 2))

print("CLIP_RANGES", [(c, tuple(round(x) for x in bpy.data.actions[c].frame_range)) for c in CLIPS])
print("GEO_PROBE_DONE")
