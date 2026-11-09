import bpy

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk")
body = max([o for o in bpy.data.objects if o.type == 'MESH'], key=lambda o: len(o.data.vertices))
kb = body.data.shape_keys.key_blocks
print("DBG_KEYS", [k.name for k in kb])
print("DBG_VALS", [round(k.value, 3) for k in kb])
for i, k in enumerate(kb):
    print("DBG_KEY", i, k.name, len(k.data), [round(v, 4) for v in k.data[6264].co])
print("DBG_BASECO", [round(v, 4) for v in body.data.vertices[6264].co])
