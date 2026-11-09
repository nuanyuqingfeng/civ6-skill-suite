import argparse
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

LEVEL = 0.5


def find_group(mesh, star_name):
    for slot in mesh.material_slots:
        if slot.material and star_name in slot.material.name:
            return slot.slot_index
    raise SystemExit("找不到材质槽：%s" % star_name)


def gather(mesh, star):
    uvl = mesh.data.uv_layers.active.data
    gname = {g.index: g.name for g in mesh.vertex_groups}
    rows = []
    for poly in mesh.data.polygons:
        if poly.material_index != star:
            continue
        for li in poly.loop_indices:
            vi = mesh.data.loops[li].vertex_index
            u, v = uvl[li].uv
            weights = {gname[ge.group]: ge.weight for ge in mesh.data.vertices[vi].groups}
            rows.append((u, v, weights, mesh.matrix_world @ mesh.data.vertices[vi].co))
    if not rows:
        raise SystemExit("该材质槽没有任何面")
    return rows


def fit_plane(rows):
    a = np.array([[r[3].x, r[3].y, r[3].z] for r in rows])
    u = np.array([[r[0], r[1]] for r in rows])
    m = np.column_stack([np.ones(len(u)), u])
    coef, *_ = np.linalg.lstsq(m, a, rcond=None)
    resid = float(np.abs(m @ coef - a).max())
    return coef, resid


def patch_normal(mesh, star, center):
    nsum = Vector((0.0, 0.0, 0.0))
    for poly in mesh.data.polygons:
        if poly.material_index == star:
            nsum += mesh.matrix_world.to_3x3() @ poly.normal
    n = nsum.normalized()
    body = sum((mesh.matrix_world @ v.co for v in mesh.data.vertices), Vector((0.0, 0.0, 0.0)))
    body = body / len(mesh.data.vertices)
    if n.dot(center - body) < 0:
        n = -n
    return n


def clearance(mesh, star, reach=3.0):
    mwi = mesh.matrix_world.inverted()
    dist = []
    for poly in mesh.data.polygons:
        if poly.material_index != star:
            continue
        pc = mesh.matrix_world @ poly.center
        pn = (mesh.matrix_world.to_3x3() @ poly.normal).normalized()
        step = (mwi.to_3x3() @ (-pn)).normalized()
        start = mwi @ (pc + pn * reach)
        for _ in range(16):
            ok, loc, _n, idx = mesh.ray_cast(start, step)
            if not ok:
                break
            if mesh.data.polygons[idx].material_index == star:
                start = loc + step * 0.01
                continue
            dist.append(((mesh.matrix_world @ loc) - pc).length)
            break
    dist.sort()
    return dist


def main():
    parser = argparse.ArgumentParser(
        description="把贴在某块曲面上的面片按蒙版轮廓重建成三角网，新顶点继承原面片权重。")
    parser.add_argument("--blend", required=True)
    parser.add_argument("--material", required=True, help="材质名片段，如 3XingStar")
    parser.add_argument("--mask", required=True, help="蒙版图，取 alpha 通道切轮廓")
    parser.add_argument("--res", type=int, default=160, help="栅格分辨率，默认 160")
    parser.add_argument("--outward", type=float, default=0.0015,
                        help="沿法线朝外偏移，单位与网格一致；米制网格取 0.0015 即 1.5 毫米")
    parser.add_argument("--tol", type=float, default=2.0, help="质心漂移上限，单位与网格一致")
    parser.add_argument("--json")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)

    bpy.ops.wm.open_mainfile(filepath=args.blend)
    mesh = [o for o in bpy.data.objects if o.type == "MESH"][0]
    bpy.context.view_layer.update()

    star = find_group(mesh, args.material)
    rows = gather(mesh, star)
    coef, resid = fit_plane(rows)
    print("FIT_RESID %.4f" % resid)

    old_c = sum((r[3] for r in rows), Vector((0.0, 0.0, 0.0))) / len(rows)
    normal = patch_normal(mesh, star, old_c)

    img = bpy.data.images.load(args.mask, check_existing=True)
    mw, mh = img.size
    alpha = np.array(img.pixels[:]).reshape(mh, mw, 4)[:, :, 3]

    u = np.array([[r[0], r[1]] for r in rows])
    u0, u1 = float(u[:, 0].min()), float(u[:, 0].max())
    v0, v1 = float(u[:, 1].min()), float(u[:, 1].max())

    def inside(cu, cv):
        x = int(min(max(cu * mw, 0), mw - 1))
        y = int(min(max(cv * mh, 0), mh - 1))
        return alpha[y, x] > LEVEL

    def pos(cu, cv):
        p = coef[0] + coef[1] * cu + coef[2] * cv
        return Vector((p[0], p[1], p[2])) + normal * args.outward

    def weights_at(cu, cv):
        best = None
        best_d = None
        for ru, rv, w, _p in rows:
            d = (ru - cu) ** 2 + (rv - cv) ** 2
            if best_d is None or d < best_d:
                best_d, best = d, w
        return best

    du = (u1 - u0) / args.res
    dv = (v1 - v0) / args.res
    cells = []
    cache = {}
    for j in range(args.res):
        for i in range(args.res):
            ua = u0 + i * du
            vb = v0 + j * dv
            ub = ua + du
            vc = vb + dv
            if not inside((ua + ub) * 0.5, (vb + vc) * 0.5):
                continue
            corners = [(ua, vb), (ub, vb), (ub, vc), (ua, vc)]
            pts = []
            for cu, cv in corners:
                key = (round(cu, 6), round(cv, 6))
                if key not in cache:
                    cache[key] = pos(cu, cv)
                pts.append(cache[key])
            cells.append((corners, pts))
    print("CELLS %d CORNERS %d" % (len(cells), len(cache)))
    if not cells:
        raise SystemExit("蒙版在该 UV 区间内没有任何采样点")

    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    uvlay = bm.loops.layers.uv.verify()
    doomed = [f for f in bm.faces if f.material_index == star]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")

    inv = mesh.matrix_world.inverted()
    new_uv = {}
    made = 0
    for corners, pts in cells:
        vs = []
        for p, (cu, cv) in zip(pts, corners):
            vert = bm.verts.new(inv @ p)
            new_uv[vert] = (cu, cv)
            vs.append(vert)
        face = bm.faces.new(vs)
        face.material_index = star
        if face.normal.dot(normal) < 0:
            face.normal_flip()
        for loop, (cu, cv) in zip(face.loops, corners):
            loop[uvlay].uv = (cu, cv)
        made += 1

    bm.verts.index_update()
    pairs = [(v.index, new_uv[v]) for v in bm.verts if v in new_uv]
    bm.to_mesh(mesh.data)
    bm.free()
    mesh.data.update()

    inherited = 0
    for vi, (cu, cv) in pairs:
        w = weights_at(cu, cv)
        if not w:
            continue
        inherited += 1
        for bone, weight in w.items():
            if weight <= 0.0:
                continue
            mesh.vertex_groups[bone].add([vi], weight, 'REPLACE')
    print("WEIGHTS_INHERITED %d/%d" % (inherited, len(pairs)))

    pts = [mesh.matrix_world @ mesh.data.vertices[v].co
           for poly in mesh.data.polygons if poly.material_index == star
           for v in poly.vertices]
    new_c = sum(pts, Vector((0.0, 0.0, 0.0))) / len(pts)
    drift = (new_c - old_c).length
    print("FACES %d DRIFT %.4f OUTWARD %.4f" % (made, drift, args.outward))

    dist = clearance(mesh, star)
    if dist:
        print("CLEARANCE n=%d min=%.4f med=%.4f" % (len(dist), dist[0], dist[len(dist) // 2]))
    else:
        print("CLEARANCE n=0")

    ok = drift < args.tol and inherited == len(pairs)
    if args.json:
        import json
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"faces": made, "fit_resid": resid, "drift": drift,
                       "clearance_min": dist[0] if dist else None,
                       "weights_inherited": inherited, "corners": len(pairs), "ok": ok},
                      fh, ensure_ascii=False, indent=1)
        print("JSON %s" % args.json)
    print("PATCH_SHAPE_REBUILD_%s" % ("OK" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
