import hashlib
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi")
TEX = ROOT / "Jinzhou_Jinhsi" / "Textures"
OUT_JSON = ROOT / "workspace" / "tmp" / "alpha_verify.json"

OPACITY = [
    "JINHSI_LEADER_OPACITY_CLOTH.dds",
    "JINHSI_BANGS_OPACITY.dds",
    "MI_R2T1JinxiMd10011Hair_Opacity.dds",
    "MI_R2T1JinxiMd10011Skirt_Opacity.dds",
    "MI_R2T1JinxiMd10011Bangs_Opacity.dds",
]
BASECOLOR = [
    "JINHSI_BANGS_BASECOLOR.dds",
    "MI_R2T1JinxiMd10011Hair_BaseColor.dds",
]


def read_chain(path):
    raw = path.read_bytes()
    w = struct.unpack_from("<I", raw, 16)[0]
    h = struct.unpack_from("<I", raw, 12)[0]
    mips = struct.unpack_from("<I", raw, 28)[0]
    bits = struct.unpack_from("<I", raw, 88)[0] // 8
    off = 128
    out = []
    cw, ch = w, h
    for _ in range(mips):
        n = cw * ch * bits
        a = np.frombuffer(raw[off:off + n], dtype=np.uint8)
        out.append(a.reshape(ch, cw) if bits == 1 else a.reshape(ch, cw, bits))
        off += n
        cw = max(1, cw // 2)
        ch = max(1, ch // 2)
    return w, h, mips, bits, out, len(raw) - off


result = {"opacity": {}, "basecolor": {}}
for name in OPACITY:
    path = TEX / name
    w, h, mips, bits, chain, tail = read_chain(path)
    pil_r = np.asarray(Image.open(path))[:, :, 0]
    if pil_r.shape != chain[0].shape or not np.array_equal(pil_r, chain[0]):
        raise ValueError("PIL channel R and struct decode disagree for " + name)
    per_mip = []
    for m in chain:
        n = m.size
        per_mip.append({
            "size": int(m.shape[1]),
            "frac_full": round(float((m == 255).sum()) / n, 6),
            "frac_zero": round(float((m == 0).sum()) / n, 6),
            "frac_mid": round(float(((m > 0) & (m < 255)).sum()) / n, 6),
            "gray_levels": int(len(np.unique(m))),
            "mean": round(float(m.mean()), 4),
        })
    result["opacity"][name] = {
        "width": w,
        "height": h,
        "mips": mips,
        "bits": bits,
        "bytes": path.stat().st_size,
        "trailing_bytes": tail,
        "sha256_16": hashlib.sha256(path.read_bytes()).hexdigest()[:16],
        "level0": per_mip[0],
        "mips_stats": per_mip,
        "mip_mid_all_zero": all(x["frac_mid"] == 0.0 for x in per_mip),
    }

for name in BASECOLOR:
    path = TEX / name
    w, h, mips, bits, chain, tail = read_chain(path)
    a = np.asarray(Image.open(path).convert("RGBA"))
    if not np.array_equal(a, chain[0]):
        raise ValueError("PIL RGBA and struct decode disagree for " + name)
    rgb = a[:, :, :3].astype(np.int32)
    lum = (rgb[:, :, 0] * 299 + rgb[:, :, 1] * 587 + rgb[:, :, 2] * 114) // 1000
    dark = ((rgb[:, :, 0] < 30) & (rgb[:, :, 1] < 30) & (rgb[:, :, 2] < 30))
    al = a[:, :, 3]
    result["basecolor"][name] = {
        "width": w,
        "height": h,
        "mips": mips,
        "bytes": path.stat().st_size,
        "sha256_16": hashlib.sha256(path.read_bytes()).hexdigest()[:16],
        "near_black": int(dark.sum()),
        "near_black_frac": round(float(dark.mean()), 6),
        "lum_mean": round(float(lum.mean()), 3),
        "lum_min": int(lum.min()),
        "gray_levels_lum": int(len(np.unique(lum))),
        "alpha_mean": round(float(al.mean()), 3),
        "alpha_min": int(al.min()),
        "alpha_max": int(al.max()),
        "alpha_below_255": int((al < 255).sum()),
        "alpha_zero": int((al == 0).sum()),
    }

OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

for name, e in result["opacity"].items():
    l0 = e["level0"]
    print(name, str(e["width"]) + "x" + str(e["height"]), "mips", e["mips"], "bits", e["bits"],
          "bytes", e["bytes"], "sha", e["sha256_16"])
    print("   L0 full", l0["frac_full"], "zero", l0["frac_zero"], "mid", l0["frac_mid"],
          "gray_levels", l0["gray_levels"], "| mip_mid_all_zero", e["mip_mid_all_zero"])
for name, e in result["basecolor"].items():
    print(name, str(e["width"]) + "x" + str(e["height"]), "mips", e["mips"], "bytes", e["bytes"], "sha", e["sha256_16"])
    print("   near_black", e["near_black"], e["near_black_frac"], "lum_mean", e["lum_mean"],
          "gray_levels", e["gray_levels_lum"], "| alpha mean", e["alpha_mean"], "min", e["alpha_min"],
          "below255", e["alpha_below_255"], "zero", e["alpha_zero"])
print("WROTE", OUT_JSON)
