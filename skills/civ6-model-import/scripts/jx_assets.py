import os
import shutil
import struct
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

PROJ = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi"
STAGE = r"E:\SoftWares\civ6_nexus_work\jinhsi_fgx"
SRC = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model"
SRC_STAR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\CommonTexture\Star"
DENIA = r"D:\desktop\mods-CIV6\others\Denia_Pack\Denia_Pack"
TEXCONV = r"C:\Users\Administrator\.agents\skills\civ6-modding\art\bin\texconv.exe"
TMP = r"E:\SoftWares\civ6_nexus_work\tex_tmp"

os.makedirs(TMP, exist_ok=True)

MATS = {
    "Bangs": "T_R2T1JinxiMd10011Bangs_D.png",
    "Hair": "T_R2T1JinxiMd10011Hair_D.png",
    "Face": "T_R2T1JinxiMd10011Face_D.png",
    "Down": "T_R2T1JinxiMd10011Down_D.png",
    "Skirt": "T_R2T1JinxiMd10011Skirt_D.png",
    "Eye": "T_R2T1JinxiMd10011Eye_D.png",
    "6XingStar": None,
}
OPACITY_MATS = ["Bangs", "Hair", "Skirt"]
STAR_TEX = "T_6XingStar_D.png"


# Eye 眼球贴图里眼睛图形的中心（归一化坐标）与缩放半径比例
EYE_CENTER = (0.51025, 0.55176)
EYE_SCALE = 0.99
EYE_RADIUS = 0.205


def shrink_eye(im):
    """围绕眼睛图形中心做缩放重采样：虹膜环向内收，四周巩膜区域相应扩展。"""
    arr = np.asarray(im.convert("RGB"), dtype=np.float32)
    height, width = arr.shape[:2]
    cx = EYE_CENTER[0] * width
    cy = EYE_CENTER[1] * height
    radius = EYE_RADIUS * width
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    dx = xx - cx
    dy = yy - cy
    dist = np.hypot(dx, dy)
    weight = np.clip((radius - dist) / (radius * 0.15), 0.0, 1.0)
    weight = weight * weight * (3.0 - 2.0 * weight)
    factor = 1.0 / EYE_SCALE - 1.0
    src_x = xx + weight * dx * factor
    src_y = yy + weight * dy * factor
    out = np.empty_like(arr)
    for channel in range(3):
        out[:, :, channel] = map_coordinates(arr[:, :, channel], [src_y, src_x], order=1, mode="nearest")
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def _mip_count(size):
    count = 1
    while size > 1:
        size //= 2
        count += 1
    return count


def make_basecolor(name, png_path):
    out_name = "MI_R2T1JinxiMd10011%s_BaseColor" % name if name != "6XingStar" else "MI_6XingStar_BaseColor"
    tmp_png = os.path.join(TMP, out_name + "_1024.png")
    src = Image.open(png_path).convert("RGBA")
    rgb = src.convert("RGB").resize((1024, 1024), Image.LANCZOS)
    alpha = src.split()[3].resize((1024, 1024), Image.LANCZOS)
    Image.merge("RGBA", (*rgb.split(), alpha)).save(tmp_png)
    subprocess.run([TEXCONV, "-y", "-f", "RGBA", "-m", "11", "-ft", "dds", "-o", TMP, tmp_png],
                   check=True, capture_output=True)
    dds = os.path.join(TMP, out_name + "_1024.dds")
    shutil.copy2(dds, os.path.join(PROJ, "Textures", out_name + ".dds"))
    print("TEX_BC", out_name)
    return out_name


def make_source_basecolor(name, png_path):
    """源图原尺寸转成 RGBA DDS：不缩放，alpha 恒为 255。"""
    out_name = "MI_R2T1JinxiMd10011%s_BaseColor" % name
    src = Image.open(png_path).convert("RGBA")
    if name == "Eye":
        src = shrink_eye(src).convert("RGBA")
    src.putalpha(255)
    width, height = src.size
    tmp_png = os.path.join(TMP, out_name + "_native.png")
    src.save(tmp_png)
    subprocess.run([TEXCONV, "-y", "-f", "RGBA", "-m", "%d" % _mip_count(width),
                    "-ft", "dds", "-o", TMP, tmp_png], check=True, capture_output=True)
    shutil.copy2(os.path.join(TMP, out_name + "_native.dds"),
                 os.path.join(PROJ, "Textures", out_name + ".dds"))
    print("TEX_BC", out_name, width, height, _mip_count(width))
    return out_name, width, height, _mip_count(width)


def make_opacity(name, png_path):
    out_name = "MI_R2T1JinxiMd10011%s_Opacity" % name
    alpha = Image.open(png_path).convert("RGBA").split()[3].resize((256, 256), Image.LANCZOS)
    mips = []
    size = 256
    cur = alpha
    while size >= 1:
        mips.append(cur.tobytes())
        size //= 2
        if size >= 1:
            cur = cur.resize((size, size), Image.BOX)
    write_r8_dds(os.path.join(PROJ, "Textures", out_name + ".dds"), 256, len(mips), mips)
    print("TEX_OP", out_name)
    return out_name


def write_r8_dds(path, size, mip_count, mips):
    header_size = 124
    pitch = size
    flags = 0x0000100F
    caps2 = 0
    data_len = sum(len(m) for m in mips)
    total = 4 + header_size + data_len
    hdr = struct.pack("<I", 0x20534444)
    hdr += struct.pack("<7I", header_size, flags, size, size, pitch, 0, mip_count)
    hdr += b"\x00" * 44
    hdr += struct.pack("<II", 32, 0x00000040)
    hdr += struct.pack("<4s", b"")
    hdr += struct.pack("<5I", 8, 0x000000FF, 0, 0, 0)
    hdr += struct.pack("<5I", 0x00401007, caps2, 0, 0, 0)
    with open(path, "wb") as fh:
        fh.write(hdr)
        for m in mips:
            fh.write(m)


TEX_BC_TEMPLATE = open(os.path.join(DENIA, "Textures", "MI_R2T1DaniyaMd10011Bangs1_BaseColor.tex"),
                       encoding="utf-8").read()
TEX_OP_TEMPLATE = open(os.path.join(DENIA, "Textures", "MI_R2T1DaniyaMd10011Bangs1_Opacity.tex"),
                       encoding="utf-8").read()
MTL_TEMPLATE = open(os.path.join(DENIA, "Materials", "MI_R2T1DaniyaMd10011Bangs1.mtl"),
                    encoding="utf-8").read()
MTL_OPACITY_TEMPLATE = open(os.path.join(DENIA, "Materials", "MI_R2T1DaniyaMd10011Hair01.mtl"),
                            encoding="utf-8").read()


def render_tex(template, old_name, new_name, width, height, mips):
    text = template.replace(old_name, new_name)
    text = text.replace("<m_Height>%d</m_Height>" % (1024 if width == 1024 else 256),
                        "<m_Height>%d</m_Height>" % height)
    return text


def write_tex(path, template, dania_name, new_name, width, height, mips, dds_name):
    text = template
    text = text.replace(dania_name, new_name)
    if width == 1024 and height == 1024:
        pass
    text = text.replace("<m_Width>1024</m_Width>", "<m_Width>%d</m_Width>" % width)
    text = text.replace("<m_Width>256</m_Width>", "<m_Width>%d</m_Width>" % width)
    text = text.replace("<m_Height>1024</m_Height>", "<m_Height>%d</m_Height>" % height)
    text = text.replace("<m_Height>256</m_Height>", "<m_Height>%d</m_Height>" % height)
    text = text.replace("<m_NumMipMaps>11</m_NumMipMaps>", "<m_NumMipMaps>%d</m_NumMipMaps>" % mips)
    text = text.replace("<m_NumMipMaps>9</m_NumMipMaps>", "<m_NumMipMaps>%d</m_NumMipMaps>" % mips)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def write_mtl(path, mat_name, base_tex, opacity_tex):
    if opacity_tex:
        text = MTL_OPACITY_TEMPLATE.replace("MI_R2T1DaniyaMd10011Hair01_BaseColor", base_tex)
        text = text.replace("MI_R2T1DaniyaMd10011Hair01_Opacity", opacity_tex)
        text = text.replace("MI_R2T1DaniyaMd10011Hair01", mat_name)
    else:
        text = MTL_TEMPLATE.replace("MI_R2T1DaniyaMd10011Bangs1_BaseColor", base_tex)
        text = text.replace("MI_R2T1DaniyaMd10011Bangs1", mat_name)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def main(names=()):
    only = set(names)
    unknown = only - set(MATS)
    if unknown:
        raise KeyError("未知材质：%s" % sorted(unknown))

    for sub in ("Geometries", "Animations", "Materials", "Textures"):
        os.makedirs(os.path.join(PROJ, sub), exist_ok=True)

    if not only:
        for ext in ("fgx", "geo", "wig"):
            shutil.copy2(os.path.join(STAGE, "LEAD_Jinhsi_QYQXP." + ext),
                         os.path.join(PROJ, "Geometries", "LEAD_Jinhsi_QYQXP." + ext))
        print("GEO_COPIED")

        for name in ["JX_IDLE", "JX_FirstMeet", "JX_DeclareWarHuman", "JX_DeclareWarAI",
                     "JX_Kudos", "JX_Warning", "JX_Defeat"]:
            for ext in ("anm", "fgx", "wig"):
                shutil.copy2(os.path.join(STAGE, name + "." + ext),
                             os.path.join(PROJ, "Animations", name + "." + ext))
        print("ANIM_COPIED")

    star_src = os.path.join(SRC_STAR, STAR_TEX)
    for name, png in MATS.items():
        if only and name not in only:
            continue
        png_path = star_src if name == "6XingStar" else os.path.join(SRC, png)
        if name == "Eye":
            base, width, height, mips = make_source_basecolor(name, png_path)
        else:
            base = make_basecolor(name, png_path)
            width = height = 1024
            mips = 11
        write_tex(os.path.join(PROJ, "Textures", base + ".tex"), TEX_BC_TEMPLATE,
                  "MI_R2T1DaniyaMd10011Bangs1_BaseColor", base, width, height, mips, base + ".dds")
        opacity = None
        if name in OPACITY_MATS:
            opacity = make_opacity(name, png_path)
            write_tex(os.path.join(PROJ, "Textures", opacity + ".tex"), TEX_OP_TEMPLATE,
                      "MI_R2T1DaniyaMd10011Bangs1_Opacity", opacity, 256, 256, 9, opacity + ".dds")
        mat_name = "MI_R2T1JinxiMd10011" + name if name != "6XingStar" else "MI_6XingStar"
        write_mtl(os.path.join(PROJ, "Materials", mat_name + ".mtl"), mat_name, base, opacity)
        print("MTL_DONE", mat_name)
    print("ASSETS_DONE")


if __name__ == "__main__":
    main(sys.argv[1:])
