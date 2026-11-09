import bpy
import os
import math

from mathutils import Matrix, Vector

OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\jinhsi_fbx"
TEX_DIR = os.path.join(OUT_DIR, "weapon_tex")
PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
FBX = r"D:\desktop\Material\建模文件\WeaponJinXIWeapon\JinxiSwordModel.fbx"
ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"
CLIPS = ["Ui_Weapon_Start", "Ui_Weapon_Loop", "Ui_Weapon_End"]
BONE = "WeaponProp01"
MAT = "MI_R2T1JinxiMd10011Weapon"
BLEND_OUT = os.path.join(OUT_DIR, "weapon_rigged.blend")
# 武器 FBX 以米为单位，PSK 骨架以厘米为单位
UNIT_SCALE = 100.0
# 武器局部轴与挂点骨局部轴逐一重合（骨对骨挂接），剑身沿骨 +X
BLADE_AXIS = Vector((1.0, 0.0, 0.0))
RIG_ALIGN = Matrix.Rotation(math.radians(90.0), 4, 'Z')
ANIM_SCALE = 100.0
REF_CLIP = "Ui_Weapon_Loop"
REF_FRAME = 0

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions, bpy.data.materials, bpy.data.images):
    for item in list(block):
        block.remove(item, do_unlink=True)

bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = [o for o in bpy.data.objects if o.type == 'MESH'][0]
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
for clip in CLIPS:
    bpy.ops.uf.import_ueanim(directory=ANIM_DIR, files=[{'name': clip + '.ueanim'}])
if arm.animation_data is None:
    arm.animation_data_create()


def topo():
    order = []
    seen = set()

    def visit(pb):
        if pb.name in seen:
            return
        seen.add(pb.name)
        if pb.parent is not None:
            visit(pb.parent)
        order.append(pb)

    for pb in arm.pose.bones:
        visit(pb)
    return order


ORDER = topo()
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'


def apply_correct_pose():
    pw = {}
    for pb in ORDER:
        local = Matrix.LocRotScale(pb.location * ANIM_SCALE, pb.rotation_quaternion, pb.scale)
        pw[pb.name] = (RIG_ALIGN @ local) if pb.parent is None else (pw[pb.parent.name] @ local)
    for pb in ORDER:
        pb.matrix = pw[pb.name]
        bpy.context.view_layer.update()


arm.animation_data.action = bpy.data.actions[REF_CLIP]
bpy.context.scene.frame_set(REF_FRAME)
bpy.context.view_layer.update()
apply_correct_pose()

f0 = arm.pose.bones["Bip001LFinger0"].matrix.translation.copy()
f01 = arm.pose.bones["Bip001LFinger01"].matrix.translation.copy()
f4 = arm.pose.bones["Bip001LFinger4"].matrix.translation.copy()
fingers = (f01 - f0).normalized()
across = (f4 - f0).normalized()
palm_n = fingers.cross(across).normalized()
pm = arm.pose.bones[BONE].matrix
pnb = (pm.to_3x3().inverted() @ palm_n)
pnb.normalize()
a = BLADE_AXIS.normalized()
S = Matrix.Identity(4)
print("PALM_WORLD", "fingers", [round(c, 4) for c in fingers],
      "across", [round(c, 4) for c in across], "normal", [round(c, 4) for c in palm_n])
print("PALM_IN_BONE", [round(c, 4) for c in pnb])
print("ATTACH_MATRIX", [[round(S[r][c], 6) for c in range(3)] for r in range(3)])
print("BLADE_DEG_TO_PALM_NORMAL", round(math.degrees(a.angle(pnb)), 2),
      "TO_ACROSS", round(math.degrees(a.angle(across)), 2))

bpy.ops.import_scene.fbx(filepath=FBX)
weapon = [o for o in bpy.data.objects if o.type == 'MESH' and o is not body][0]
warm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o is not arm][0]
print("WEAPON_SRC", weapon.name, len(weapon.data.vertices), "verts",
      len(weapon.data.polygons), "polys", "src_armature", warm.name,
      "parent", weapon.parent.name if weapon.parent else "-")
weapon.parent = None
weapon.matrix_world = Matrix.Identity(4)
weapon.matrix_parent_inverse = Matrix.Identity(4)
for m in list(weapon.modifiers):
    weapon.modifiers.remove(m)
bpy.ops.object.select_all(action='DESELECT')
warm.select_set(True)
bpy.context.view_layer.objects.active = warm
bpy.ops.object.delete(use_global=False)

bone = arm.data.bones[BONE]
B = bone.matrix_local.copy()
M = B @ S @ Matrix.Scale(UNIT_SCALE, 4)
weapon.data.transform(M)
weapon.data.update()
lo = [min(v.co[i] for v in weapon.data.vertices) for i in range(3)]
hi = [max(v.co[i] for v in weapon.data.vertices) for i in range(3)]
print("WEAPON_RIG_BOX", [round(c, 3) for c in lo], [round(c, 3) for c in hi])
print("WEAPON_RIG_SPAN", [round(hi[i] - lo[i], 3) for i in range(3)])
print("BONE_REST", BONE, "parent", bone.parent.name,
      "head", [round(c, 3) for c in bone.head_local],
      "blade_dir_world_rest", [round(c, 4) for c in (B.to_3x3() @ a)])

weapon.vertex_groups.clear()
vg = weapon.vertex_groups.new(name=BONE)
vg.add([v.index for v in weapon.data.vertices], 1.0, 'REPLACE')
weapon.name = "JinhsiWeapon"
weapon.data.name = "JinhsiWeapon"
weapon.parent = arm
weapon.matrix_parent_inverse = arm.matrix_world.inverted()
mod = weapon.modifiers.new(name="Armature", type='ARMATURE')
mod.object = arm
print("BIND", [(g.name, len(weapon.data.vertices)) for g in weapon.vertex_groups],
      [(m.type, m.object.name) for m in weapon.modifiers])

for uv_name in [u.name for u in weapon.data.uv_layers][1:]:
    weapon.data.uv_layers.remove(weapon.data.uv_layers[uv_name])
weapon.data.uv_layers[0].active_render = True
print("UV_AFTER", [u.name for u in weapon.data.uv_layers])

mat = bpy.data.materials.new(MAT)
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
bsdf = nodes["Principled BSDF"]
img_base = nodes.new("ShaderNodeTexImage")
img_base.name = "BaseColor"
img_base.image = bpy.data.images.load(os.path.join(TEX_DIR, MAT + "_BaseColor.dds"))
img_base.image.colorspace_settings.name = "sRGB"
img_nrm = nodes.new("ShaderNodeTexImage")
img_nrm.name = "Normal"
img_nrm.image = bpy.data.images.load(os.path.join(TEX_DIR, MAT + "_Normal.dds"))
img_nrm.image.colorspace_settings.name = "Non-Color"
nmap = nodes.new("ShaderNodeNormalMap")
links.new(img_base.outputs["Color"], bsdf.inputs["Base Color"])
links.new(img_nrm.outputs["Color"], nmap.inputs["Color"])
links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
weapon.data.materials.clear()
weapon.data.materials.append(mat)
print("MATERIAL", [m.name for m in weapon.data.materials],
      [(i.name, i.image.name) for i in nodes if i.type == 'TEX_IMAGE'])

for act in bpy.data.actions:
    act.use_fake_user = True
arm.animation_data.action = bpy.data.actions[REF_CLIP]
arm.data.pose_position = 'POSE'
bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = 80
bpy.context.scene.frame_set(REF_FRAME)
bpy.context.view_layer.update()
print("SCENE_OBJECTS", [(o.name, o.type) for o in bpy.data.objects])
print("MESH_TOTAL", len(weapon.data.vertices), len(weapon.data.polygons))
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
print("BLEND_SAVED", BLEND_OUT, os.path.getsize(BLEND_OUT))
print("BUILD_WEAPON_DONE")
