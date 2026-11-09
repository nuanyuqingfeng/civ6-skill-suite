import math

from mathutils import Matrix, Quaternion, Vector

DT = 1.0 / 30.0
GRAVITY = Vector((0.0, 0.0, -980.0))
GRAVITY_SCALE = 0.3
CURVE_TIP = 0.05

SPRING_STIFFNESS = 16.0
SPRING_DAMPING = 2.4

CHAIN_STIFFNESS = 1.0
CURVE_ROOT = 0.18
CHAIN_DAMPING = 2.0
CONSTRAINT_ITER = 12
COLLISION_MARGIN = 0.3
COLLISION_TOP = 105.0

CHAINS = (
    ("Bone_Hair009_L", "Bone_Hair010_L", "Bone_Hair011_L", "Bone_Hair012_L",
     "Bone_Hair013_L", "Bone_Hair015_L", "Bone_Hair016_L", "Bone_Hair017_L"),
    ("Bone_Hair019_R", "Bone_Hair020_R", "Bone_Hair021_R", "Bone_Hair022_R",
     "Bone_Hair023_R", "Bone_Hair025_R", "Bone_Hair026_R", "Bone_Hair027_R"),
)
CHAIN_BONES = frozenset(name for chain in CHAINS for name in chain)

FAMILIES = ("Hair", "Skirt", "Piao")
# 实际参与仿真的族：发丝由 RibbonAnim 原样驱动时关掉 Hair，避免在源数据上再叠弹簧
ACTIVE_FAMILIES = FAMILIES
FAMILY_TARGET = {"Hair": (1.0, 2.0), "Skirt": (1.0, 2.2), "Piao": (0.8, 1.8)}
CHAIN_TARGET = (2.5, 10.0)
CLIP_TARGET = {
    "JX_FirstMeet": (1.2, 1.4, 1.2),
    "JX_DeclareWarHuman": (1.8, 2.0, 1.8),
    "JX_DeclareWarAI": (1.8, 2.0, 1.8),
    "JX_Kudos": (1.6, 1.8, 1.6),
    "JX_Warning": (1.3, 1.5, 1.3),
    "JX_Defeat": (1.3, 1.5, 1.3),
}
CHAIN_CLIP_TARGET = {
    "JX_FirstMeet": 6.0,
    "JX_DeclareWarHuman": 9.0,
    "JX_DeclareWarAI": 9.0,
    "JX_Kudos": 7.0,
    "JX_Warning": 6.0,
    "JX_Defeat": 6.0,
}

FRONT_HAIR = ("Bone_Hair033_L", "Bone_Hair034_L", "Bone_Hair035_L",
              "Bone_Hair037_R", "Bone_Hair038_R", "Bone_Hair039_R")
FRONT_HAIR_FACTOR = 0.35

IDLE_RAMP = 40
LEVEL_CAP = 10.0
CALIBRATION_ROUNDS = 5
CALIBRATION_TOL = 0.1
CALIBRATION_GAIN = 0.7
SEAM_PASSES = 2


def smoothstep(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def swing(q):
    if q.w < 0.0:
        q = Quaternion((-q.w, -q.x, -q.y, -q.z))
    w = min(1.0, q.w)
    angle = 2.0 * math.acos(w)
    s = math.sqrt(max(1e-12, 1.0 - w * w))
    return Vector((q.x / s, q.y / s, q.z / s)), angle


def set_families(names):
    global ACTIVE_FAMILIES
    ACTIVE_FAMILIES = tuple(names)


def family_of(name):
    if name in CHAIN_BONES:
        return None
    for fam in FAMILIES:
        if name.startswith("Bone_" + fam):
            return fam if fam in ACTIVE_FAMILIES else None
    return None


def curve_table(action):
    table = {}
    for fc in action.fcurves:
        path = fc.data_path
        if not path.startswith('pose.bones["'):
            continue
        parts = path.rsplit("].", 1)
        if len(parts) != 2:
            continue
        name = parts[0].split('"')[1]
        table.setdefault(name, {}).setdefault(parts[1], {})[fc.array_index] = fc
    return table


def sample(slot, frame, default):
    out = list(default)
    for index, fc in slot.items():
        out[index] = fc.evaluate(frame)
    return out


def body_profile(body):
    rows = []
    groups = {g.index: g.name for g in body.vertex_groups}
    verts = []
    for v in body.data.vertices:
        best = None
        for g in v.groups:
            if best is None or g.weight > best[1]:
                best = (groups[g.group], g.weight)
        if best is not None and (best[0].startswith("Bone_Hair") or best[0].startswith("Bone_Piao")):
            continue
        verts.append(v.co)
    for z0 in range(15, 140, 5):
        band = [co for co in verts if z0 <= co.z < z0 + 5]
        if len(band) < 30:
            continue
        rad = sorted(math.hypot(co.x, co.y) for co in band)
        rows.append((z0 + 2.5, rad[int(len(rad) * 0.98)]))
    return rows


def profile_radius(rows, z):
    if z <= rows[0][0]:
        return rows[0][1]
    for i in range(1, len(rows)):
        if z <= rows[i][0]:
            z0, r0 = rows[i - 1]
            z1, r1 = rows[i]
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return rows[-1][1]


def prepare(arm, body, anim_scale):
    parents = {}
    rest_rel = {}
    for b in arm.data.bones:
        parents[b.name] = b.parent.name if b.parent else None
        rest_rel[b.name] = (b.matrix_local.copy() if b.parent is None
                            else b.parent.matrix_local.inverted() @ b.matrix_local)
    order = []
    seen = set()

    def visit(name):
        if name in seen:
            return
        seen.add(name)
        if parents[name] is not None:
            visit(parents[name])
        order.append(name)

    for name in parents:
        visit(name)
    chains = []
    for names in CHAINS:
        lengths = [rest_rel[names[i + 1]].translation.length for i in range(len(names) - 1)]
        lengths.append(sum(lengths) / len(lengths))
        chains.append({"bones": list(names), "lengths": lengths})
    affected = [n for n in order if family_of(n) is not None]
    affected.extend(n for names in CHAINS for n in names)
    needed = set(affected)
    for name in affected:
        cur = parents[name]
        while cur is not None and cur not in needed:
            needed.add(cur)
            cur = parents[cur]
    seg_len = {}
    for name in parents:
        kids = [n for n in parents if parents[n] == name]
        if kids:
            seg_len[name] = rest_rel[kids[0]].translation.length
        elif parents[name] is not None:
            seg_len[name] = rest_rel[name].translation.length
        else:
            seg_len[name] = 1.0
    return {"parents": parents, "rest_rel": rest_rel,
            "order": order, "chains": chains, "affected": affected, "needed": needed,
            "profile": body_profile(body), "anim_scale": anim_scale, "seg_len": seg_len}


def base_worlds(rig, curves, frame):
    world = {}
    cache = {}
    scale = rig["anim_scale"]
    for name in rig["order"]:
        if name not in rig["needed"]:
            continue
        slot = curves.get(name, {})
        loc = Vector(sample(slot.get("location", {}), frame, (0.0, 0.0, 0.0))) * scale
        quat = Quaternion(sample(slot.get("rotation_quaternion", {}), frame, (1.0, 0.0, 0.0, 0.0)))
        size = Vector(sample(slot.get("scale", {}), frame, (1.0, 1.0, 1.0)))
        basis = Matrix.LocRotScale(loc, quat, size)
        cache[name] = (loc, quat, size)
        parent = rig["parents"][name]
        world[name] = basis if parent is None else world[parent] @ basis
    return world, cache


def push_out(rig, p, amount):
    if p.z >= COLLISION_TOP:
        return
    r = profile_radius(rig["profile"], p.z) + COLLISION_MARGIN
    d = math.hypot(p.x, p.y)
    if 1e-6 < d < r:
        target = d + (r - d) * amount
        s = target / d
        p.x *= s
        p.y *= s


def chain_step(rig, chain, world, state, key, stiffness):
    bones = chain["bones"]
    lengths = chain["lengths"]
    n = len(bones)
    anchor = world[bones[0]].translation.copy()
    base_rot = [world[b].to_quaternion().normalized() for b in bones]
    base_head = [world[b].translation.copy() for b in bones]
    targets = [base_head[i + 1].copy() for i in range(n - 1)]
    tip_dir = (base_head[n - 1] - base_head[n - 2]).normalized()
    targets.append(base_head[n - 1] + tip_dir * lengths[n - 1])
    base_dirs = [(targets[i] - base_head[i]).normalized() for i in range(n)]
    curve = [CURVE_ROOT + (CURVE_TIP - CURVE_ROOT) * ((i - 1) / (n - 2)) if i >= 1 else 0.0
             for i in range(n)]
    inv_mass = [1.0 / (1.0 - 0.4 * (i / (n - 1))) for i in range(n)]
    st = state.get(key)
    if st is None:
        st = {"pos": [t.copy() for t in targets], "prev": [t.copy() for t in targets]}
        state[key] = st
    pos = st["pos"]
    prev = st["prev"]
    pos[0] = targets[0].copy()
    prev[0] = targets[0].copy()
    damp = math.exp(-CHAIN_DAMPING * DT)
    for i in range(1, n):
        d = pos[i] - pos[i - 1]
        if d.length > 1e-6:
            axis = d.normalized()
            acc = GRAVITY - axis * GRAVITY.dot(axis)
        else:
            acc = GRAVITY.copy()
        velocity = (pos[i] - prev[i]) * damp
        prev[i] = pos[i].copy()
        pos[i] = pos[i] + velocity + acc * (GRAVITY_SCALE * DT * DT)
    for _ in range(CONSTRAINT_ITER):
        for i in range(1, n):
            a = pos[i - 1]
            b = pos[i]
            d = b - a
            dist = d.length
            if dist < 1e-6:
                continue
            diff = (dist - lengths[i]) / dist
            wa = 0.0 if i == 1 else inv_mass[i - 1]
            wb = inv_mass[i]
            total = wa + wb
            pos[i] = b - d * (diff * wb / total)
            if wa > 0.0:
                pos[i - 1] = a + d * (diff * wa / total)
    for i in range(1, n):
        head = pos[i - 1]
        cur = pos[i] - head
        if cur.length < 1e-6:
            continue
        q = cur.normalized().rotation_difference(base_dirs[i])
        if q.angle < 1e-6:
            continue
        q = Quaternion(q.axis, q.angle * min(0.95, stiffness * curve[i]))
        for j in range(i, n):
            pos[j] = head + q @ (pos[j] - head)
    for _ in range(2):
        for i in range(1, n):
            push_out(rig, pos[i], 0.6)
        for _ in range(4):
            for i in range(1, n):
                a = pos[i - 1]
                b = pos[i]
                d = b - a
                dist = d.length
                if dist < 1e-6:
                    continue
                diff = (dist - lengths[i]) / dist
                wa = 0.0 if i == 1 else inv_mass[i - 1]
                wb = inv_mass[i]
                total = wa + wb
                pos[i] = b - d * (diff * wb / total)
                if wa > 0.0:
                    pos[i - 1] = a + d * (diff * wa / total)
    rot = [base_rot[0]]
    head = anchor
    for i in range(1, n):
        new_dir = pos[i] - head
        base_dir = targets[i] - base_head[i]
        if new_dir.length < 1e-6 or base_dir.length < 1e-6:
            rot.append(base_rot[i])
        else:
            q = base_dir.normalized().rotation_difference(new_dir.normalized())
            rot.append((q @ base_rot[i]).normalized())
        head = pos[i]
    return rot


def run_pass(rig, curves, frames, state, level_of, stiffness, emit, simulate_chains=True):
    out = {} if emit else None
    peaks = []
    for frame in frames:
        world_base, cache = base_worlds(rig, curves, frame)
        rot_final = {}
        world_final = {}
        for name in rig["order"]:
            if name not in rig["needed"]:
                continue
            if name in CHAIN_BONES:
                continue
            parent = rig["parents"][name]
            parent_rot = rot_final[parent] if parent is not None else Quaternion()
            parent_world = world_final[parent] if parent is not None else Matrix.Identity(4)
            loc, quat, size = cache[name]
            fam = family_of(name)
            if fam is None:
                rot_final[name] = (parent_rot @ quat).normalized()
                world_final[name] = world_base[name]
                continue
            target = (parent_rot @ quat).normalized()
            st = state.get(name)
            if st is None:
                st = [Vector((0.0, 0.0, 0.0)), target.copy()]
                state[name] = st
            axis, angle = swing((target @ st[1].inverted()).normalized())
            omega = st[0] + (axis * (SPRING_STIFFNESS * angle) - st[0] * SPRING_DAMPING) * DT
            speed = omega.length
            if speed > 0.0:
                st[1] = (Quaternion(omega / speed, speed * DT) @ st[1]).normalized()
            st[0] = omega
            axis, angle = swing((st[1] @ target.inverted()).normalized())
            factor = level_of(frame, fam)
            if name in FRONT_HAIR:
                factor *= FRONT_HAIR_FACTOR
            rot = (Quaternion(axis, angle * factor) @ target).normalized() if angle > 0.0 else st[1]
            rot_final[name] = rot
            basis_rot = parent_rot.inverted() @ rot
            world_final[name] = parent_world @ Matrix.LocRotScale(loc, basis_rot, size)
            if emit:
                out.setdefault(name, {})[frame] = basis_rot
        for index, chain in enumerate(rig["chains"] if simulate_chains else ()):
            rots = chain_step(rig, chain, world_base, state, "chain%d" % index, stiffness)
            for i, name in enumerate(chain["bones"]):
                loc, quat, size = cache[name]
                parent_world = world_final[rig["parents"][name]]
                basis_rot = (rots[i - 1] if i > 0 else world_base[rig["parents"][name]].to_quaternion().normalized())
                basis_rot = basis_rot.inverted() @ rots[i]
                rot_final[name] = rots[i]
                world_final[name] = parent_world @ Matrix.LocRotScale(loc, basis_rot, size)
                if emit:
                    out.setdefault(name, {})[frame] = basis_rot
        current = {"Hair": 0.0, "Skirt": 0.0, "Piao": 0.0, "Chain": 0.0}
        for name in rig["affected"]:
            if name in CHAIN_BONES and not simulate_chains:
                continue
            tail = Vector((0.0, rig["seg_len"][name], 0.0))
            delta = (world_final[name] @ tail - world_base[name] @ tail).length
            fam = "Chain" if name in CHAIN_BONES else family_of(name)
            if delta > current[fam]:
                current[fam] = delta
        peaks.append(current)
    return out, peaks


def zone_peak(peaks, index, fam):
    return max(peaks[i][fam] for i in index)


def bake(arm, action, clip, total, window, body=None, anim_scale=1.0, chain_physics=True):
    rig = prepare(arm, body, anim_scale)
    curves = curve_table(action)
    frames = list(range(1, total + 1))
    span = range(len(frames))
    quiet_idx = [i for i, f in enumerate(frames) if idle_weight(f, window) == 0.0]
    think_idx = [i for i, f in enumerate(frames) if idle_weight(f, window) == 1.0]
    state = {}
    stiffness = CHAIN_STIFFNESS
    _, peaks = run_pass(rig, curves, frames, state, lambda f, fam: 1.0, stiffness, False,
                        simulate_chains=chain_physics)
    chain_raw = zone_peak(peaks, think_idx if clip == "JX_IDLE" else span, "Chain") if chain_physics else 0.0
    if clip == "JX_IDLE":
        if chain_physics:
            stiffness = min(2.5, max(0.2, stiffness * (chain_raw / max(CHAIN_TARGET[1], 1e-4)) ** CALIBRATION_GAIN))
        levels = {fam: [FAMILY_TARGET[fam][0] / max(zone_peak(peaks, quiet_idx, fam), 1e-4),
                        FAMILY_TARGET[fam][1] / max(zone_peak(peaks, think_idx, fam), 1e-4)]
                  for fam in ACTIVE_FAMILIES}

        def level_of(frame, fam):
            low, high = levels[fam]
            return low + (high - low) * idle_weight(frame, window)

        print("SECONDARY_PROBE", clip, "chain_raw", round(chain_raw, 2),
              "short_raw", " ".join("%s=%.2f/%.2f" % (fam, zone_peak(peaks, quiet_idx, fam),
                                                      zone_peak(peaks, think_idx, fam))
                                    for fam in ACTIVE_FAMILIES),
              "k", round(stiffness, 3))
    else:
        if chain_physics:
            stiffness = min(2.5, max(0.2, stiffness * (chain_raw / max(CHAIN_CLIP_TARGET[clip], 1e-4)) ** CALIBRATION_GAIN))
        targets = {fam: CLIP_TARGET[clip][i] for i, fam in enumerate(FAMILIES)}
        levels = {fam: [targets[fam] / max(zone_peak(peaks, span, fam), 1e-4)]
                  for fam in ACTIVE_FAMILIES}

        def level_of(frame, fam):
            return levels[fam][0]

        print("SECONDARY_PROBE", clip, "chain_raw", round(chain_raw, 2),
              "short_raw", " ".join("%s=%.2f" % (fam, zone_peak(peaks, span, fam)) for fam in ACTIVE_FAMILIES),
              "k", round(stiffness, 3))
    out = None
    for attempt in range(CALIBRATION_ROUNDS):
        if clip != "JX_IDLE":
            state.clear()
        out, peaks = run_pass(rig, curves, frames, state, level_of, stiffness, True,
                              simulate_chains=chain_physics)
        if clip == "JX_IDLE":
            chain_now = zone_peak(peaks, think_idx, "Chain") if chain_physics else 0.0
            actual = {fam: (zone_peak(peaks, quiet_idx, fam), zone_peak(peaks, think_idx, fam))
                      for fam in ACTIVE_FAMILIES}
            settled = ((not chain_physics or abs(chain_now / CHAIN_TARGET[1] - 1.0) < CALIBRATION_TOL)
                       and all(abs(actual[fam][0] / FAMILY_TARGET[fam][0] - 1.0) < CALIBRATION_TOL
                               and abs(actual[fam][1] / FAMILY_TARGET[fam][1] - 1.0) < CALIBRATION_TOL
                               for fam in ACTIVE_FAMILIES))
            print("SECONDARY_CAL", clip, attempt, "chain", round(chain_now, 2),
                  "quiet", round(zone_peak(peaks, quiet_idx, "Chain"), 2),
                  " ".join("%s=%.2f/%.2f" % (fam, actual[fam][0], actual[fam][1]) for fam in ACTIVE_FAMILIES),
                  "k", round(stiffness, 3))
            if settled:
                break
            if chain_physics:
                stiffness = min(2.5, max(0.2, stiffness * (chain_now / max(CHAIN_TARGET[1], 1e-4)) ** CALIBRATION_GAIN))
            for fam in ACTIVE_FAMILIES:
                for slot, key in ((0, 0), (1, 1)):
                    ratio = FAMILY_TARGET[fam][key] / max(actual[fam][key], 1e-4)
                    levels[fam][slot] = min(LEVEL_CAP, levels[fam][slot] * ratio ** CALIBRATION_GAIN)
        else:
            chain_now = zone_peak(peaks, span, "Chain") if chain_physics else 0.0
            actual = {fam: zone_peak(peaks, span, fam) for fam in ACTIVE_FAMILIES}
            targets = {fam: CLIP_TARGET[clip][i] for i, fam in enumerate(FAMILIES)}
            settled = ((not chain_physics or abs(chain_now / CHAIN_CLIP_TARGET[clip] - 1.0) < CALIBRATION_TOL)
                       and all(abs(actual[fam] / targets[fam] - 1.0) < CALIBRATION_TOL
                               for fam in ACTIVE_FAMILIES))
            print("SECONDARY_CAL", clip, attempt, "chain", round(chain_now, 2),
                  " ".join("%s=%.2f" % (fam, actual[fam]) for fam in ACTIVE_FAMILIES), "k", round(stiffness, 3))
            if settled:
                break
            if chain_physics:
                stiffness = min(2.5, max(0.2, stiffness * (chain_now / max(CHAIN_CLIP_TARGET[clip], 1e-4)) ** CALIBRATION_GAIN))
            for fam in ACTIVE_FAMILIES:
                ratio = targets[fam] / max(actual[fam], 1e-4)
                levels[fam][0] = min(LEVEL_CAP, levels[fam][0] * ratio ** CALIBRATION_GAIN)
    if clip == "JX_IDLE":
        for _ in range(SEAM_PASSES):
            out, peaks = run_pass(rig, curves, frames, state, level_of, stiffness, True,
                                  simulate_chains=chain_physics)
    seam = 0.0
    for name, series in out.items():
        seam = max(seam, math.degrees(swing((series[frames[-1]] @ series[frames[0]].inverted()).normalized())[1]))
    for name in sorted(out):
        path = 'pose.bones["%s"].rotation_quaternion' % name
        for fc in [c for c in action.fcurves if c.data_path == path]:
            action.fcurves.remove(fc)
        series = out[name]
        values = {}
        prev = None
        for frame in frames:
            q = series[frame].normalized()
            if prev is not None and q.dot(prev) < 0.0:
                q = Quaternion((-q.w, -q.x, -q.y, -q.z))
            prev = q
            values[frame] = q
        for index in range(4):
            fc = action.fcurves.new(path, index=index, action_group=name)
            fc.keyframe_points.add(total)
            for kp, frame in zip(fc.keyframe_points, frames):
                kp.co = (float(frame), values[frame][index])
                kp.interpolation = 'LINEAR'
            fc.update()
    final = {fam: zone_peak(peaks, span, fam) for fam in ("Hair", "Skirt", "Piao", "Chain")}
    print("SECONDARY", clip, "bones", len(out), "seam_deg", round(seam, 3),
          "peak_cm", " ".join("%s=%.2f" % (fam, final[fam]) for fam in ("Chain", "Hair", "Skirt", "Piao")),
          "k", round(stiffness, 3))
    return len(out)


def idle_weight(frame, window):
    start, end = window
    if frame <= start - IDLE_RAMP:
        return 0.0
    if frame < start:
        return smoothstep((frame - (start - IDLE_RAMP)) / IDLE_RAMP)
    if frame <= end:
        return 1.0
    if frame < end + IDLE_RAMP:
        return 1.0 - smoothstep((frame - end) / IDLE_RAMP)
    return 0.0



