#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""hair_toon_refine.py — 文明6 领袖头发 BaseColor 的 Toon 观感精修（v2 流程参考实现）。

用途：把「平涂/塑料感」的头发贴图，重烘成接近鸣潮/原神那类 ToonHair 的观感：
宽而柔的冷色带状高光、暗部仍可辨发束分层、整体明度不跳变。

设计前提（必须遵守，勿"优化"）：
  * 只改 BaseColor。不碰几何、材质类、Opacity、灯光、.tex 的 W/H/mips。
  * 基底取**解包源 _D**直转，不叠加任何历史中间版本（压暗/锐化/软遮罩…）。
  * _HM 是 RGBA 分通道图，只有 **G** 有信息；读它必须取 G，禁止 convert("L")。
  * 亮度分位锚定到「改前现网贴图」，保证实机亮度不跳变——这是全流程的支点。

用法：
    python hair_toon_refine.py --config job.json preview   # 只出预览与指标，不落盘
    python hair_toon_refine.py --config job.json apply     # 校验通过后覆盖工程 DDS

job.json 见同目录 hair_job.example.json；字段含义见 hair-toon-refine.md。
退出码：0=成功；2=前置断言失败（输入缺失/尺寸不符/DDS 尺寸异常）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

# ---- 默认参数（新领袖先用这套，再按实测微调；见文档「调参入口」） ----------------
DEFAULTS = {
    "target": 2048,
    "mips": 12,
    # D1 拆赛璐璐硬白斑
    "blob_t0": 100.0, "blob_t1": 180.0, "blob_soft": 0.60, "blob_blur": 20,
    # D2 双层柔高光
    "spec_wide_r": 12, "spec_narrow_r": 3, "spec_mix": 0.65,
    "spec_lum": 0.12, "spec_tint": 0.22,
    # D3 UV-V 顶部渐变
    "grad_color": [227, 245, 251], "grad_w": 0.07, "grad_p": 1.4,
    # D4 暗部抬升
    "shadow_lift": 0.08, "shadow_knee": 45.0,
    # D5 亮度分位锚定 + 高频回注
    "anchor_lift_p5": 6.0, "anchor_lift_p50": 1.0, "anchor_drop_p95": 12.0,
    "anchor_tail": 0.42, "p95_cap": {},
    "detail_gain": 0.20, "detail_only_below": 110.0,
    # D6 双色调
    "duotone": 0.45, "tint_gamma": 1.8,
    "shadow": [34, 38, 56], "tint": [95, 142, 200],
    "l_lo": 0.16, "l_hi": 0.53,
}


def die(msg):
    print("FAIL " + msg, file=sys.stderr)
    sys.exit(2)


def blur(a, r):
    return np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(r)), np.float32)


def norm01(x, p=98):
    s = float(np.percentile(x, p))
    return np.clip(x / max(s, 1e-3), 0.0, 1.0)


def dds_head(path):
    h = open(path, "rb").read(128)
    return dict(zip(("magic", "size", "flags", "h", "w", "pitch", "d", "mips"),
                    struct.unpack_from("<8I", h, 0)))


def sha16(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def metric(a):
    L = a.mean(2)
    mx, mn = a.max(2), a.min(2)
    return dict(mean=float(L.mean()),
                p5=float(np.percentile(L, 5)), p50=float(np.percentile(L, 50)),
                p95=float(np.percentile(L, 95)), p99=float(np.percentile(L, 99)),
                bright=float((L > 110).mean() * 100),
                dark=float((L < 25).mean() * 100),
                sat=float(((mx - mn) / np.maximum(mx, 1e-3)).mean()),
                br=float((a[..., 2] - a[..., 0]).mean()),
                hp=float(np.abs(L - blur(L, 3)).mean()))


class Job:
    def __init__(self, cfg):
        self.cfg = cfg
        p = dict(DEFAULTS)
        p.update(cfg.get("params", {}))
        self.p = p
        self.target = int(p["target"])
        self.mips = int(p["mips"])
        self.expect = 128 + 4 * sum((self.target >> k) ** 2 for k in range(self.mips))
        self.proj_tex = cfg["proj_tex"]
        self.src_dir = cfg["src_dir"]
        self.src_prefix = cfg["src_prefix"]
        self.tex_prefix = cfg["tex_prefix"]
        self.parts = cfg.get("parts", ["Hair", "Bangs"])
        self.texconv = cfg.get("texconv", "texconv")
        self.work = cfg.get("work", cfg.get("out", "."))
        self.grad_color = np.array(p["grad_color"], np.float32)
        self.shadow = np.array(p["shadow"], np.float32)
        self.tint = np.array(p["tint"], np.float32)

    def name_of(self, part):
        return "%s%s_BaseColor" % (self.tex_prefix, part)

    def read_mip0(self, path):
        raw = open(path, "rb").read()
        if len(raw) != self.expect:
            die("%s 大小 %d != 期望 %d（.tex 尺寸/mip 与 target 不符？）"
                % (os.path.basename(path), len(raw), self.expect))
        return (np.frombuffer(raw[128:128 + self.target * self.target * 4], np.uint8)
                .reshape(self.target, self.target, 4)[..., :3].astype(np.float32))

    # ---- 六步 ----
    def build(self, part):
        p, T = self.p, self.target
        name = self.name_of(part)
        src_p = os.path.join(self.src_dir, "%s%s_D.png" % (self.src_prefix, part))
        hm_p = os.path.join(self.src_dir, "%s%s_HM.png" % (self.src_prefix, part))
        for f in (src_p, hm_p):
            if not os.path.exists(f):
                die("缺源贴图 " + f)
        src = np.asarray(Image.open(src_p).convert("RGB"), np.float32)
        if src.shape[:2] != (T, T):
            src = np.asarray(Image.fromarray(src.astype(np.uint8))
                             .resize((T, T), Image.LANCZOS), np.float32)
            print("WARN 源 _D 非 %d²，已 LANCZOS 放大" % T)
        # ★ _HM 取 G 通道（R≈0 / B 恒 255，只有 G 有信息）
        hm = np.asarray(Image.open(hm_p).convert("RGB"), np.uint8)[..., 1]
        if hm.max() < 8:
            die("_HM 的 G 通道近乎全黑：源图可能不是 RGBA 分通道格式，先体检再跑")
        g = np.asarray(Image.fromarray(hm).resize((T, T), Image.BILINEAR), np.float32) / 255.0

        cur_p = os.path.join(self.proj_tex, name + ".dds")
        cur = self.read_mip0(cur_p)
        if cur.shape != src.shape:
            die("现网 DDS 与源尺寸不一致：%s vs %s" % (cur.shape, src.shape))

        rgb = src.copy()

        # D1 软化源 _D 的赛璐璐硬边白斑
        L0 = rgb.mean(2)
        bright = np.clip((L0 - p["blob_t0"]) / (p["blob_t1"] - p["blob_t0"]), 0.0, 1.0)
        soft = blur(bright * 255.0, p["blob_blur"]) / 255.0
        L_blur = blur(L0, p["blob_blur"])
        comp = L0 - (L0 - L_blur) * p["blob_soft"] * soft
        rgb *= (comp / np.maximum(L0, 1e-3))[..., None]

        # D2 HM G → 宽/窄双层柔高光
        gn = np.clip(g / max(float(np.percentile(g, 98)), 1e-3), 0.0, 1.0)
        wide = norm01(blur(gn * 255.0, p["spec_wide_r"]) / 255.0)
        narrow = norm01(np.clip(gn - blur(gn * 255.0, p["spec_narrow_r"]) / 255.0, 0.0, 1.0))
        spec = p["spec_mix"] * wide + (1.0 - p["spec_mix"]) * narrow
        rgb *= (1.0 + p["spec_lum"] * spec)[..., None]
        w = (p["spec_tint"] * spec)[..., None]
        rgb = rgb * (1.0 - w) + self.grad_color * w

        # D3 UV-V 顶部渐变（只加不减）
        v = np.linspace(0.0, 1.0, T, dtype=np.float32)[:, None]
        grad = np.clip(1.0 - v, 0.0, 1.0) ** p["grad_p"]
        wg = (p["grad_w"] * grad)[..., None]
        rgb = rgb * (1.0 - wg) + self.grad_color * wg

        # D4 暗部抬升
        L = rgb.mean(2)
        down = np.clip((p["shadow_knee"] - L) / p["shadow_knee"], 0.0, 1.0)
        rgb *= (1.0 + p["shadow_lift"] * down)[..., None]

        # D5 亮度分位锚定到改前现网基底 —— 全流程支点，禁止省略/改全局系数
        cq = np.percentile(cur.mean(2), [5, 50, 95])
        nq = np.percentile(rgb.mean(2), [5, 50, 95])
        cap = p["p95_cap"].get(part)
        p95 = cq[2] - p["anchor_drop_p95"]
        if cap is not None:
            p95 = min(p95, float(cap))
        dst_q = [cq[0] + p["anchor_lift_p5"], cq[1] + p["anchor_lift_p50"], p95]
        Lm = self.anchor_map(rgb.mean(2), nq, dst_q)
        rgb *= (Lm / np.maximum(rgb.mean(2), 1e-3))[..., None]
        rgb = np.clip(rgb, 0, 255)

        # D5b 回注源发丝高频（严格只在暗/中调）
        detail = (L0 - blur(L0, 3))[..., None]
        dark = np.clip((p["detail_only_below"] - L0) / 40.0, 0.0, 1.0)[..., None]
        rgb = np.clip(rgb + detail * p["detail_gain"] * dark, 0, 255)

        # D6 双色调，色偏只落亮部
        L = rgb.mean(2)
        t = np.clip((L / 255.0 - p["l_lo"]) / (p["l_hi"] - p["l_lo"]), 0.0, 1.0) ** p["tint_gamma"]
        tc = self.shadow * (1.0 - t[..., None]) + self.tint * t[..., None]
        tc *= (L / np.maximum(tc.mean(2), 1e-3))[..., None]
        rgb = np.clip(rgb * (1.0 - p["duotone"]) + tc * p["duotone"], 0, 255)

        return name, rgb.astype(np.uint8), cur.astype(np.uint8), src.astype(np.uint8), (nq, dst_q)

    def anchor_map(self, L, src_q, dst_q):
        p = self.p
        x = [0.0, src_q[0], src_q[1], src_q[2], 255.0]
        tail = dst_q[2] + (255.0 - src_q[2]) * p["anchor_tail"]
        y = [0.0, dst_q[0], dst_q[1], dst_q[2], min(255.0, max(tail, dst_q[2] + 1))]
        return np.interp(L, x, y).astype(np.float32)


def save_sheet(results, path, tag="REFINED"):
    """改前/改后并排 + 局部放大，共两行。"""
    S = 560
    cols = []
    for part, out, cur, src, _ in results:
        for label, arr in (("NOW", cur), (tag, out)):
            im = Image.fromarray(arr)
            w, h = im.size
            cw = min(w, h) // 2
            crop = im.crop((w // 4, h // 4, w // 4 + cw, h // 4 + cw))
            cols.append((label, im.resize((S, S), Image.LANCZOS),
                         crop.resize((S, S), Image.LANCZOS)))
    if not cols:
        return
    sheet = Image.new("RGB", (S * len(cols), S * 2), (24, 24, 28))
    for col, (_, full, crop) in enumerate(cols):
        sheet.paste(full, (col * S, 0))
        sheet.paste(crop, (col * S, S))
    sheet.save(path)


def make_dds(job, name, rgb):
    os.makedirs(job.work, exist_ok=True)
    png = os.path.join(job.work, name + "_refined.png")
    Image.merge("RGBA", (*Image.fromarray(rgb).split(),
                         Image.new("L", (job.target, job.target), 255))).save(png)
    out = os.path.join(job.work, name + "_refined.dds")
    r = subprocess.run([job.texconv, "-y", "-f", "RGBA", "-m", str(job.mips),
                        "-ft", "dds", "-o", job.work, png], capture_output=True, text=True)
    if r.returncode != 0:
        die("texconv 失败: " + (r.stderr or r.stdout)[-400:])
    return out


def verify(job, prod, ref_head, want):
    d = dds_head(prod)
    bad = [k for k in ref_head if d[k] != ref_head[k]]
    if bad:
        die("DDS 头与基准不一致: %s" % bad)
    if os.path.getsize(prod) != job.expect:
        die("产物大小 %d != %d" % (os.path.getsize(prod), job.expect))
    raw = np.frombuffer(open(prod, "rb").read()[128:128 + job.target * job.target * 4], np.uint8)
    got = raw.reshape(job.target, job.target, 4)
    mae = float(np.abs(got[..., :3].astype(int) - want.astype(int)).mean())
    if mae != 0.0:
        die("mip0 与预期图 MAE=%.4f（应=0）" % mae)
    if not (got[..., 3] == 255).all():
        die("alpha 未全 255")


def apply_all(job, results):
    ref_head = dds_head(os.path.join(job.proj_tex, results[0][0] + ".dds"))
    for name, out, _, _, _ in results:
        dds = os.path.join(job.proj_tex, name + ".dds")
        tex = dds[:-4] + ".tex"
        if os.path.exists(tex):
            t = open(tex, encoding="utf-8", newline="").read()
            wh = (int(re.search(r"<m_Width>(\d+)</m_Width>", t).group(1)),
                  int(re.search(r"<m_Height>(\d+)</m_Height>", t).group(1)),
                  int(re.search(r"<m_NumMipMaps>(\d+)</m_NumMipMaps>", t).group(1)))
            if wh != (job.target, job.target, job.mips):
                die("%s .tex 声明 %s，与 target/mips 不符" % (name, wh))
        prod = make_dds(job, name, out)
        verify(job, prod, ref_head, out)
        old = sha16(dds)
        shutil.copy2(prod, dds)
        print("APPLY %-46s old=%s new=%s MAE=0 alpha=255" % (name, old, sha16(dds)))
    print("APPLY_DONE count=%d  ※ BLP 需重新 cook 并完整重启游戏" % len(results))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("mode", choices=["preview", "apply"], nargs="?", default="preview")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    job = Job(cfg)
    os.makedirs(job.work, exist_ok=True)

    results = [job.build(p) for p in job.parts]
    for part, out, cur, src, q in results:
        Image.fromarray(out).save(os.path.join(job.work, "refined_%s.png" % part))
        m0, m1 = metric(cur.astype(np.float32)), metric(out.astype(np.float32))
        print("\n[%s] anchor p5/p50/p95: %s -> %s"
              % (part, "/".join("%.1f" % x for x in q[0]), "/".join("%.1f" % x for x in q[1])))
        for tag, m in (("NOW", m0), ("NEW", m1)):
            print("  %-3s mean %5.1f  p5/p50/p95/p99 %5.1f/%5.1f/%5.1f/%5.1f"
                  "  >110 %5.2f%%  <25 %4.2f%%  sat %.3f  B-R %5.1f  hp %5.2f"
                  % (tag, m["mean"], m["p5"], m["p50"], m["p95"], m["p99"],
                     m["bright"], m["dark"], m["sat"], m["br"], m["hp"]))
        dm = m1["mean"] - m0["mean"]
        if abs(dm) > 3:
            print("  WARN 均值变化 %.1f 超出 ±3：实机会有明暗跳变，调 D5 锚点" % dm)
    save_sheet(results, os.path.join(job.work, "refined_compare.png"))
    print("\nPREVIEW " + os.path.join(job.work, "refined_compare.png"))
    if a.mode == "apply":
        apply_all(job, results)


if __name__ == "__main__":
    main()
