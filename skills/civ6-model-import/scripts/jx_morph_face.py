"""把《鸣潮》86 个面部 MorphTarget（形态键）转换成骨骼动画通道。

Civ6 的领袖动画只认骨骼曲线，源模型的形态键无法直接导出。这里用逐骨加权刚体拟合
（weighted Kabsch）：对每个形态键、每根 JX 面骨，取该骨权重大于阈值的顶点，求
最小二乘的旋转+平移，把顶点位移还原成该骨的局部姿态增量；再按表情权重叠加到
七段动画的面骨曲线上。全部 86 个形态键都会建好映射，动画侧按片段取用其中
的微笑/愤怒/悲伤/专注等预置。
"""
import math

import numpy as np
from mathutils import Matrix, Quaternion, Vector

W_MIN = 0.02
MIN_VERTS = 18
# 单骨转角上限：眉/睑这类薄片区绕骨心转一点就会把卡片几何顶出脸面，
# 12° 以内配合质心位移保留，形变幅度仍由平移承担
MAX_BONE_ROT_DEG = 12.0
MIN_DELTA_CM = 0.08
# 拉伸诊断关注的形态键（表情预置里真正会用到、且历史上出过尖刺的）
STRETCH_WATCH = ("B_Anger", "B_Sad", "B_Flat", "B_Happy", "B_Cheerful",
                 "E_Smile_L", "E_Smile_R", "E_Focus", "E_Close",
                 "C_Up_Face", "C_Down_Face")

# 片段内的表情预置：窗口按总帧数比例给出（起, 止），两端各 8% 做 smoothstep 过渡
PRESETS = {
    "JX_Kudos": (("Smile", (0.06, 0.94)),),
    "JX_DeclareWarHuman": (("Anger", (0.03, 0.97)),),
    "JX_DeclareWarAI": (("Anger", (0.03, 0.97)),),
    "JX_Warning": (("Focus", (0.04, 0.96)),),
    "JX_Defeat": (("Sad", (0.03, 0.97)),),
    "JX_FirstMeet": (("Focus", (0.00, 1.00)),),
}

# 待机段不叠加任何形态键表情层：思考段沿用原有的骨驱动表情，
# 形态键拟合在眉/眼睑的大幅度上误差会被放大成面部拉伸，故待机整体保持原样

# 形态键按源数据满强度（1.0）驱动，不再做人工衰减
EXPRESSIONS = {
    "Smile": {"B_Happy": 1.0, "E_Smile_L": 1.0, "E_Smile_R": 1.0,
              "M_Smile_L": 1.0, "M_Smile_R": 1.0, "C_Up_Face": 1.0},
    "Anger": {"B_Anger": 1.0, "E_Anger": 1.0, "M_Anger": 1.0, "C_Down_Face": 1.0},
    "Sad": {"B_Sad": 1.0, "E_Sad": 1.0, "M_Ennui_L": 1.0, "M_Ennui_R": 1.0},
    "Focus": {"E_Focus": 1.0, "B_Flat": 1.0},
}


def _arr(mat3):
    return np.array([[mat3[i][j] for j in range(3)] for i in range(3)], dtype=np.float64)


def capture(mesh):
    """读取形态键相对基础网格的逐顶点位移（导入尺度、未缩放/未旋转）。"""
    keys = mesh.data.shape_keys.key_blocks if mesh.data.shape_keys else []
    if not keys:
        return None
    base = np.array([v.co[:] for v in keys[0].data], dtype=np.float64)
    out = {"deltas": {}}
    for kb in keys[1:]:
        pos = np.array([v.co[:] for v in kb.data], dtype=np.float64)
        out["deltas"][kb.name] = pos - base
    print("MORPH_CAPTURED", len(out["deltas"]))
    return out


def _face_weights(mesh):
    groups = {g.name: g.index for g in mesh.vertex_groups}
    bones = sorted(n for n in groups if n.startswith("JX_"))
    idx = {n: groups[n] for n in bones}
    weight = {n: np.zeros(len(mesh.data.vertices), dtype=np.float64) for n in bones}
    for v in mesh.data.vertices:
        for g in v.groups:
            for n, gi in idx.items():
                if g.group == gi:
                    weight[n][v.index] = g.weight
    print("MORPH_FACE_WEIGHTS", len(bones),
          [(n, int((weight[n] > W_MIN).sum())) for n in bones])
    return bones, weight


def _fit(p, q, w, max_rot_deg=180.0):
    sw = w.sum()
    cp = (p * w[:, None]).sum(0) / sw
    cq = (q * w[:, None]).sum(0) / sw
    h = ((p - cp) * w[:, None]).T @ (q - cq)
    u, _, vt = np.linalg.svd(h)
    d = np.sign(np.linalg.det(vt.T @ u.T))
    rot = vt.T @ np.diag([1.0, 1.0, d]) @ u.T
    t = cq - rot @ cp
    if max_rot_deg < 180.0:
        # 小顶点池会拟出夸张的单骨转角：满形态键时这类骨会把蒙皮扫出拉伸。
        # 限幅只裁转角、质心位移完全保留，形状不变形，只是不再整片扫动。
        rq = Matrix(((float(rot[0][0]), float(rot[0][1]), float(rot[0][2])),
                     (float(rot[1][0]), float(rot[1][1]), float(rot[1][2])),
                     (float(rot[2][0]), float(rot[2][1]), float(rot[2][2])))).to_quaternion()
        if rq.angle > math.radians(max_rot_deg):
            rq = Quaternion(rq.axis, math.radians(max_rot_deg))
            m3 = rq.to_matrix()
            rot = np.array([[m3[i][j] for j in range(3)] for i in range(3)])
            t = cq - rot @ cp
    res = float(np.sqrt(((((p @ rot.T) + t - q) * w[:, None]) ** 2).sum() / sw))
    return rot, t, res


def _mix(entry, ps, ws):
    out = np.zeros_like(ps)
    for bone, m in entry.items():
        r3 = np.array([[m[i][j] for j in range(3)] for i in range(3)], dtype=np.float64)
        t3 = np.array([m[i][3] for i in range(3)], dtype=np.float64)
        out += ws[bone][:, None] * ((ps @ r3.T) + t3 - ps)
    return out


def _refine(ps, d, ws, entry, iters=10):
    """LBS 一致性修正。逐骨独立的 Kabsch 求的是 p→p+d 的刚体，而顶点实际只收到
    w·(T p − p)，权重大小不等于 1 时整片就短了一截。这里固定权重逐骨重解：
    目标取 p + 残差/w，权重取 w²，每轮都要求总误差不上升。"""
    names = list(entry)
    cur = dict(entry)
    err = float((( _mix(cur, ps, ws) - d) ** 2).sum())
    start = err
    for _ in range(iters):
        prev = dict(cur)
        for bone in names:
            part = np.zeros_like(ps)
            for other in names:
                if other == bone:
                    continue
                m = cur[other]
                r3 = np.array([[m[i][j] for j in range(3)] for i in range(3)], dtype=np.float64)
                t3 = np.array([m[i][3] for i in range(3)], dtype=np.float64)
                part += ws[other][:, None] * ((ps @ r3.T) + t3 - ps)
            keep = ws[bone] > 0.12
            if int(keep.sum()) < 6:
                continue
            w = ws[bone][keep]
            target = ps[keep] + (d[keep] - part[keep]) / w[:, None]
            rot, tr, _ = _fit(ps[keep], target, w * w, MAX_BONE_ROT_DEG)
            cur[bone] = _world(rot, tr)
        new = float(((_mix(cur, ps, ws) - d) ** 2).sum())
        if new > err:
            cur = prev
            break
        if err - new < err * 1e-6:
            err = new
            break
        err = new
    return cur, float(np.sqrt(start / len(ps))), float(np.sqrt(err / len(ps)))


def _top_stretch(mix, edges, count):
    if edges is None or not len(edges):
        return []
    diff = mix[edges[:, 0]] - mix[edges[:, 1]]
    mag = np.sqrt((diff ** 2).sum(1))
    order = np.argsort(-mag)[:count]
    return [(int(edges[i, 0]), int(edges[i, 1]), float(mag[i])) for i in order]


def _dom(weight, bones, vi):
    best, name = -1.0, "head"
    for bone in bones:
        w = float(weight[bone][vi])
        if w > best:
            best, name = w, bone
    return name if best > 0.0 else "head"


def _world(rot, t):
    return Matrix(((float(rot[0][0]), float(rot[0][1]), float(rot[0][2]), float(t[0])),
                   (float(rot[1][0]), float(rot[1][1]), float(rot[1][2]), float(t[1])),
                   (float(rot[2][0]), float(rot[2][1]), float(rot[2][2]), float(t[2])),
                   (0.0, 0.0, 0.0, 1.0)))


def build(arm, mesh, captured, k, align_deg):
    """建立 {morph: {bone: 世界系刚体增量}}；p 用最终（缩放+旋转后）网格坐标。

    表里存的是世界系变换 W：pose() 把它合成为 P' = P @ rest⁻¹ @ W @ rest，
    顶点拿到的蒙皮变换正好是 W，与 _fit 的最小二乘目标一致。
    存成 rest⁻¹ W rest 会让顶点实际拿到 rest⁻¹ W rest，多套一层共轭，
    薄片面片会被甩出几十厘米。"""
    bones, weight = _face_weights(mesh)
    edges = np.array([[e.vertices[0], e.vertices[1]] for e in mesh.data.edges], dtype=np.int64) \
        if len(mesh.data.edges) else None
    p = np.array([v.co[:] for v in mesh.data.vertices], dtype=np.float64)
    rz = _arr(Matrix.Rotation(math.radians(align_deg), 4, 'Z'))
    table = {"__bones__": bones}
    wsum = np.zeros(len(p), dtype=np.float64)
    for bone in bones:
        wsum += weight[bone]
    act = np.flatnonzero(wsum > 0.0)
    ps = p[act]
    ws = {bone: weight[bone][act] for bone in bones}
    worst = []
    for name, delta in captured["deltas"].items():
        d = (rz @ (float(k) * delta).T).T
        moved = np.sqrt((delta ** 2).sum(1))
        entry = {}
        for bone in bones:
            w = weight[bone]
            sel = w > W_MIN
            if int(sel.sum()) < MIN_VERTS or float(moved[sel].max()) < MIN_DELTA_CM / float(k):
                continue
            rot, tr, _ = _fit(p[sel], p[sel] + d[sel], w[sel], MAX_BONE_ROT_DEG)
            entry[bone] = _world(rot, tr)
        if entry:
            entry, err_before, err_after = _refine(ps, d[act], ws, entry)
            print("MORPH_REFINE", name, round(err_before, 4), "->", round(err_after, 4))
        table[name] = entry
        # 覆盖率诊断：用各骨权重把拟合位移混合后与真实位移比较
        mix = np.zeros_like(p)
        for bone, world in entry.items():
            rot3 = np.array([[world[i][j] for j in range(3)] for i in range(3)])
            t3 = np.array([world[i][3] for i in range(3)])
            dm = (rot3 @ p.T).T + t3 - p
            mix += weight[bone][:, None] * dm
        err = float(np.sqrt(((mix - d) ** 2).sum(1).mean()))
        worst.append((err, name))
        print("MORPH_FIT", name, "max_cm", round(float(np.abs(d).max()), 3),
              "rms_cm", round(err, 3), "bones", len(entry))
        # 拉伸诊断：相邻顶点被不同骨的位移拉开时，薄片几何会被撕成尖刺
        if name in STRETCH_WATCH:
            for e0, e1, mag in _top_stretch(mix, edges, 3):
                print("MORPH_STRETCH", name, e0, _dom(weight, bones, e0), e1, _dom(weight, bones, e1),
                      round(mag, 3))
        # 单骨转角诊断：满形态键时若某根骨转角过大，顶点会被扫出明显的拉伸
        mx, mb = 0.0, "-"
        for bone, local in entry.items():
            a = math.degrees(abs(local.to_quaternion().angle))
            if a > mx:
                mx, mb = a, bone
        print("MORPH_ROT", name, round(mx, 1), mb)
    worst.sort(reverse=True)
    print("MORPH_FIT_WORST", [(n, round(e, 2)) for e, n in worst[:6]])
    return table


def _blend(local, w):
    """把局部增量按权重插值（四元数轴角线性缩放、平移同比）。"""
    if w >= 1.0:
        return local.copy()
    loc, rot, _ = local.decompose()
    q = Quaternion()
    if rot.w < 0.0:
        rot = Quaternion((-rot.w, -rot.x, -rot.y, -rot.z))
    axis = Vector((rot.x, rot.y, rot.z))
    if axis.length > 1e-9:
        q = Quaternion(axis.normalized(), 2.0 * math.acos(min(1.0, rot.w)) * w)
    return Matrix.LocRotScale(loc * w, q, Vector((1.0, 1.0, 1.0)))


def _ramp(frame, lo, hi, total):
    start = lo * total
    end = hi * total
    edge = max(1.0, 0.08 * total)
    if frame <= start or frame > end:
        return 0.0
    t = 1.0
    if frame < start + edge:
        t = (frame - start) / edge
    elif frame > end - edge:
        t = (end - frame) / edge
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def expression_weights(clip, frame, total):
    out = {}
    for preset, (lo, hi) in PRESETS.get(clip, ()):
        w = _ramp(frame, lo, hi, total)
        if w <= 0.0:
            continue
        for morph, base in EXPRESSIONS[preset].items():
            out[morph] = max(out.get(morph, 0.0), base * w)
    return out


def takes_over_brow(clip, frame, total):
    """形态键满强度接管眉毛时，骨驱动的眉高要让位，避免同一根眉骨被叠加两次。"""
    weights = expression_weights(clip, frame, total)
    return any(weights.get(k, 0.0) > 0.0 for k in ("B_Happy", "B_Anger", "B_Sad", "B_Flat"))


def pose(pose_world, rest_all, table, clip, frame, total):
    """在 face_rig.pose_face 之后叠加表情层：P' = P @ rest⁻¹ @ E @ rest。"""
    weights = expression_weights(clip, frame, total)
    if not weights:
        return
    for bone in table["__bones__"]:
        m = Matrix.Identity(4)
        for morph, w in weights.items():
            local = table.get(morph, {}).get(bone)
            if local is None:
                continue
            m = m @ _blend(local, w)
        if m == Matrix.Identity(4):
            continue
        pose_world[bone] = pose_world[bone] @ (rest_all[bone].inverted() @ m @ rest_all[bone])


def diagnose(arm, mesh, captured, table, k, align_deg):
    """把形态键表按 pose() 的合成方式落到网格上，和真实形态键位移比较。

    表里存的是骨局部增量，pose() 写成 P' = P @ rest⁻¹ @ E @ rest，
    顶点实际位移由 LBS 变换 T 决定。这里按「T = E」与「T = rest E rest⁻¹」两种口径
    各算一遍，哪一个贴近真实位移就说明表用的是哪一种坐标系。"""
    bones, weight = _face_weights(mesh)
    p = np.array([v.co[:] for v in mesh.data.vertices], dtype=np.float64)
    rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
    rz = _arr(Matrix.Rotation(math.radians(align_deg), 4, 'Z'))
    names = [m.name for m in mesh.data.materials]
    face_slot = names.index("MI_R2T1JinxiMd10011Face")
    face_verts = set()
    for poly in mesh.data.polygons:
        if poly.material_index == face_slot:
            face_verts.update(poly.vertices)
    face_set = np.zeros(len(p), dtype=bool)
    face_set[np.array(sorted(face_verts), dtype=np.int64)] = True
    fidx = np.flatnonzero(face_set)
    edges = np.array([[e.vertices[0], e.vertices[1]] for e in mesh.data.edges], dtype=np.int64)
    edges = edges[face_set[edges[:, 0]] & face_set[edges[:, 1]]]

    def apply(entry):
        out = np.zeros_like(p)
        for bone in bones:
            m = entry.get(bone)
            if m is None:
                continue
            m3 = np.array([[m[i][j] for j in range(3)] for i in range(3)], dtype=np.float64)
            t3 = np.array([m[i][3] for i in range(3)], dtype=np.float64)
            out += weight[bone][:, None] * ((p @ m3.T) + t3 - p)
        return out

    for preset, morphs in EXPRESSIONS.items():
        d = np.zeros_like(p)
        for morph in morphs:
            delta = captured["deltas"].get(morph)
            if delta is not None:
                d += (rz @ (float(k) * delta).T).T
        direct, conj = {}, {}
        for bone in bones:
            m = Matrix.Identity(4)
            for morph, w in morphs.items():
                local = table.get(morph, {}).get(bone)
                if local is None:
                    continue
                m = m @ _blend(local, w)
            if m == Matrix.Identity(4):
                continue
            direct[bone] = m
            r = rest[bone]
            conj[bone] = r @ m @ r.inverted()
        wsum = np.zeros(len(p), dtype=np.float64)
        for bone in bones:
            wsum += weight[bone]
        moved = np.sqrt((d ** 2).sum(1))
        print("MORPH_GAP", preset,
              "noW02", int(((wsum < 0.02) & (moved > 0.1))[fidx].sum()),
              "noW10", int(((wsum < 0.10) & (moved > 0.1))[fidx].sum()),
              "noW50", int(((wsum < 0.50) & (moved > 0.1))[fidx].sum()),
              "face", int(len(fidx)), "zeroW", int((wsum[fidx] < 0.02).sum()))
        for label, entry in (("direct", direct), ("conj", conj)):
            mix = apply(entry)
            mag = np.sqrt(((mix - d) ** 2).sum(1))
            order = np.argsort(-mag[fidx])[:3]
            top = [(int(fidx[i]), round(float(mag[fidx[i]]), 2),
                    _dom(weight, bones, int(fidx[i])),
                    round(float(wsum[fidx[i]]), 2),
                    [round(float(np.sqrt((d[fidx[i]] ** 2).sum())), 2),
                     round(float(np.sqrt((mix[fidx[i]] ** 2).sum())), 2)],
                    [round(float(p[fidx[i]][1]), 2), round(float(mesh.data.vertices[fidx[i]].normal.y), 2)])
                   for i in order]
            dm = p + mix
            dt = p + d
            el = np.sqrt(((dm[edges[:, 0]] - dm[edges[:, 1]]) ** 2).sum(1))
            tl = np.sqrt(((dt[edges[:, 0]] - dt[edges[:, 1]]) ** 2).sum(1))
            ratio = el / np.maximum(tl, 1e-6)
            print("MORPH_DIAG", preset, label,
                  "mean", round(float(mag[fidx].mean()), 3),
                  "p95", round(float(np.percentile(mag[fidx], 95)), 3),
                  "max", round(float(mag[fidx].max()), 3),
                  "truth", round(float(np.sqrt((d ** 2).sum(1))[fidx].max()), 3),
                  "stretch", round(float(ratio.max()), 2), "top", top)

