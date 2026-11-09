import bpy
from mathutils import Matrix

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
SCALE = 0.915502

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
body = max([o for o in bpy.data.objects if o.type == 'MESH'], key=lambda o: len(o.data.vertices))
print("DIAG_PARENT", body.parent.name if body.parent else "-", body.parent_type)
print("DIAG_MODS", [(m.name, m.type, m.object.name if m.type == 'ARMATURE' else "-") for m in body.modifiers])
print("DIAG_ARM_SCALE", tuple(round(v, 6) for v in arm.scale), "BODY_SCALE", tuple(round(v, 6) for v in body.scale))
print("DIAG_BODY_MW", [round(c, 6) for row in body.matrix_world for c in row])
print("DIAG_PAR_INV", [round(c, 6) for row in body.matrix_parent_inverse for c in row])


def delta(tag):
    co = [v.co.copy() for v in body.data.vertices]
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    worst = max((me.vertices[i].co - co[i]).length for i in range(len(co)))
    print("DIAG_EVAL", tag, "verts", len(me.vertices), "worst", round(worst, 6),
          "world", [round(c, 6) for row in ev.matrix_world for c in row])
    ev.to_mesh_clear()


delta("as_imported")

bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
arm.scale = (SCALE, SCALE, SCALE)
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
body.data.transform(Matrix.Scale(SCALE, 4))
body.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()
print("DIAG_ARM_SCALE2", tuple(round(v, 6) for v in arm.scale), "BODY_MW2", [round(c, 6) for row in body.matrix_world for c in row])
delta("after_scale")
print("DIAG_DONE")
