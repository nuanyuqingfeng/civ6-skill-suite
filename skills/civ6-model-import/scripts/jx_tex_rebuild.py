import struct
import numpy as np
from PIL import Image
from scipy import ndimage

TEX = r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Textures/"

def read_dds(path):
    with open(path, "rb") as f:
        raw = f.read()
    hdr = raw[:128]
    h, w = struct.unpack("<2I", hdr[12:20])
    mips = struct.unpack("<I", hdr[28:32])[0]
    return hdr, w, h, mips, raw[128:]

def level_bytes(w, h, bpp):
    return (w * h * bpp + 7) // 8

def read_level0(path):
    hdr, w, h, mips, body = read_dds(path)
    pf_flags = struct.unpack("<I", hdr[80:84])[0]
    bits = struct.unpack("<I", hdr[88:92])[0]
    bpp = bits // 8
    n = level_bytes(w, h, bits)
    data = np.frombuffer(body[:n], dtype=np.uint8).reshape(h, w, bpp)
    return hdr, w, h, mips, bpp, data

def box_down(a):
    h, w, c = a.shape
    if h % 2 or w % 2:
        a = np.pad(a, ((0, h % 2), (0, w % 2), (0, 0)), mode="edge")
        h, w, c = a.shape
    return a.reshape(h // 2, 2, w // 2, 2, c).mean(axis=(1, 3)).round().astype(np.uint8)

def write_dds(path, hdr, w, h, bpp, level0):
    mips = 1
    tw, th = w, h
    while tw > 1 or th > 1:
        tw = max(1, tw // 2)
        th = max(1, th // 2)
        mips += 1
    head = bytearray(hdr)
    struct.pack_into("<2I", head, 12, h, w)
    struct.pack_into("<I", head, 28, mips)
    if bpp == 4:
        struct.pack_into("<I", head, 20, w * 4)
    out = [bytes(head)]
    cur = level0
    for _ in range(mips):
        out.append(cur.tobytes())
        if cur.shape[0] == 1 and cur.shape[1] == 1:
            break
        cur = box_down(cur)
    with open(path, "wb") as f:
        f.write(b"".join(out))
    return mips

hdr_bc, w, h, mips, bpp, bc = read_level0(TEX + "MI_R2T1JinxiMd10011Bangs_BaseColor.dds")
print("BASECOLOR", w, h, bpp, "mips", mips)

hdr_op, wo, ho, mo, bo, op = read_level0(TEX + "MI_R2T1JinxiMd10011Bangs_Opacity.dds")
print("BANGS_OPACITY", wo, ho, bo)

hdr_is, wi, hi, mi, bi, isl = read_level0(TEX + "JINHSI_BANGS_OPACITY.dds")
print("ISLAND", wi, hi, bi, "white_frac", round(float((isl[:, :, 0] > 127).mean()), 4))

op_img = Image.fromarray(op[:, :, 0]).resize((w, h), Image.BILINEAR)
kept = np.asarray(op_img) > 127
island = isl[:, :, 0] > 127
print("KEPT_FRAC", round(float(kept.mean()), 4), "ISLAND_FRAC", round(float(island.mean()), 4))
print("ISLAND_NOT_KEPT", int((island & ~kept).sum()))

fill = ~kept
src = bc[:, :, :3].astype(np.float32)
idx = ndimage.distance_transform_edt(~kept, return_distances=False, return_indices=True)
filled = src[tuple(idx)]
out = bc.copy()
out[fill, :3] = filled[fill].round().astype(np.uint8)
out[fill, 3] = 255
def lum_map(a):
    f = a.astype(np.float32)
    return (f[:, :, 0] * 299 + f[:, :, 1] * 587 + f[:, :, 2] * 114) / 1000.0

lum_before = lum_map(bc[:, :, :3])
lum_after = lum_map(out[:, :, :3])
print("LUM_BEFORE_FILLED", round(float(lum_before[fill].mean()) if fill.any() else 0.0, 3))
print("LUM_AFTER_FILLED", round(float(lum_after[fill].mean()), 3))
print("LUM_KEPT", round(float(lum_before[kept].mean()), 3))
m = write_dds(TEX + "JINHSI_BANGS_BASECOLOR.dds", hdr_bc, w, h, 4, out)
print("WROTE_BASECOLOR mips", m)

hdr_sk, ws, hs, ms, bs, sk = read_level0(TEX + "MI_R2T1JinxiMd10011Skirt_Opacity.dds")
print("SKIRT_SRC", ws, hs, bs, "uniq", len(np.unique(sk[:, :, 0])))
soft = np.asarray(Image.fromarray(sk[:, :, 0]).resize((wi, hi), Image.BILINEAR))
cover = ndimage.binary_dilation(soft > 0, iterations=2)
alpha = np.where(cover, 255, 0).astype(np.uint8)
uniq = len(np.unique(alpha))
mid = int(((alpha > 8) & (alpha < 247)).sum())
full = int((alpha == 255).sum())
print("CLOTH_SOFT cover_frac", round(float(cover.mean()), 4),
      "full_frac", round(full / float(alpha.size), 4),
      "uniq", uniq, "mid_frac", round(mid / float(alpha.size), 4))
cloth = alpha.reshape(hi, wi, 1)
m2 = write_dds(TEX + "JINHSI_LEADER_OPACITY_CLOTH.dds", hdr_is, wi, hi, 1, cloth)
print("WROTE_CLOTH mips", m2, "shape", cloth.shape)
print("TEX_REBUILD_DONE")