import bpy, json, os, re, sys

REPORT = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/pbr_face_forensics_data.json"

CASES = [
    ("pmx_104", r"D:/desktop/Material/建模文件/今汐1.04_by_鸣潮_fde1189fab0bc6c2fdff468721871df0/鸣潮_今汐1.023请标明辫子软化版本.pmx"),
    ("pmx_q", r"D:/desktop/Material/建模文件/今汐Q/今汐Q.pmx"),
    ("pmx_lemon", r"D:/desktop/Material/建模文件/今汐_by_给你柠檬椰果养乐多你会跟我玩吗_99b19bd24ac0b745e36aea1bef83c46b/今汐.pmx"),
]

FACE_PAT = re.compile(r"(左目|右目|目|瞳|口|眉|舌|顎|あ|い|う|え|お|頬|涙|照れ|まばたき|笑|怒|困|星|ハイライト|歯|唇|顔|鼻)")

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def do_case(tag, path):
    reset()
    bpy.ops.preferences.addon_enable(module="mmd_tools")
    bpy.ops.mmd_tools.import_model(filepath=path, scale=0.08,
        types={'MESH','ARMATURE','MORPHS'},
        clean_model=True, remove_doubles=False, fix_IK_links=False,
        apply_bone_fixed_axis=False, rename_bones=False, use_underscore=False,
        dictionary='DISABLED', use_mipmap=False, sph_blend_factor=1.0,
        spa_blend_factor=1.0, log_level='WARNING', save_log=False)
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    assert len(arms) >= 1, "no armature for " + tag
    arm = arms[0]
    bones = [b.name for b in arm.data.bones]
    face_bones = [b for b in bones if FACE_PAT.search(b)]
    roots = [o for o in bpy.data.objects if getattr(o, "mmd_type", "") == "ROOT"]
    morphs = {}
    if roots:
        r = roots[0].mmd_root
        for kind in ("vertex_morphs", "bone_morphs", "material_morphs", "uv_morphs", "group_morphs"):
            coll = getattr(r, kind)
            morphs[kind] = [m.name for m in coll]
    else:
        morphs = {"vertex_morphs": [], "bone_morphs": [], "material_morphs": [], "uv_morphs": [], "group_morphs": []}
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    verts = sum(len(m.data.vertices) for m in meshes)
    shape_keys = {}
    for m in meshes:
        if m.data.shape_keys:
            for kb in m.data.shape_keys.key_blocks:
                shape_keys[kb.name] = shape_keys.get(kb.name, 0) + 1
    return {
        "tag": tag, "path": path,
        "bone_count": len(bones),
        "bones": bones,
        "face_bones": face_bones,
        "face_bone_count": len(face_bones),
        "morph_counts": {k: len(v) for k, v in morphs.items()},
        "morphs": morphs,
        "mesh_count": len(meshes),
        "vertex_count": verts,
        "shape_keys": shape_keys,
    }

out = []
for tag, path in CASES:
    out.append(do_case(tag, path))

os.makedirs(os.path.dirname(REPORT), exist_ok=True)
with open(REPORT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("PMX_PROBE_DONE", REPORT)
