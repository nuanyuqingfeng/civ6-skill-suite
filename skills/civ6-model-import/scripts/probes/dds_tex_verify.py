import json
import os
import re
import struct

YSL = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Yusanjia\Jinzhou_Yusanjia\Textures"
JX = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi\Textures"

TARGETS = [
    (YSL, "MI_R2T1YangyangMd10011Hair_Opacity"),
    (YSL, "MI_R2T1YangyangMd10011Bangs_Opacity"),
    (YSL, "MI_R2T1MaxiaofangMd10011Hair_Opacity"),
    (YSL, "MI_R2T1MaxiaofangMd10011Bangs_Opacity"),
    (YSL, "MI_R2T1BailianMd10011Hair_Opacity"),
    (YSL, "MI_R2T1BailianMd10011Bangs_Opacity"),
    (JX, "MI_R2T1JinxiMd10011Hair_Opacity"),
    (JX, "MI_R2T1JinxiMd10011Bangs_Opacity"),
    (JX, "JINHSI_BANGS_OPACITY"),
]

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp", "opacity_verify.json")


def read_dds(path):
    raw = open(path, "rb").read()
    magic, size, flags, height, width, pitch, depth, mips = struct.unpack_from("<8I", raw, 0)
    assert magic == 0x20534444, path
    pf_size, pf_flags, fourcc, bits, rmask, gmask, bmask, amask = struct.unpack_from("<8I", raw, 76)
    caps, caps2 = struct.unpack_from("<2I", raw, 108)
    data = raw[128:]
    offsets = []
    off = 0
    for level in range(max(mips, 1)):
        dim = max(width >> level, 1)
        offsets.append((off, dim * dim))
        off += dim * dim
    white = data[: width * width].count(255) / float(width * width)
    mip_white = []
    for off_l, length in offsets:
        block = data[off_l: off_l + length]
        mip_white.append(round(block.count(255) / float(length), 6))
    return {
        "bytes": len(raw),
        "width": width,
        "height": height,
        "header_mips": mips,
        "payload_bytes": len(data),
        "expected_payload": sum(length for _, length in offsets),
        "pixelformat": {"size": pf_size, "flags": hex(pf_flags), "fourcc": fourcc.to_bytes(4, "little").decode("latin1"),
                        "bits": bits, "rmask": hex(rmask), "gmask": hex(gmask), "bmask": hex(bmask), "amask": hex(amask)},
        "caps": hex(caps),
        "caps2": hex(caps2),
        "flag_ddsd_linearsize": bool(flags & 0x00080000),
        "flag_ddsd_mipmapcount": bool(flags & 0x00020000),
        "white_ratio": round(white, 6),
        "mip_white": mip_white,
    }


def read_tex(path):
    text = open(path, encoding="utf-8").read()
    def one(tag):
        m = re.search(r"<%s>([^<]*)</%s>" % (tag, tag), text)
        return m.group(1) if m else None
    rel = re.search(r'<m_RelativePath text="([^"]*)"', text)
    name = re.search(r'<m_Name text="([^"]*)"', text)
    cls = re.search(r'<m_ClassName(?: text="([^"]*)"|>([^<]*)</m_ClassName>)', text)
    return {
        "width": one("m_Width"),
        "height": one("m_Height"),
        "mips": one("m_NumMipMaps"),
        "pixelformat": one("ePixelformat"),
        "class": (lambda m: m.group(1) or m.group(2) if m else None)(cls),
        "relative_path": rel.group(1) if rel else None,
        "name": name.group(1) if name else None,
        "complete_mip_chain": "<bCompleteMipChain>true</bCompleteMipChain>" in text,
    }


def main():
    rows = []
    for root, name in TARGETS:
        dds_path = os.path.join(root, name + ".dds")
        tex_path = os.path.join(root, name + ".tex")
        d = read_dds(dds_path)
        t = read_tex(tex_path)
        d["name"] = name
        d["tex"] = t
        d["ok_white"] = d["white_ratio"] == 1.0 and all(v == 1.0 for v in d["mip_white"])
        d["ok_mips"] = str(d["header_mips"]) == t["mips"] and d["payload_bytes"] == d["expected_payload"]
        d["ok_size"] = str(d["width"]) == t["width"] and str(d["height"]) == t["height"]
        d["ok_path"] = t["relative_path"] == name + ".dds" and t["name"] == name
        rows.append(d)

    result = {"rows": rows, "all_ok": all(r["ok_white"] and r["ok_mips"] and r["ok_size"] and r["ok_path"] for r in rows)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    for r in rows:
        print("VERIFY", r["name"], r["width"], r["header_mips"], r["white_ratio"], r["ok_mips"], r["ok_size"], r["ok_path"], r["tex"]["pixelformat"], r["tex"]["class"])
    print("ALL_OK", result["all_ok"], OUT)


if __name__ == "__main__":
    main()
