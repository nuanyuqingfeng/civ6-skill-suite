import json
import struct
from pathlib import Path

import numpy as np

ROOT = Path(r"D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi")
TEX = ROOT / "Jinzhou_Jinhsi" / "Textures"
OUT = ROOT / "workspace" / "tmp" / "alpha_hist.json"

OPACITY = [
    "MI_R2T1JinxiMd10011Hair_Opacity.dds",
    "MI_R2T1JinxiMd10011Skirt_Opacity.dds",
    "MI_R2T1JinxiMd10011Bangs_Opacity.dds",
    "JINHSI_LEADER_OPACITY_CLOTH.dds",
    "JINHSI_BANGS_OPACITY.dds",
]
BASECOLOR = [
    "JINHSI_BANGS_BASECOLOR.dds",
    "MI_R2T1JinxiMd10011Hair_BaseColor.dds",
]


def decode(path):
    raw = path.read_bytes()
    if raw[0:4] != b"DDS ":
        raise ValueError("not DDS: " + str(path))
    h = struct.unpack_from("<I", raw, 12)[0]
    w = struct.unpack_from("<I", raw, 16)[0]
    mips = struct.unpack_from("<I", raw, 28)[0]
    pf_flags = struct.unpack_from("<I", raw, 80)[0]
    fourcc = raw[84:88]
    bits = struct.unpack_from("<I", raw, 88)[0]
    dx10 = 0
    off = 128
    if fourcc == b"DX10":
        dx10 = struct.unpack_from("<I", raw, 128)[0]
        off = 148
    bytes_per_px = bits // 8
    levels = []
    cw, ch = w, h
    for _ in range(mips):
        n = cw * ch * bytes_per_px
        arr = np.frombuffer(raw[off:off + n], dtype=np.uint8)
        if bytes_per_px == 1:
            arr = arr.reshape(ch, cw)
        else:
            arr = arr.reshape(ch, cw, bytes_per_px)
        levels.append(arr)
        off += n
        cw = max(1, cw // 2)
        ch = max(1, ch // 2)
    return {
        "file": path.name,
        "width": w,
        "height": h,
        "mips": mips,
        "pf_flags": pf_flags,
        "fourcc": fourcc.decode("latin1"),
        "dxgi": dx10,
        "bits": bits,
        "bytes": len(raw),
        "bytes_after_header": off - 128,
        "trailing_bytes": len(raw) - off,
        "levels": levels,
    }


def gray_stats(a):
    v = a.astype(np.uint8)
    n = v.size
    vals, counts = np.unique(v, return_counts=True)
    top = sorted(zip(counts.tolist(), vals.tolist()), reverse=True)[:6]
    mid = int(((v > 0) & (v < 255)).sum())
    return {
        "pixels": n,
        "mean": round(float(v.mean()), 4),
        "min": int(v.min()),
        "max": int(v.max()),
        "unique": int(len(vals)),
        "frac_zero": round(float((v == 0).sum()) / n, 6),
        "frac_full": round(float((v == 255).sum()) / n, 6),
        "frac_mid": round(float(mid) / n, 6),
        "mid_count": mid,
        "top_values": [[int(val), int(cnt), round(cnt / n, 6)] for cnt, val in top],
    }


def rgb_stats(a):
    rgb = a[:, :, :3].astype(np.int32)
    lum = (rgb[:, :, 0] * 299 + rgb[:, :, 1] * 587 + rgb[:, :, 2] * 114) / 1000.0
    dark = (rgb[:, :, 0] < 30) & (rgb[:, :, 1] < 30) & (rgb[:, :, 2] < 30)
    n = lum.size
    ys, xs = np.nonzero(dark)
    al = a[:, :, 3]
    return {
        "pixels": n,
        "lum_mean": round(float(lum.mean()), 4),
        "lum_p1": round(float(np.percentile(lum, 1)), 4),
        "lum_min": round(float(lum.min()), 4),
        "lum_max": round(float(lum.max()), 4),
        "near_black_count": int(dark.sum()),
        "near_black_frac": round(float(dark.sum()) / n, 8),
        "near_black_bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if dark.any() else None,
        "alpha_mean": round(float(al.mean()), 4),
        "alpha_min": int(al.min()),
        "alpha_unique": int(len(np.unique(al))),
        "alpha_below_255": int((al < 255).sum()),
    }


report = {"opacity": {}, "basecolor": {}}
for name in OPACITY:
    d = decode(TEX / name)
    lv = d.pop("levels")
    d["level0"] = gray_stats(lv[0])
    d["mips_stats"] = [gray_stats(m) for m in lv]
    report["opacity"][name] = d

for name in BASECOLOR:
    d = decode(TEX / name)
    lv = d.pop("levels")
    d["level0"] = rgb_stats(lv[0])
    report["basecolor"][name] = d

OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

for name, e in report["opacity"].items():
    s = e["level0"]
    mids = [m["frac_mid"] for m in e["mips_stats"]]
    print(name, str(e["width"]) + "x" + str(e["height"]), "mips", e["mips"], "bits", e["bits"],
          "| mean", s["mean"], "uniq", s["unique"], "min", s["min"], "max", s["max"],
          "| zero", s["frac_zero"], "full", s["frac_full"], "mid", s["frac_mid"])
    print("   mip_mid", [round(x, 4) for x in mids], "| mip_full", [round(m["frac_full"], 4) for m in e["mips_stats"]])
for name, e in report["basecolor"].items():
    s = e["level0"]
    print(name, str(e["width"]) + "x" + str(e["height"]), "bits", e["bits"], "| lum_mean", s["lum_mean"],
          "p1", s["lum_p1"], "min", s["lum_min"], "max", s["lum_max"],
          "| near_black", s["near_black_count"], "bbox", s["near_black_bbox"],
          "| alpha mean", s["alpha_mean"], "min", s["alpha_min"], "uniq", s["alpha_unique"], "<255", s["alpha_below_255"])
print("WROTE", OUT)
