import argparse
import glob
import json
import os
import re
import struct
import sys

import numpy as np
from PIL import Image

UNCOMPRESSED = {28: "R8G8B8A8_UNORM", 61: "R8_UNORM"}
BYTES_PER_PIXEL = {"R8G8B8A8_UNORM": 4, "R8_UNORM": 1}
DEFAULT_CLASSES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "references", "texture-classes.json")


def field(text, tag):
    found = re.search(r"<%s>([^<]*)</%s>" % (tag, tag), text)
    return found.group(1) if found else None


def attribute(text, tag):
    found = re.search(r'<%s text="([^"]*)"' % tag, text)
    return found.group(1) if found else None


def value(text, tag):
    element = field(text, tag)
    if element is not None:
        return element
    return attribute(text, tag)


def read_dds(path):
    raw = open(path, "rb").read()
    magic, size, flags, height, width, pitch, depth, mips = struct.unpack_from("<8I", raw, 0)
    assert magic == 0x20534444, path
    pf_size, pf_flags, fourcc, bits, rmask, gmask, bmask, amask = struct.unpack_from("<8I", raw, 76)
    caps, caps2 = struct.unpack_from("<2I", raw, 108)
    fourcc_text = fourcc.to_bytes(4, "little").decode("latin1").rstrip("\x00")
    header = {
        "bytes": len(raw), "width": width, "height": height, "header_mips": mips,
        "caps": hex(caps), "caps2": hex(caps2), "fourcc": fourcc_text, "bits": bits,
        "masks": [hex(rmask), hex(gmask), hex(bmask), hex(amask)], "offset": 128,
        "pf_flags": hex(pf_flags), "format": None,
    }
    if fourcc_text == "DX10":
        header["dxgi"] = struct.unpack_from("<I", raw, 128)[0]
        header["format"] = UNCOMPRESSED.get(header["dxgi"])
        header["offset"] = 148
    elif bits == 32 and amask == 0xFF000000:
        header["format"] = "R8G8B8A8_UNORM"
    elif bits == 8:
        header["format"] = "R8_UNORM"
    header["payload"] = raw[header["offset"]:]
    return header


def expected_payload(width, height, mips, bytes_per_pixel):
    total = 0
    for level in range(mips):
        total += max(width >> level, 1) * max(height >> level, 1) * bytes_per_pixel
    return total


def full_chain_levels(width, height):
    levels = 1
    while max(width, height) > 1:
        width = max(width // 2, 1)
        height = max(height // 2, 1)
        levels += 1
    return levels


def mip0_pixels(header):
    count = header["width"] * header["height"]
    if header["format"] == "R8G8B8A8_UNORM":
        return np.frombuffer(header["payload"][: count * 4], dtype=np.uint8).reshape(header["height"], header["width"], 4)
    return np.frombuffer(header["payload"][: count], dtype=np.uint8).reshape(header["height"], header["width"])


def source_pixels(path):
    return np.asarray(Image.open(path).convert("RGBA"))


def check_pair(directory, stem, source_path, classes):
    hard = []
    soft = []
    dds_path = None
    for candidate in glob.glob(os.path.join(directory, stem + ".*")):
        if os.path.splitext(candidate)[1].lower() == ".dds":
            dds_path = candidate
    tex_path = os.path.join(directory, stem + ".tex")
    if dds_path is None:
        hard.append("缺少 dds")
    if not os.path.exists(tex_path):
        hard.append("缺少 tex")
    if hard:
        return {"stem": stem, "status": "FAIL", "hard": hard, "soft": soft}, None
    dds = read_dds(dds_path)
    raw = open(tex_path, "rb").read()
    try:
        text = raw.decode("utf-8")
        decode_problem = None
    except UnicodeDecodeError as exc:
        text = ""
        decode_problem = "tex 非 UTF-8: " + str(exc)
    if decode_problem:
        hard.append(decode_problem)
    if dds["format"] is None:
        hard.append("dds 像素格式未登记: fourcc=%r bits=%d masks=%s" % (dds["fourcc"], dds["bits"], dds["masks"]))
        return {"stem": stem, "status": "FAIL", "hard": hard, "soft": soft}, dds
    declared = value(text, "ePixelformat")
    if declared != "PF_" + dds["format"]:
        hard.append(".tex 声明 %s 与 dds 实际 %s 不一致" % (declared, dds["format"]))
    if value(text, "m_Width") != str(dds["width"]) or value(text, "m_Height") != str(dds["height"]):
        hard.append(".tex 尺寸 %sx%s 与 dds %dx%d 不一致" % (value(text, "m_Width"), value(text, "m_Height"), dds["width"], dds["height"]))
    expected = expected_payload(dds["width"], dds["height"], dds["header_mips"], BYTES_PER_PIXEL[dds["format"]])
    if len(dds["payload"]) != expected:
        hard.append("dds 载荷 %d 字节与 %d 层应有 %d 字节不一致" % (len(dds["payload"]), dds["header_mips"], expected))
    if (attribute(text, "m_RelativePath") or "").lower() != stem.lower() + ".dds":
        hard.append("m_RelativePath %s 与文件名不匹配" % attribute(text, "m_RelativePath"))
    class_name = value(text, "m_ClassName")
    entry = classes.get(class_name)
    if entry is None:
        hard.append("类别未登记: " + str(class_name))
    else:
        if declared and declared != "PF_" + entry["pixel_format"]:
            hard.append(".tex 声明 %s 与类别表 %s 不一致" % (declared, entry["pixel_format"]))
        if int(value(text, "m_NumMipMaps")) != dds["header_mips"]:
            soft.append(".tex mip 数 %s 与 dds 头 %d 不一致" % (value(text, "m_NumMipMaps"), dds["header_mips"]))
        chain = full_chain_levels(dds["width"], dds["height"])
        if entry["allow_artist_mips"]:
            if dds["header_mips"] != chain:
                soft.append("mip 链不完整: 头写 %d，完整链应为 %d" % (dds["header_mips"], chain))
            if value(text, "bCompleteMipChain") != "true" or value(text, "bUseMips") != "true":
                soft.append(".tex 未声明完整 mip 链: bUseMips=%s bCompleteMipChain=%s" % (value(text, "bUseMips"), value(text, "bCompleteMipChain")))
        elif dds["header_mips"] != 1:
            soft.append("类别不允许 artist mips，dds 却有 %d 层" % dds["header_mips"])
        if value(text, "eFilterType") != "FT_" + entry["mip_filter"]:
            soft.append("eFilterType %s 与类别表 FT_%s 不一致" % (value(text, "eFilterType"), entry["mip_filter"]))
        for tag, key in (("fSupportScale", "mip_support_scale"), ("fGammaIn", "gamma_in"), ("fGammaOut", "gamma_out"), ("fValueClampMin", "clamp_min"), ("fValueClampMax", "clamp_max")):
            if abs(float(value(text, tag)) - entry[key]) > 1e-6:
                soft.append("%s %s 与类别表 %s 不一致" % (tag, value(text, tag), entry[key]))
        if dds["width"] > entry["max_width"] or dds["height"] > entry["max_height"] or dds["width"] < entry["min_width"] or dds["height"] < entry["min_height"]:
            hard.append("尺寸 %dx%d 超出类别范围 %d-%d" % (dds["width"], dds["height"], entry["min_width"], entry["max_width"]))
        if entry["require_square"] and dds["width"] != dds["height"]:
            hard.append("类别要求正方形而实际 %dx%d" % (dds["width"], dds["height"]))
    tags = re.findall(r'<Element text="([^"]*)"/>', text)
    if not tags or tags[0] != class_name:
        soft.append("m_Tags %s 与 m_ClassName %s 不匹配" % (tags, class_name))
    if value(text, "m_Description") != value(text, "m_Name"):
        soft.append("m_Description 与 m_Name 不一致")
    pixel = None
    if source_path is not None and os.path.exists(source_path):
        src = source_pixels(source_path)
        got = mip0_pixels(dds)
        if dds["format"] == "R8_UNORM":
            src = src[:, :, 0]
        if src.shape != got.shape:
            hard.append("源图形状 %s 与 dds 首层 %s 不一致" % (src.shape, got.shape))
        else:
            max_abs = int(np.abs(src.astype(np.int16) - got.astype(np.int16)).max())
            pixel = {"max_abs_diff": max_abs}
            if max_abs != 0:
                hard.append("源图与 dds 首层像素不一致: max_abs_diff=%d" % max_abs)
    row = {
        "stem": stem, "status": "PASS" if not hard else "FAIL", "hard": hard, "soft": soft,
        "class": class_name, "filter": value(text, "eFilterType"), "format": dds["format"],
        "fourcc": dds["fourcc"], "bits": dds["bits"], "masks": dds["masks"],
        "width": dds["width"], "height": dds["height"], "mips": dds["header_mips"],
        "caps": dds["caps"], "caps2": dds["caps2"], "dds_bytes": dds["bytes"],
        "tex_bytes": os.path.getsize(tex_path), "pixel": pixel,
    }
    return row, dds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("report")
    parser.add_argument("--source-dir")
    parser.add_argument("--classes", default=DEFAULT_CLASSES)
    args = parser.parse_args()
    classes = json.load(open(args.classes, encoding="utf-8"))
    stems = sorted({os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(args.directory, "*.tex"))})
    stems += sorted({os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(args.directory, "*.dds")) if os.path.splitext(os.path.basename(p))[0] not in stems})
    rows = []
    hard_failures = 0
    soft_items = 0
    for stem in stems:
        source_path = os.path.join(args.source_dir, stem + ".png") if args.source_dir else None
        row, dds = check_pair(args.directory, stem, source_path, classes)
        if row["hard"]:
            hard_failures += 1
        soft_items += len(row["soft"])
        rows.append(row)
        print("%-42s %-4s class=%-18s fmt=%-14s %dx%d mips=%-2d dds=%-8d tex=%-5d pixel=%s" % (
            stem, row["status"], row.get("class"), row.get("format"), row.get("width", 0), row.get("height", 0),
            row.get("mips", 0), row.get("dds_bytes", 0), row.get("tex_bytes", 0),
            row["pixel"]["max_abs_diff"] if row.get("pixel") else "-"))
        for problem in row["hard"]:
            print("    HARD " + problem)
        for problem in row["soft"]:
            print("    SOFT " + problem)
    print("DIR", args.directory)
    print("PAIRS", len(rows), "HARD_FAILURES", hard_failures, "SOFT_ITEMS", soft_items)
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    return 1 if hard_failures else 0


if __name__ == "__main__":
    sys.exit(main())
