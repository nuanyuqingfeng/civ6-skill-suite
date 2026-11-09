import bpy
import os
import sys
import json
import math

from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "both"
ADDON_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\_tools\blender_addons"
if ADDON_DIR not in sys.path:
    sys.path.insert(0, ADDON_DIR)
if "psk_psa" not in sys.modules:
    import psk_psa
    psk_psa.register()
print("PSK_PSA_MODULE", "psk_psa" in sys.modules)
OUT_DIR = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\tmp"
FBX = r"D:\desktop\Material\建模文件\WeaponJinXIWeapon\JinxiSwordModel.fbx"
PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"

os.makedirs(OUT_DIR, exist_ok=True)


def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions, bpy.data.materials, bpy.data.images):
        for item in list(block):
            block.remove(item, do_unlink=True)


def vec(v):
    return [round(float(c), 6) for c in v]


def mat(m):
    return [round(float(c), 6) for row in m for c in row]


def bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = [round(min(p[i] for p in pts), 4) for i in range(3)]
    hi = [round(max(p[i] for p in pts), 4) for i in range(3)]
    return lo, hi


def dump_mesh(obj, tag):
    me = obj.data
    info = {
        "name": obj.name,
        "tag": tag,
        "verts": len(me.vertices),
        "polys": len(me.polygons),
        "loops": len(me.loops),
        "tris_est": sum(len(p.vertices) - 2 for p in me.polygons),
        "uv_layers": [u.name for u in me.uv_layers],
        "color_attrs": [c.name for c in me.color_attributes],
        "materials": [],
        "modifiers": [(m.name, m.type) for m in obj.modifiers],
        "vertex_groups": [g.name for g in obj.vertex_groups],
        "shape_keys": [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else [],
        "animation": obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None,
        "parent": obj.parent.name if obj.parent else None,
        "matrix_world": mat(obj.matrix_world),
        "scale": vec(obj.scale),
        "rotation_euler_deg": [round(float(math.degrees(a)), 4) for a in obj.rotation_euler],
        "bbox_world": bbox(obj),
        "dimensions": vec(obj.dimensions),
    }
    for slot_i, ms in enumerate(obj.material_slots):
        entry = {"slot": slot_i, "material": ms.material.name if ms.material else None, "images": [],
                 "nodes": []}
        if ms.material and ms.material.use_nodes:
            for n in ms.material.node_tree.nodes:
                entry["nodes"].append((n.name, n.type))
                if n.type == 'TEX_IMAGE' and n.image:
                    entry["images"].append({"node": n.name, "image": n.image.name,
                                            "filepath": bpy.path.abspath(n.image.filepath),
                                            "size": list(n.image.size),
                                            "colorspace": n.image.colorspace_settings.name})
        info["materials"].append(entry)
    per_slot = {}
    for p in me.polygons:
        per_slot[p.material_index] = per_slot.get(p.material_index, 0) + 1
    info["polys_per_slot"] = {str(k): v for k, v in sorted(per_slot.items())}
    return info


result = {"blender": bpy.app.version_string, "arg": ARG,
          "unit_system": bpy.context.scene.unit_settings.system,
          "scale_length": bpy.context.scene.unit_settings.scale_length,
          "length_unit": bpy.context.scene.unit_settings.length_unit}

if ARG in ("fbx", "both"):
    clear()
    bpy.ops.import_scene.fbx(filepath=FBX)
    objs = list(bpy.context.scene.objects)
    result["fbx"] = {
        "path": FBX,
        "object_count": len(objs),
        "objects": [(o.name, o.type) for o in objs],
        "armatures": [(o.name, len(o.data.bones)) for o in objs if o.type == 'ARMATURE'],
        "actions": [a.name for a in bpy.data.actions],
        "meshes": [dump_mesh(o, "fbx") for o in objs if o.type == 'MESH'],
        "empties": [{"name": o.name, "matrix_world": mat(o.matrix_world),
                     "parent": o.parent.name if o.parent else None} for o in objs if o.type == 'EMPTY'],
    }

if ARG in ("psk", "both"):
    clear()
    bpy.ops.import_scene.psk(filepath=PSK)
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    bones = {}
    for b in arm.data.bones:
        mw = arm.matrix_world @ b.matrix_local
        bones[b.name] = {
            "parent": b.parent.name if b.parent else None,
            "head_local": vec(b.head_local),
            "tail_local": vec(b.tail_local),
            "head_world": vec(mw.translation),
            "x_axis_world": vec(mw.to_3x3() @ Vector((1, 0, 0))),
            "y_axis_world": vec(mw.to_3x3() @ Vector((0, 1, 0))),
            "z_axis_world": vec(mw.to_3x3() @ Vector((0, 0, 1))),
            "matrix_local": mat(b.matrix_local),
            "length": round(float(b.length), 6),
        }
    props = {k: v for k, v in bones.items() if k.startswith("WeaponProp")}
    hands = {k: v for k, v in bones.items() if k in ("Bip001LHand", "Bip001RHand", "Bip001LForearm", "Bip001RForearm")}
    result["psk"] = {
        "path": PSK,
        "armature": arm.name,
        "bone_count": len(arm.data.bones),
        "matrix_world": mat(arm.matrix_world),
        "objects": [(o.name, o.type) for o in bpy.data.objects],
        "weapon_bones": props,
        "hand_bones": hands,
        "all_bone_names": [b.name for b in arm.data.bones],
        "root_bones": [(b.name, mat(b.matrix_local)) for b in arm.data.bones if b.parent is None],
    }

path = os.path.join(OUT_DIR, "wpn_probe_%s.json" % ARG)
with open(path, "w", encoding="utf-8") as fh:
    json.dump(result, fh, ensure_ascii=False, indent=1)
print("PROBE_JSON", path)
print("BLENDER", bpy.app.version_string)
if "fbx" in result:
    print("FBX_OBJECTS", result["fbx"]["object_count"], result["fbx"]["objects"])
    for m in result["fbx"]["meshes"]:
        print("FBX_MESH", m["name"], "verts", m["verts"], "polys", m["polys"], "tris", m["tris_est"],
              "uv", m["uv_layers"], "bbox", m["bbox_world"], "dims", m["dimensions"],
              "scale", m["scale"], "rot", m["rotation_euler_deg"], "groups", m["vertex_groups"],
              "shapes", m["shape_keys"], "anim", m["animation"])
        for mm in m["materials"]:
            print("FBX_MAT", mm["slot"], mm["material"], "images", mm["images"])
        print("FBX_SLOTPOLY", m["polys_per_slot"])
    print("FBX_ARMATURES", result["fbx"]["armatures"], "ACTIONS", result["fbx"]["actions"])
if "psk" in result:
    print("PSK_BONES", result["psk"]["bone_count"], "armature", result["psk"]["armature"])
    for n, b in result["psk"]["weapon_bones"].items():
        print("WEAPON_BONE", n, "parent", b["parent"], "head_world", b["head_world"],
              "y_axis", b["y_axis_world"], "z_axis", b["z_axis_world"], "len", b["length"])
    for n, b in result["psk"]["hand_bones"].items():
        print("HAND_BONE", n, "parent", b["parent"], "head_world", b["head_world"],
              "y_axis", b["y_axis_world"], "z_axis", b["z_axis_world"], "len", b["length"])
print("PROBE_DONE")
