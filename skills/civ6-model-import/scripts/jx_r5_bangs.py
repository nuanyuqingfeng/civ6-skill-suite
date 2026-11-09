import os

BANGS_SLOT = "MI_R2T1JinxiMd10011Bangs"
HAIR_SLOT = "MI_R2T1JinxiMd10011Hair"
FACE_SLOT = "MI_R2T1JinxiMd10011Face"
EYE_SLOT = "MI_R2T1JinxiMd10011Eye"
# 位移量＝（上睑缘最高点减刘海最低点再加余量）× 该比例，单位厘米
LID_CLEARANCE = 0.25
LIFT_RATIO = 0.5
REPORT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\reports\bangs_lift.tsv"


def slot_vertices(mesh):
    names = [m.name for m in mesh.data.materials]
    sets = {n: set() for n in names}
    for p in mesh.data.polygons:
        for vi in p.vertices:
            sets[names[p.material_index]].add(vi)
    return names, sets


def lift_bangs(mesh):
    """刘海的 967 个顶点整体沿世界 +Z 平移，其余材质顶点保持原坐标。"""
    names, sets = slot_vertices(mesh)
    bangs = sorted(sets[BANGS_SLOT])
    moved = set(bangs)
    others = [v for v in range(len(mesh.data.vertices)) if v not in moved]
    shared = moved & set().union(*[sets[n] for n in names if n != BANGS_SLOT])
    assert not shared, shared
    before = [v.co.copy() for v in mesh.data.vertices]
    lid_zmax = max(before[v].z for v in sets[EYE_SLOT])
    z_min_before = min(before[v].z for v in bangs)
    z_max_before = max(before[v].z for v in bangs)
    overlap = lid_zmax - z_min_before
    lift = (overlap + LID_CLEARANCE) * LIFT_RATIO
    assert lift > 0.0, (overlap, lift)
    for v in bangs:
        mesh.data.vertices[v].co.z += lift
    mesh.data.update()
    other_delta = max((mesh.data.vertices[v].co - before[v]).length for v in others)
    hair_delta = max((mesh.data.vertices[v].co - before[v]).length for v in sets[HAIR_SLOT])
    face_delta = max((mesh.data.vertices[v].co - before[v]).length for v in sets[FACE_SLOT])
    z_min_after = min(mesh.data.vertices[v].co.z for v in bangs)
    z_max_after = max(mesh.data.vertices[v].co.z for v in bangs)
    print("BANGS_LIFT slot=%s z_min_before=%.4f lid_zmax=%.4f overlap=%.4f clearance=%.2f ratio=%.2f lift=%.4f z_min_after=%.4f"
          % (BANGS_SLOT, z_min_before, lid_zmax, overlap, LID_CLEARANCE, LIFT_RATIO, lift, z_min_after))
    print("BANGS_LIFT_Z before=[%.4f, %.4f] after=[%.4f, %.4f] moved_verts=%d shared_verts=%d"
          % (z_min_before, z_max_before, z_min_after, z_max_after, len(bangs), len(shared)))
    print("BANGS_LIFT_ZERO other_max_delta=%.9f hair_max_delta=%.9f face_max_delta=%.9f"
          % (other_delta, hair_delta, face_delta))
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    rows = [
        ("bangs_z_min_before", "%.6f" % z_min_before),
        ("bangs_z_max_before", "%.6f" % z_max_before),
        ("lid_zmax", "%.6f" % lid_zmax),
        ("overlap", "%.6f" % overlap),
        ("lift", "%.6f" % lift),
        ("bangs_z_min_after", "%.6f" % z_min_after),
        ("bangs_z_max_after", "%.6f" % z_max_after),
        ("moved_verts", str(len(bangs))),
        ("shared_verts", str(len(shared))),
        ("other_max_delta", "%.9f" % other_delta),
        ("hair_max_delta", "%.9f" % hair_delta),
        ("face_max_delta", "%.9f" % face_delta),
    ]
    with open(REPORT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("item\tvalue\n")
        for key, val in rows:
            fh.write(key + "\t" + val + "\n")
    print("BANGS_LIFT_REPORT", REPORT)
    return lift
