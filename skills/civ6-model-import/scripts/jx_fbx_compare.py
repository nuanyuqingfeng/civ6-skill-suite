import bpy

MODEL_FBX = r"E:\SoftWares\civ6_nexus_work\jinhsi_fbx\LEAD_Jinhsi_QYQXP_Model.fbx"
ANIM_FBX = r"E:\SoftWares\civ6_nexus_work\jinhsi_fbx\JX_IDLE.fbx"


def load_rest(path, tag):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    data = {}
    for b in arm.data.bones:
        data[b.name] = (tuple(round(c, 4) for c in b.head_local), round(b.length, 4),
                        tuple(round(c, 4) for c in (b.tail_local - b.head_local)))
    print(tag, "bones=", len(data), "arm_obj_scale=", [round(c, 4) for c in arm.scale])
    return data


m = load_rest(MODEL_FBX, "MODEL")
a = load_rest(ANIM_FBX, "ANIM")

only_m = set(m) - set(a)
only_a = set(a) - set(m)
print("CMP only_model=", sorted(only_m)[:6], "only_anim=", sorted(only_a)[:6])
diff = []
for name in set(m) & set(a):
    if m[name] != a[name]:
        diff.append((name, m[name], a[name]))
print("CMP diff_count=", len(diff))
for name, mv, av in diff[:8]:
    print("CMP", name, "model=", mv, "anim=", av)
print("CMP_DONE")
