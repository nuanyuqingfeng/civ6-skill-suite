import json
import os
import struct

import numpy as np
from PIL import Image

SRC = r"G:\Wuwa_3D_Assets\Characters"
DST = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Yusanjia\Jinzhou_Yusanjia\Textures"

CASES = [
    ("MI_R2T1YangyangMd10011Hair_BaseColor", r"角色_Yangyang\converted\Client\Content\Aki\Character\Role\FemaleM\Yangyang\R2T1YangyangMd10011\Model\T_R2T1YangyangMd10011Hair_D.png"),
    ("MI_R2T1MaxiaofangMd10011Hair_BaseColor", r"角色_Maxiaofang\converted\Client\Content\Aki\Character\Role\FemaleM\Maxiaofang\R2T1MaxiaofangMd10011\Model\T_R2T1MaxiaofangMd10011Hair_D.png"),
    ("MI_R2T1BailianMd10011Hair_BaseColor", r"角色_BaiLian\converted\Client\Content\Aki\Character\Role\FemaleXL\BaiLian\R2T1BaiLianMd10011\Model\T_R2T1BaiLianMd10011Hair_D.png"),
    ("MI_R2T1YangyangMd10011Bangs_BaseColor", r"角色_Yangyang\converted\Client\Content\Aki\Character\Role\FemaleM\Yangyang\R2T1YangyangMd10011\Model\T_R2T1YangyangMd10011Bangs_D.png"),
    ("MI_R2T1MaxiaofangMd10011Bangs_BaseColor", r"角色_Maxiaofang\converted\Client\Content\Aki\Character\Role\FemaleM\Maxiaofang\R2T1MaxiaofangMd10011\Model\T_R2T1MaxiaofangMd10011Bangs_D.png"),
    ("MI_R2T1BailianMd10011Bangs_BaseColor", r"角色_BaiLian\converted\Client\Content\Aki\Character\Role\FemaleXL\BaiLian\R2T1BaiLianMd10011\Model\T_R2T1BaiLianMd10011Bangs_D.png"),
]

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp", "hair_reimport.json")


def mip_chain(rgba):
    chain = [rgba]
    while chain[-1].shape[0] > 1 and chain[-1].shape[1] > 1:
        img = Image.fromarray(chain[-1], mode="RGBA")
        chain.append(np.asarray(img.resize((max(img.width // 2, 1), max(img.height // 2, 1)), Image.BOX)))
    return chain


def rebuild(name, rel):
    path = os.path.join(DST, name + ".dds")
    header = open(path, "rb").read(128)
    magic, size, flags, height, width, pitch, depth, mips = struct.unpack_from("<8I", header, 0)
    assert magic == 0x20534444, path
    src = Image.open(os.path.join(SRC, rel)).convert("RGBA")
    assert src.size == (width, height), (src.size, width, height)
    chain = mip_chain(np.asarray(src))
    assert len(chain) == mips, (len(chain), mips)
    body = b"".join(np.ascontiguousarray(level).tobytes() for level in chain)
    open(path, "wb").write(header + body)
    first = np.asarray(chain[0]).astype(np.float64)
    return {
        "name": name,
        "size": [width, height],
        "mips": mips,
        "mean_rgb": [round(float(v), 2) for v in first[:, :, :3].mean(axis=(0, 1))],
        "alpha_mean": round(float(first[:, :, 3].mean()), 1),
        "bytes": len(body) + 128,
    }


def main():
    rows = [rebuild(name, rel) for name, rel in CASES]
    for r in rows:
        print("REIMPORT", r["name"], r["size"], r["mips"], r["mean_rgb"], "alpha", r["alpha_mean"])
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"rows": rows}, fh, ensure_ascii=False, indent=1)
    print("OUT", OUT)


if __name__ == "__main__":
    main()
