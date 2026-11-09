import importlib.util
import json
import os
import sys

PMX_MODULE = r"E:/SoftWares/blender45/userres/scripts/addons/mmd_tools/core/pmx/__init__.py"

spec = importlib.util.spec_from_file_location("mmd_pmx", PMX_MODULE)
pmx = importlib.util.module_from_spec(spec)
sys.modules["mmd_pmx"] = pmx
spec.loader.exec_module(pmx)

TARGETS = [
    r"G:/Wuwa_3D_Assets/Characters/角色_Jinxi/../../Material/建模文件/今汐1.04_by_鸣潮_fde1189fab0bc6c2fdff468721871df0/鸣潮_今汐1.023请标明辫子软化版本.pmx",
]

FACE_KEYS = ["左目", "右目", "あ", "口", "眉", "舌", "目", "顎", " cheek", "Cheek", "eye", "Eye", "mouth", "Mouth", "jaw", "Jaw", "brow", "Brow", "tongue", "Tongue"]

def is_face_bone(name):
    for k in FACE_KEYS:
        if k in name:
            return True
    return False

def dump(path):
    model = pmx.load(path)
    bones = model.bones
    face_bones = [b.name for b in bones if is_face_bone(b.name)]
    morphs = []
    for m in model.morphs:
        morphs.append({
            "name": m.name,
            "name_e": m.name_e,
            "category": m.category,
            "type": m.type_index(),
            "offsets": len(m.offsets),
        })
    return {
        "path": path,
        "name": model.name,
        "bone_count": len(bones),
        "bone_names": [b.name for b in bones],
        "face_bones": face_bones,
        "face_bone_count": len(face_bones),
        "morph_count": len(morphs),
        "morphs": morphs,
    }

def main():
    out_dir = sys.argv[1]
    result = []
    for p in sys.argv[2:]:
        result.append(dump(p))
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "pmx_forensics.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    for r in result:
        print("PMX", os.path.basename(r["path"]))
        print("  bones", r["bone_count"], "face", r["face_bone_count"], "morphs", r["morph_count"])
    print("PMX_DONE", dst)

main()
