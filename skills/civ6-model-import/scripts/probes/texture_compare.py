import hashlib
import json
import os
import struct

import numpy as np
from PIL import Image

SRC = r"G:\Wuwa_3D_Assets\Characters"
MMD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp", "mmd")
PRJ = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Yusanjia\Jinzhou_Yusanjia\Textures"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp", "tex_compare.json")

CASES = [
    ("yangyang", "Yangyang", r"角色_Yangyang\converted\Client\Content\Aki\Character\Role\FemaleM\Yangyang\R2T1YangyangMd10011\Model", "MI_R2T1YangyangMd10011"),
    ("chixia", "Maxiaofang", r"角色_Maxiaofang\converted\Client\Content\Aki\Character\Role\FemaleM\Maxiaofang\R2T1MaxiaofangMd10011\Model", "MI_R2T1MaxiaofangMd10011"),
    ("baizhi", "BaiLian", r"角色_BaiLian\converted\Client\Content\Aki\Character\Role\FemaleXL\BaiLian\R2T1BaiLianMd10011\Model", "MI_R2T1BailianMd10011"),
]


def stats(arr):
    rgb = arr[:, :, :3].astype(np.float64)
    lum = rgb.mean(axis=2)
    gx = np.abs(np.diff(lum, axis=1)).mean()
    gy = np.abs(np.diff(lum, axis=0)).mean()
    return {
        "mean": round(float(lum.mean()), 2),
        "std": round(float(lum.std()), 2),
        "p5": round(float(np.percentile(lum, 5)), 1),
        "p95": round(float(np.percentile(lum, 95)), 1),
        "grad": round(float((gx + gy) / 2), 3),
        "alpha_mean": round(float(arr[:, :, 3].mean()), 1) if arr.shape[2] == 4 else None,
    }


def from_png(path):
    im = Image.open(path).convert("RGBA")
    arr = np.asarray(im)
    d = stats(arr)
    d.update({"w": im.width, "h": im.height, "bytes": os.path.getsize(path), "md5": hashlib.md5(open(path, "rb").read()).hexdigest()[:12]})
    return d


def from_dds(path):
    raw = open(path, "rb").read()
    magic, size, flags, height, width, pitch, depth, mips = struct.unpack_from("<8I", raw, 0)
    arr = np.frombuffer(raw[128:128 + width * height * 4], dtype=np.uint8).reshape(height, width, 4)
    d = stats(arr)
    d.update({"w": width, "h": height, "mips": mips, "bytes": len(raw)})
    return d


def main():
    rows = []
    for slug, char, rel, mat in CASES:
        for part in ("Hair", "Bangs"):
            src_name = "T_R2T1%sMd10011%s_D.png" % (char, part)
            src = os.path.join(SRC, rel, src_name)
            mmd = os.path.join(MMD, slug, "tex", src_name)
            dds = os.path.join(PRJ, "%s%s_BaseColor.dds" % (mat, part))
            rec = {"char": slug, "part": part}
            if os.path.exists(src):
                rec["source"] = from_png(src)
            if os.path.exists(mmd):
                rec["mmd"] = from_png(mmd)
            if os.path.exists(dds):
                rec["project"] = from_dds(dds)
            rows.append(rec)
            print("CMP", slug, part)
            for key in ("source", "mmd", "project"):
                if key in rec:
                    r = rec[key]
                    print("   %-8s %dx%d mean %.1f std %.1f p5 %.1f p95 %.1f grad %.3f bytes %d" % (
                        key, r["w"], r["h"], r["mean"], r["std"], r["p5"], r["p95"], r["grad"], r["bytes"]))
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    print("OUT", OUT)


if __name__ == "__main__":
    main()
