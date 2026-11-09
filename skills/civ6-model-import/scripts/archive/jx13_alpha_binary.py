import hashlib
import shutil
import struct
from pathlib import Path

import numpy as np

ROOT = Path(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi")
TEX = ROOT / "Jinzhou_Jinhsi" / "Textures"
BACKUP = ROOT / "workspace" / "tmp" / "before_binary"
TARGETS = [
    "JINHSI_LEADER_OPACITY_CLOTH.dds",
    "JINHSI_BANGS_OPACITY.dds",
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(path):
    raw = path.read_bytes()
    if raw[0:4] != b"DDS ":
        raise ValueError("not DDS: " + path.name)
    h = struct.unpack_from("<I", raw, 12)[0]
    w = struct.unpack_from("<I", raw, 16)[0]
    mips = struct.unpack_from("<I", raw, 28)[0]
    bits = struct.unpack_from("<I", raw, 88)[0]
    if bits != 8:
        raise ValueError("expected 8 bpp, got " + str(bits) + " in " + path.name)
    if raw[84:88] == b"DX10":
        raise ValueError("unexpected DX10 header in " + path.name)
    levels = []
    off = 128
    cw, ch = w, h
    for _ in range(mips):
        n = cw * ch
        levels.append(np.frombuffer(raw[off:off + n], dtype=np.uint8).reshape(ch, cw).copy())
        off += n
        cw = max(1, cw // 2)
        ch = max(1, ch // 2)
    if off != len(raw):
        raise ValueError("size mismatch in " + path.name + ": " + str(off) + " vs " + str(len(raw)))
    return raw[:128], w, h, mips, levels


def binary_mips(level0):
    out = [level0.copy().astype(np.uint8)]
    cur = out[0]
    while cur.shape[0] > 1 or cur.shape[1] > 1:
        h, w = cur.shape
        if h % 2 or w % 2:
            cur = np.pad(cur, ((0, h % 2), (0, w % 2)), mode="edge")
            h, w = cur.shape
        blocks = cur.reshape(h // 2, 2, w // 2, 2).astype(np.uint16).sum(axis=(1, 3))
        cur = np.where(blocks >= 510, 255, 0).astype(np.uint8)
        out.append(cur)
    return out


BACKUP.mkdir(parents=True, exist_ok=True)
for name in TARGETS:
    path = TEX / name
    src_sha = sha256(path)
    shutil.copy2(path, BACKUP / name)
    hdr, w, h, mips, levels = decode(path)
    l0 = levels[0]
    uniq = np.unique(l0)
    if not set(uniq.tolist()) <= {0, 255}:
        raise ValueError("level0 is not binary in " + name + ": " + str(uniq[:8].tolist()))
    rebuilt = binary_mips(l0)
    if len(rebuilt) != mips:
        raise ValueError("mip count changed in " + name + ": " + str(len(rebuilt)) + " vs " + str(mips))
    for i, (old, new) in enumerate(zip(levels, rebuilt)):
        if i == 0:
            if not np.array_equal(old, new):
                raise ValueError("level0 changed in " + name)
        else:
            if not np.array_equal(np.unique(new).tolist(), np.union1d(np.unique(new), np.unique(old)).tolist()):
                pass
    body = b"".join(lv.tobytes() for lv in rebuilt)
    path.write_bytes(hdr + body)
    new_sha = sha256(path)
    if path.stat().st_size != len(hdr) + len(body):
        raise ValueError("write size mismatch in " + name)
    old_mid = [round(float((((m > 0) & (m < 255)).sum()) / m.size), 6) for m in levels]
    new_mid = [round(float((((m > 0) & (m < 255)).sum()) / m.size), 6) for m in rebuilt]
    print(name, str(w) + "x" + str(h), "mips", mips, "level0 uniq", len(uniq))
    print("   sha256", src_sha[:16], "->", new_sha[:16], "size", path.stat().st_size)
    print("   mip_mid before", old_mid)
    print("   mip_mid after ", new_mid)
print("BINARY_REBUILD_DONE")
