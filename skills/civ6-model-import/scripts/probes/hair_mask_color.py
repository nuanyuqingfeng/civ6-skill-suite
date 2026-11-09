import argparse
from PIL import Image, ImageDraw, ImageFilter

parser = argparse.ArgumentParser()
parser.add_argument("--tsv", required=True, help="dump_hair_uv.py 的产物")
parser.add_argument("--src", required=True, help="源漫反射 PNG")
parser.add_argument("--out", required=True, help="输出贴图 PNG")
parser.add_argument("--preview", required=True, help="掩膜预览 PNG")
parser.add_argument("--size", type=int, default=2048, help="掩膜边长，必须与出图 TARGET_SIZE 一致；默认随源图 2048²")
parser.add_argument("--replace-group", action="append", default=[],
                    help="组名:阈值 —— 该组按阈值替换成基色，如 head:195")
parser.add_argument("--curve-group", action="append", default=[],
                    help="组名:均值:系数 —— 该组走平滑压缩曲线，如 side:208:0.22")
parser.add_argument("--base", default="205,208,212")
parser.add_argument("--feather", type=int, default=5)
args = parser.parse_args()

N = args.size
BASE = [float(v) for v in args.base.split(",")]
BASE_L = 0.2126 * BASE[0] + 0.7152 * BASE[1] + 0.0722 * BASE[2]
replace = {}
for spec in args.replace_group:
    g, t = spec.split(":")
    replace[g] = float(t)
curve = {}
for spec in args.curve_group:
    g, m, k = spec.split(":")
    curve[g] = (float(m), float(k))

masks = {}
with open(args.tsv, encoding="utf-8") as fh:
    for line in fh:
        f = line.rstrip("\n").split("\t")
        if len(f) != 7:
            continue
        buf = masks.setdefault(f[0], bytearray(N * N))
        u1, v1, u2, v2, u3, v3 = [float(v) for v in f[1:]]
        xs = [u1 * N, u2 * N, u3 * N]
        ys = [(1 - v) * N for v in (v1, v2, v3)]
        x0, x1 = max(0, int(min(xs))), min(N - 1, int(max(xs)) + 1)
        y0, y1 = max(0, int(min(ys))), min(N - 1, int(max(ys)) + 1)
        d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(d) < 1e-9:
            continue
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                a = ((ys[1] - ys[2]) * (x - xs[2]) + (xs[2] - xs[1]) * (y - ys[2])) / d
                b = ((ys[2] - ys[0]) * (x - xs[2]) + (xs[0] - xs[2]) * (y - ys[2])) / d
                c = 1 - a - b
                if a >= -0.001 and b >= -0.001 and c >= -0.001:
                    buf[y * N + x] = 255

im = Image.open(args.src).convert("RGB").resize((N, N), Image.LANCZOS)
gray = im.convert("L")
alphas = {}
for g, buf in masks.items():
    if g in replace:
        dark = gray.point(lambda v, t=replace[g]: 255 if v < t else 0)
        inter = bytes(a & b for a, b in zip(buf, dark.tobytes()))
        alphas[g] = Image.frombytes("L", (N, N), inter).filter(ImageFilter.GaussianBlur(args.feather))
    else:
        alphas[g] = Image.frombytes("L", (N, N), bytes(buf)).filter(ImageFilter.GaussianBlur(args.feather + 2))

px = im.load()
touched = 0
for y in range(N):
    for x in range(N):
        p = px[x, y]
        best = 0.0
        target = None
        for g, layer in alphas.items():
            a = layer.load()[x, y] / 255.0
            if a <= best:
                continue
            best = a
            if g in curve:
                m, k = curve[g]
                L = 0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]
                scale = (m + k * (L - m)) / BASE_L
                target = (BASE[0] * scale, BASE[1] * scale, BASE[2] * scale)
            else:
                target = tuple(BASE)
        if target is None or best == 0.0:
            continue
        px[x, y] = (min(255, int(round(p[0] + (target[0] - p[0]) * best))),
                    min(255, int(round(p[1] + (target[1] - p[1]) * best))),
                    min(255, int(round(p[2] + (target[2] - p[2]) * best))))
        touched += 1

im.save(args.out)
overlay = Image.new("L", (N, N))
for layer in alphas.values():
    overlay = Image.composite(Image.new("L", (N, N), 255), overlay, layer.point(lambda v: 255 if v > 40 else 0))
source = Image.open(args.src).convert("RGB").resize((N, N), Image.LANCZOS)
source.paste((255, 0, 128), mask=overlay)
draw = ImageDraw.Draw(source)
draw.text((8, 8), args.preview, fill=(0, 0, 0))
source.save(args.preview)

def stats(img):
    g = img.convert("L")
    vals = list(g.getdata())
    n = len(vals)
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / n
    return round(min(vals), 1), round(mean, 1), round(var ** 0.5, 1), round(sum(1 for v in vals if v < 128) / n, 4), round(sum(1 for v in vals if v < 175) / n, 4)

print("TOUCHED", touched, round(touched / (N * N), 4))
print("BEFORE", stats(Image.open(args.src).convert("RGB").resize((N, N), Image.LANCZOS)))
print("AFTER", stats(im))
print("PREVIEW", args.preview)
