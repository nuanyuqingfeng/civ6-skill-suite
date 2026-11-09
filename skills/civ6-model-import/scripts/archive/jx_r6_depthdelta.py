import bpy
import os
import json
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi"
MODEL = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
TEXDIR = os.path.join(ROOT, "Jinzhou_Jinhsi", "Textures")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images):
    for item in list(block):
        block.remove(item, do_unlink=True)
bpy.ops.import_scene.psk(filepath=MODEL)
body = [o for o in bpy.data.objects if o.type == 'MESH' and len(o.data.vertices) > 100][0]
me = body.data
me.calc_loop_triangles()
mw = body.matrix_world
nmat = mw.to_3x3().inverted().transposed()
V = np.array([list(mw @ v.co) for v in me.vertices], dtype=np.float64)
T = np.array([list(t.vertices) for t in me.loop_triangles], dtype=np.int32)
PMAT = np.array([t.material_index for t in me.loop_triangles], dtype=np.int32)
TN = np.array([list((nmat @ me.polygons[t.polygon_index].normal).normalized()) for t in me.loop_triangles], dtype=np.float64)
SLOT = [s.material.name if s.material else "-" for s in body.material_slots]
poly_uv = np.zeros((len(me.polygons), 2), dtype=np.float64)
uvl = me.uv_layers.active.data
for p in me.polygons:
    acc = np.zeros(2)
    for li in range(p.loop_start, p.loop_start + p.loop_total):
        acc += np.array(uvl[li].uv[:])
    poly_uv[p.index] = acc / p.loop_total
TRI_UV = poly_uv[[t.polygon_index for t in me.loop_triangles]]

def load_img(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    arr = buf.reshape(h, w, 4).copy()
    bpy.data.images.remove(img)
    return arr

def sample(arr, uv):
    h, w, _ = arr.shape
    u = float(min(max(uv[0], 0.0), 0.999999))
    v = float(min(max(uv[1], 0.0), 0.999999))
    return arr[int(v * h), int(u * w)]

tex_down = load_img(os.path.join(TEXDIR, "MI_R2T1JinxiMd10011Down_BaseColor.dds"))
tex_skirt = load_img(os.path.join(TEXDIR, "MI_R2T1JinxiMd10011Skirt_BaseColor.dds"))
poly_col = np.ones((len(me.polygons), 4), dtype=np.float64)
for p in me.polygons:
    name = SLOT[p.material_index]
    if "Down" in name:
        poly_col[p.index] = sample(tex_down, poly_uv[p.index])
    elif "Skirt" in name:
        poly_col[p.index] = sample(tex_skirt, poly_uv[p.index])
TRI_COL = poly_col[[t.polygon_index for t in me.loop_triangles]]
TRI_LUM = 0.2126 * TRI_COL[:, 0] + 0.7152 * TRI_COL[:, 1] + 0.0722 * TRI_COL[:, 2]
GARMENT = (PMAT == 3) | (PMAT == 4)
bvh = BVHTree.FromPolygons([Vector(v) for v in V], [tuple(int(x) for x in tri) for tri in T], all_triangles=True)

def trace(origin, direction, max_layers=8):
    hits = []
    t = 0.0
    for _ in range(max_layers):
        loc, nrm, tri_i, dist = bvh.ray_cast(Vector(origin) + Vector(direction) * t, Vector(direction))
        if loc is None:
            break
        hits.append((t + dist, int(tri_i)))
        t = t + dist + 0.02
    return hits

def band(zlo, zhi):
    deltas = []
    black_front = 0
    both = 0
    cells = 0
    for z in np.arange(zlo, zhi + 0.01, 0.5):
        for x in np.arange(-8.0, 8.01, 0.5):
            cells += 1
            hits = trace((float(x), -80.0, float(z)), (0.0, 1.0, 0.0))
            yl = None
            yb = None
            for dist, ti in hits:
                if not GARMENT[ti] or TN[ti][1] <= 0.0:
                    continue
                y = float(V[T[ti]][:, 1].mean())
                if TRI_LUM[ti] >= 0.5 and yl is None:
                    yl = y
                if TRI_LUM[ti] < 0.25 and yb is None:
                    yb = y
                if yl is not None and yb is not None:
                    break
            if yl is not None and yb is not None:
                both += 1
                d = yl - yb
                deltas.append(round(float(d), 3))
                if d > 0.0:
                    black_front += 1
    d = np.array(deltas)
    print("BAND", zlo, zhi, "cells", cells, "both", both,
          "black_front_frac", round(black_front / both, 3) if both else None,
          "delta_median", round(float(np.median(d)), 3) if both else None,
          "frac_abs_lt_0.25", round(float((np.abs(d) < 0.25).mean()), 3) if both else None,
          "frac_abs_lt_0.5", round(float((np.abs(d) < 0.5).mean()), 3) if both else None,
          "frac_abs_lt_1", round(float((np.abs(d) < 1.0).mean()), 3) if both else None)

band(95.0, 105.0)
band(105.0, 115.0)
band(115.0, 125.0)
print("DELTA_OK")
