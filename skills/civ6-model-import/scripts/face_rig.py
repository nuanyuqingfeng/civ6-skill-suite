import math

import bpy
from mathutils import Matrix, Vector

# 面骨前缀：调用方按角色代号调 set_prefix(code)，骨名即 <code>_<后缀>。
# 19 根骨的后缀与角色无关；一切尺寸来自 configure() 传入的 parts 测量结果与整体缩放。
PREFIX = "SK"

_SUFFIXES = ("Jaw", "LipUp", "LipLo", "MouthCorner_L", "MouthCorner_R",
             "LidUp_L", "LidUp_R", "LidLo_L", "LidLo_R",
             "Eye_L", "Eye_R", "Brow_L", "Brow_R",
             "BrowIn_L", "BrowIn_R", "Cheek_L", "Cheek_R", "Nose")


def bone(suffix):
    return PREFIX + "_" + suffix


def set_prefix(code):
    global PREFIX, FACE_BONES
    PREFIX = code
    FACE_BONES = tuple(bone(s) for s in _SUFFIXES)


FACE_BONES = tuple(bone(s) for s in _SUFFIXES)

JAW_MAX_DEG = 9.16
GAZE_MAX_DEG = 0.0
BROW_UP_CM = 0.10
CORNER_OUT_CM = 0.20
LOWER_LID_RATIO = 0.40
BLINK_FORWARD_CM = 0.10
LIP_FALL_POW = 1.5
BROW_INNER_SHARE = 0.45

PARTS = None
SCALE = 1.0
K = 1.0
FACE_SLOT = ""
EYE_SLOT = ""
EYE_L = Vector((0.0, 0.0, 0.0))
EYE_R = Vector((0.0, 0.0, 0.0))
MOUTH_Z = 0.0
MOUTH_Y = 0.0
BLINK_DOWN_CM = 1.55
REST_LID_DOWN_CM = 0.033
REST_LID_UP_CM = 0.015
AXES = {}
DIRS = {}
EYE_PIVOT_LOCAL = {}
BROW_INNER_PIVOT = {}
BROW_INNER_ARM = {}
BROW_GRAD = {}
BROW_INNER_SET = {}
JAW_PIVOT = None


def _ramp(x, lo, hi):
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def _lid_taper(dx, ctr_x):
    inner = 1.0 if ctr_x < 0.0 else -1.0
    u_in = min(1.0, max(0.0, dx * inner) / (1.45 * K))
    u_out = min(1.0, max(0.0, -dx * inner) / (1.45 * K))
    return (1.0 - 0.34 * u_in * u_in) * (1.0 - 0.06 * u_out * u_out)


def _eye_pivot(side):
    return Vector(PARTS["eyeball"][side]["center_fit"]) * SCALE


def configure(parts, scale):
    """按人配置：parts 为测量结果，scale 为整体缩放，K 为面部长度的相对系数。"""
    global PARTS, SCALE, K, FACE_SLOT, EYE_SLOT, EYE_L, EYE_R, MOUTH_Z, MOUTH_Y, BLINK_DOWN_CM
    PARTS = parts
    SCALE = scale
    EYE_L = Vector(parts["eyeball"]["L"]["center_dome"]) * SCALE
    EYE_R = Vector(parts["eyeball"]["R"]["center_dome"]) * SCALE
    MOUTH_Z = float(parts["mouth_z"]) * SCALE
    MOUTH_Y = float(parts["mouth_y"]) * SCALE
    FACE_SLOT = parts["face_slot"]
    EYE_SLOT = parts["eye_slot"]
    eye_sep = abs(EYE_R.x - EYE_L.x)
    K = eye_sep / 6.16
    spans = [v["z_range"][1] - v["z_range"][0] for v in parts["eyeball"].values()]
    eye_v = sum(spans) / len(spans)
    BLINK_DOWN_CM = 0.75 * eye_v
    print("FACE_CONFIGURE", parts["char"], "scale", round(SCALE, 6), "K", round(K, 4),
          "eye_sep", round(eye_sep, 3), "eye_v", round(eye_v, 3), "blink", round(BLINK_DOWN_CM, 3),
          "mouth", [round(MOUTH_Y, 3), round(MOUTH_Z, 3)])


def _face_vert_indices(mesh):
    names = [m.name for m in mesh.data.materials]
    slot = names.index(FACE_SLOT)
    out = set()
    for p in mesh.data.polygons:
        if p.material_index == slot:
            out.update(p.vertices)
    return sorted(out)


def build_face_rig(arm, mesh):
    co = [v.co.copy() for v in mesh.data.vertices]
    mouth = Vector((0.0, MOUTH_Y, MOUTH_Z))
    jaw_pivot = Vector((0.0, 1.6 * K, MOUTH_Z + 2.45 * K))
    lip_pivot = Vector((0.0, -2.2 * K, MOUTH_Z + 2.6 * K))
    global JAW_PIVOT
    JAW_PIVOT = jaw_pivot.copy()
    print("FACE_PIVOT jaw", [round(v, 3) for v in jaw_pivot], "lip", [round(v, 3) for v in lip_pivot])
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    eb.new(bone("Jaw")).head = jaw_pivot
    eb[bone("Jaw")].tail = jaw_pivot + Vector((0.0, -3.6 * K, -4.0 * K))
    eb[bone("Jaw")].parent = eb["Bip001Head"]
    eb.new(bone("LipUp")).head = lip_pivot
    eb[bone("LipUp")].tail = lip_pivot + Vector((0.0, -1.0 * K, -2.0 * K))
    eb[bone("LipUp")].parent = eb["Bip001Head"]
    eb.new(bone("LipLo")).head = mouth
    eb[bone("LipLo")].tail = mouth + Vector((0.0, -1.0 * K, -2.0 * K))
    eb[bone("LipLo")].parent = eb["Bip001Head"]
    for side, sx in (("L", -1.0), ("R", 1.0)):
        head = Vector((sx * 2.4 * K, MOUTH_Y, MOUTH_Z))
        eb.new(bone("MouthCorner_" + side)).head = head
        eb[bone("MouthCorner_" + side)].tail = head + Vector((sx * 0.8, 0.0, 0.0))
        eb[bone("MouthCorner_" + side)].parent = eb["Bip001Head"]
    for side, c in (("L", EYE_L), ("R", EYE_R)):
        eb.new(bone("LidUp_" + side)).head = c + Vector((0.0, 0.2 * K, 0.0))
        eb[bone("LidUp_" + side)].tail = c + Vector((0.0, 0.2 * K, 1.4 * K))
        eb[bone("LidUp_" + side)].parent = eb["Bip001Head"]
        eb.new(bone("LidLo_" + side)).head = c + Vector((0.0, 0.2 * K, 0.0))
        eb[bone("LidLo_" + side)].tail = c + Vector((0.0, 0.2 * K, -1.2 * K))
        eb[bone("LidLo_" + side)].parent = eb["Bip001Head"]
        eb.new(bone("Eye_" + side)).head = c
        eb[bone("Eye_" + side)].tail = c + Vector((0.0, -1.4 * K, 0.0))
        eb[bone("Eye_" + side)].parent = eb["Bip001Head"]
    for side in ("L", "R"):
        idx = PARTS["brow" + side]
        b = sum((co[i] for i in idx), Vector()) / len(idx)
        eb.new(bone("Brow_" + side)).head = b
        eb[bone("Brow_" + side)].tail = b + Vector((0.0, 0.0, 0.8 * K))
        eb[bone("Brow_" + side)].parent = eb["Bip001Head"]
        lat = min(idx, key=lambda i: co[i].x) if side == "L" else max(idx, key=lambda i: co[i].x)
        med = max(idx, key=lambda i: co[i].x) if side == "L" else min(idx, key=lambda i: co[i].x)
        BROW_INNER_PIVOT[bone("Brow_" + side)] = co[lat].copy()
        BROW_INNER_ARM[bone("Brow_" + side)] = max(abs(co[lat].x - co[med].x), 1e-3)
        span = abs(co[lat].x - co[med].x)
        BROW_GRAD[side] = {i: (min(1.0, max(0.0, abs(co[i].x - co[med].x) / span)) if span > 1e-6 else 1.0)
                           for i in idx}
        inner = sorted(idx, key=lambda i: abs(co[i].x))[:max(1, int(len(idx) * BROW_INNER_SHARE))]
        BROW_INNER_SET[side] = set(inner)
        h = sum((co[i] for i in inner), Vector()) / len(inner)
        eb.new(bone("BrowIn_" + side)).head = h
        eb[bone("BrowIn_" + side)].tail = h + Vector((0.0, 0.0, 0.8 * K))
        eb[bone("BrowIn_" + side)].parent = eb["Bip001Head"]
        print("FACE_BROW", side, [round(v, 3) for v in b], "inner", [round(v, 3) for v in h],
              "arm", round(BROW_INNER_ARM[bone("Brow_" + side)], 3))
    face_idx = _face_vert_indices(mesh)
    mid_z = (EYE_L.z + MOUTH_Z) * 0.5
    for side, sx in (("L", -1.0), ("R", 1.0)):
        near = [co[i] for i in face_idx
                if abs(co[i].x - sx * 2.8 * K) < 1.5 * K and abs(co[i].z - mid_z) < 1.4 * K and co[i].y < -0.4 * K]
        h = (sum(near, Vector()) / len(near)) if near else Vector((sx * 2.8 * K, -1.4 * K, mid_z))
        eb.new(bone("Cheek_" + side)).head = h
        eb[bone("Cheek_" + side)].tail = h + Vector((0.0, 0.0, 0.9 * K))
        eb[bone("Cheek_" + side)].parent = eb["Bip001Head"]
        print("FACE_CHEEK", side, [round(v, 3) for v in h], len(near))
    nose = [co[i] for i in face_idx
            if abs(co[i].x) < 0.9 * K and co[i].y < -0.9 * K
            and MOUTH_Z + 1.9 * K < co[i].z < MOUTH_Z + 4.6 * K]
    nh = (sum(nose, Vector()) / len(nose)) if nose else Vector((0.0, -2.4 * K, MOUTH_Z + 3.2 * K))
    eb.new(bone("Nose")).head = nh
    eb[bone("Nose")].tail = nh + Vector((0.0, 0.0, 0.9 * K))
    eb[bone("Nose")].parent = eb["Bip001Head"]
    print("FACE_NOSE", [round(v, 3) for v in nh], len(nose))
    bpy.ops.object.mode_set(mode='OBJECT')
    for name in FACE_BONES:
        rot = arm.data.bones[name].matrix_local.to_3x3()
        inv = rot.inverted()
        AXES[name] = (inv @ Vector((1.0, 0.0, 0.0))).normalized()
        DIRS[name] = (inv @ Vector((0.0, 0.0, -1.0))).normalized()
    for side in ("L", "R"):
        name = bone("Eye_" + side)
        EYE_PIVOT_LOCAL[name] = arm.data.bones[name].matrix_local.inverted() @ _eye_pivot(side)
    print("FACE_BONES", len([b for b in arm.data.bones if b.name.startswith(PREFIX + "_")]))


def _lip_falloff(x):
    u = min(1.0, abs(x) / (2.4 * K))
    return math.cos(math.pi * 0.5 * u) ** LIP_FALL_POW


def _lip_up_vert(dz):
    return _smooth(1.0 - _ramp(dz, 0.30 * K, 0.65 * K))


def _face_components(mesh, face_slot):
    parent = {}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for p in mesh.data.polygons:
        if p.material_index != face_slot:
            continue
        vs = list(p.vertices)
        for v in vs:
            parent.setdefault(v, v)
        for v in vs[1:]:
            union(vs[0], v)
    comps = {}
    for v in parent:
        comps.setdefault(find(v), set()).add(v)
    return list(comps.values())


def _collect_weights(mesh):
    co = [v.co.copy() for v in mesh.data.vertices]
    names = [m.name for m in mesh.data.materials]
    face_slot = names.index(FACE_SLOT)
    face_verts = set()
    for p in mesh.data.polygons:
        if p.material_index == face_slot:
            face_verts.update(p.vertices)
    w = {}

    def put(vi, group, weight):
        if weight <= 0.0:
            return
        w.setdefault(vi, {})
        w[vi][group] = max(w[vi].get(group, 0.0), min(1.0, weight))

    jaw_top = MOUTH_Z + 0.9 * K
    jaw_bottom = MOUTH_Z - 8.0 * K
    for vi in face_verts:
        c = co[vi]
        if c.y < 0.8 * K and c.z < jaw_top and abs(c.x) < 6.2 * K and c.z > jaw_bottom:
            lat = _lip_falloff(c.x)
            dz = c.z - MOUTH_Z
            if dz >= 0.0:
                put(vi, bone("LipUp"), lat * _lip_up_vert(dz))
            else:
                put(vi, bone("Jaw"), lat)
            band = (_smooth(_ramp(abs(c.x), 1.20 * K, 1.60 * K))
                    * _smooth(1.0 - _ramp(abs(c.x), 1.60 * K, 2.00 * K)))
            if band > 0.0 and abs(dz) < 0.60 * K:
                put(vi, bone("MouthCorner_" + ("L" if c.x < 0.0 else "R")), band)
        for side, ctr in (("L", EYE_L), ("R", EYE_R)):
            d = (c - ctr).length
            dx = c.x - ctr.x
            drop = ctr.z - c.z
            up_mask = (_smooth(1.0 - _ramp(-drop, 0.95 * K, 1.30 * K))
                       * _smooth(1.0 - _ramp(abs(dx), 1.60 * K, 1.95 * K)))
            if up_mask > 0.0 and c.y < -0.8 * K and c.z > ctr.z - 0.15 * K and d < 3.1 * K:
                put(vi, bone("LidUp_" + side), _smooth(1.0 - _ramp(d, 0.9 * K, 3.1 * K)) * _lid_taper(dx, ctr.x) * up_mask)
            lo_mask = _smooth(1.0 - _ramp(abs(dx), 1.20 * K, 1.55 * K))
            if lo_mask > 0.0 and c.y < -0.8 * K and 0.15 * K <= drop <= 1.15 * K:
                put(vi, bone("LidLo_" + side), _smooth(1.0 - _ramp(d, 0.8 * K, 2.2 * K)) * lo_mask)
            if c.y < -0.8 * K and -0.30 * K <= drop <= 0.55 * K:
                u = min(1.0, max(0.0, (drop + 0.30 * K) / (0.85 * K)))
                band2 = _smooth(1.0 - _ramp(abs(dx), 1.20 * K, 1.55 * K))
                if band2 > 0.0 and d < 3.1 * K:
                    put(vi, bone("LidUp_" + side), 0.8 * band2 * (1.0 - u))
                    put(vi, bone("LidLo_" + side), 0.8 * band2 * u)
    for vi in face_verts:
        c = co[vi]
        have = sum(w[vi].values()) if vi in w else 0.0
        room = 1.0 - 0.5 * have
        ctr = EYE_L if c.x < 0.0 else EYE_R
        side = "L" if c.x < 0.0 else "R"
        dx = abs(c.x - ctr.x)
        if (c.y < -0.4 * K and 1.2 * K <= dx <= 5.0 * K and MOUTH_Z + 1.0 * K < c.z < ctr.z + 0.6 * K):
            fade = _smooth(1.0 - _ramp(dx, 4.2 * K, 5.0 * K))
            put(vi, bone("Cheek_" + side), 0.55 * fade * room)
        if (abs(c.x) < 0.9 * K and c.y < -0.9 * K and MOUTH_Z + 1.9 * K < c.z < MOUTH_Z + 4.6 * K):
            put(vi, bone("Nose"), 0.60 * room)
    brow_cards = _face_components(mesh, face_slot)
    for side, ctr in (("L", EYE_L), ("R", EYE_R)):
        for vi in PARTS["lash" + side]:
            put(vi, bone("LidUp_" + side), _lid_taper(co[vi].x - ctr.x, ctr.x))
        for vi in PARTS["eyeball"][side]["verts"]:
            put(vi, bone("Eye_" + side), 1.0)
        for card in brow_cards:
            if not card & set(PARTS["brow" + side]):
                continue
            xs = [abs(co[vi].x) for vi in card]
            inner, outer = min(xs), max(xs)
            for vi in card:
                for group in list(w.get(vi, {})):
                    if group.startswith(bone("Lid")):
                        del w[vi][group]
                span = outer - inner
                u = 1.0 if span < 1e-6 else (abs(co[vi].x) - inner) / span
                put(vi, bone("BrowIn_" + side), 0.8 * (1.0 - u))
                put(vi, bone("Brow_" + side), 0.8 * u)
    print("FACE_WEIGHT_VERTS", len(w))
    return w


def apply_weights(mesh):
    w = _collect_weights(mesh)
    base = {}
    for vi in w:
        base[vi] = [(g.group, g.weight) for g in mesh.data.vertices[vi].groups]
    for vi, add in w.items():
        added = sum(add.values())
        if added > 1.0:
            add = {group: val / added for group, val in add.items()}
        up_w = sum(val for group, val in add.items() if group.startswith(bone("LidUp_")))
        lo_w = sum(val for group, val in add.items() if group.startswith(bone("LidLo_")))
        if up_w > 0.0 or lo_w > 0.0:
            co = mesh.data.vertices[vi].co
            co.z -= up_w * REST_LID_DOWN_CM * K
            co.z += lo_w * REST_LID_UP_CM * K
        keep = 1.0 - sum(add.values())
        src = base[vi]
        total = sum(x for _g, x in src)
        for g, x in src:
            mesh.vertex_groups[g].add([vi], (x / total) * keep, 'REPLACE')
        for group, val in add.items():
            if group not in mesh.vertex_groups:
                mesh.vertex_groups.new(name=group)
            mesh.vertex_groups[group].add([vi], val, 'REPLACE')
    print("FACE_WEIGHTS_APPLIED", len(w))


def _rigid_local(name, rest, angle_deg):
    rot = rest[name].to_3x3()
    return rest[name] @ Matrix.Rotation(math.radians(angle_deg), 4, AXES[name]) @ rest[name].inverted()


def _shift_local(name, rest, dist_cm, axis=None):
    rot = rest[name].to_3x3()
    direction = DIRS[name] if axis is None else (rot.inverted() @ axis).normalized()
    return Matrix.Translation(rot @ (direction * dist_cm))


def _yaw_about_pivot(name, rest, angle_deg):
    pivot = rest[name] @ EYE_PIVOT_LOCAL[name]
    spin = Matrix.Rotation(math.radians(angle_deg), 4, Vector((0.0, 0.0, 1.0)))
    return Matrix.Translation(pivot) @ spin @ Matrix.Translation(-pivot)


def _brow_inner(name, dist_cm):
    angle = math.degrees(math.asin(min(1.0, dist_cm / BROW_INNER_ARM[name])))
    sign = 1.0 if name.endswith("_R") else -1.0
    pivot = BROW_INNER_PIVOT[name]
    spin = Matrix.Rotation(math.radians(sign * angle), 4, Vector((0.0, 1.0, 0.0)))
    return Matrix.Translation(pivot) @ spin @ Matrix.Translation(-pivot)


def pose_face(pose_world, params, rest):
    base = pose_world.get("Bip001Head", rest["Bip001Head"]) @ rest["Bip001Head"].inverted()
    for group in FACE_BONES:
        pose_world[group] = base @ rest[group]
    jaw = params.get("jaw", 0.0)
    pose_world[bone("Jaw")] = base @ _rigid_local(bone("Jaw"), rest, JAW_MAX_DEG * jaw) @ rest[bone("Jaw")]
    for side, sx in (("L", -1.0), ("R", 1.0)):
        name = bone("MouthCorner_" + side)
        out = _shift_local(name, rest, sx * CORNER_OUT_CM * K * jaw, Vector((1.0, 0.0, 0.0)))
        pose_world[name] = base @ out @ rest[name]
    pose_world[bone("LipLo")] = base @ rest[bone("LipLo")]
    pose_world[bone("LipUp")] = base @ _shift_local(bone("LipUp"), rest, params.get("lip_press", 0.0) * K) @ rest[bone("LipUp")]
    for side in ("L", "R"):
        blink = params.get("blink_" + side, 0.0)
        gaze = params.get("gaze_" + side, 0.0)
        yaw = params.get("yaw_" + side, 0.0)
        lid = params.get("lid_" + side, 0.0)
        closed = BLINK_DOWN_CM * blink + lid
        drop = closed - params.get("lift_" + side, 0.0)
        up = _shift_local(bone("LidUp_" + side), rest, drop)
        up = Matrix.Translation(rest[bone("LidUp_" + side)].to_3x3()
                                @ Vector((0.0, -BLINK_FORWARD_CM * max(0.0, drop) / BLINK_DOWN_CM, 0.0))) @ up
        pose_world[bone("LidUp_" + side)] = base @ up @ rest[bone("LidUp_" + side)]
        lo = _shift_local(bone("LidLo_" + side), rest, -closed * LOWER_LID_RATIO)
        pose_world[bone("LidLo_" + side)] = base @ lo @ rest[bone("LidLo_" + side)]
        eye = _yaw_about_pivot(bone("Eye_" + side), rest, yaw) @ _rigid_local(
            bone("Eye_" + side), rest, GAZE_MAX_DEG * gaze + params.get("gaze_deg_" + side, 0.0))
        pose_world[bone("Eye_" + side)] = base @ eye @ rest[bone("Eye_" + side)]
        brow = _shift_local(bone("Brow_" + side), rest, -BROW_UP_CM * K * params.get("brow_" + side, 0.0))
        inner = _brow_inner(bone("Brow_" + side), params.get("browin_" + side, 0.0) * K)
        pose_world[bone("Brow_" + side)] = base @ inner @ brow @ rest[bone("Brow_" + side)]
        pose_world[bone("BrowIn_" + side)] = base @ inner @ brow @ rest[bone("BrowIn_" + side)]
