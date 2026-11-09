import struct
from pathlib import Path

import numpy as np
from PIL import Image

TEX = Path(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Textures")
ref = TEX / "JINHSI_LEADER_OPACITY_CLOTH.dds"
raw = ref.read_bytes()
header = raw[:128]
mips = struct.unpack_from("<I", header, 28)[0]

src = Image.open(TEX / "MI_6XingStar_BaseColor.dds").convert("RGBA")
alpha = np.asarray(src)[:, :, 3].astype(np.float32)

levels = [alpha.astype(np.uint8)]
cur = alpha
while len(levels) < mips:
    h, w = cur.shape
    nh, nw = max(1, h // 2), max(1, w // 2)
    blk = cur[: nh * 2, : nw * 2].reshape(nh, 2, nw, 2).mean(axis=(1, 3))
    cur = blk
    levels.append(np.clip(cur + 0.5, 0, 255).astype(np.uint8))

body = b"".join(lv.tobytes() for lv in levels)
out = TEX / "MI_6XingStar_Opacity.dds"
out.write_bytes(header + body)
print("WROTE bytes=%d ref_bytes=%d levels=%d delta=%d" % (len(header) + len(body), len(raw), len(levels), len(header) + len(body) - len(raw)))
back = np.frombuffer(out.read_bytes()[128: 128 + 1024 * 1024], dtype=np.uint8).reshape(1024, 1024)
print("VERIFY mean=%.1f frac_lt128=%.4f min=%d max=%d" % (float(back.mean()), float((back < 128).mean()), int(back.min()), int(back.max())))
