import numpy as np

p = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi\Textures\JINHSI_BANGS_OPACITY.dds"
raw = open(p, "rb").read()
print("bytes", len(raw), "magic", raw[:4])
import struct
h = struct.unpack("<7I", raw[4:32])
print("hdr", h)
height, width = struct.unpack("<2I", raw[12:20])
print("w", width, "h", height, "pitch", struct.unpack("<I", raw[20:24]))
off = 128
n = width * height
a = np.frombuffer(raw[off:off + n], dtype=np.uint8).reshape(height, width)
print("mip0 hist opaque", float((a > 127).mean()), "levels", len(np.unique(a)))
t = a <= 127
try:
    from scipy import ndimage
    lab, cnt = ndimage.label(t)
    sizes = ndimage.sum(t, lab, range(1, cnt + 1))
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    holes = sorted([(int(i + 1), int(s)) for i, s in enumerate(sizes) if (i + 1) not in border], key=lambda x: -x[1])
    print("transparent_components", cnt, "enclosed", len(holes), "top", holes[:6])
    if holes:
        big = holes[0][0]
        ys, xs = np.where(lab == big)
        print("hole_bbox", xs.min(), xs.max(), ys.min(), ys.max())
except ImportError as exc:
    print("no scipy", exc)
