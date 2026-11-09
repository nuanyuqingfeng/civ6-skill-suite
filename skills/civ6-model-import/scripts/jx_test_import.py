import bpy
import os

MODEL_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
PSK = os.path.join(MODEL_DIR, "R2T1JinxiMd10011.psk")

bpy.ops.import_scene.psk(filepath=PSK)
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
print("ARMATURES:", [(a.name, len(a.data.bones)) for a in arms])
print("MESHES:", len(meshes))
verts = sum(len(m.data.vertices) for m in meshes)
print("TOTAL_VERTS:", verts)
for m in meshes:
    print("MESH:", m.name, "verts=", len(m.data.vertices), "slots=", [s.name for s in m.material_slots])

if arms:
    arm = arms[0]
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm

ANIM_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim\UiAnim"
bpy.ops.uf.import_ueanim(directory=ANIM_DIR, files=[{'name': 'Ui_Nature_Loop.ueanim'}])

for a in bpy.data.actions:
    print("ACTION:", a.name, "frames=", a.frame_range)
