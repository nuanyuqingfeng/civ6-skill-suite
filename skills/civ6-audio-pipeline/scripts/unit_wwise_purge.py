#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 Wwise 工作单元（.wwu）里按名字正则删除对象块。

用途：重建语音池前清掉上一版的 Sound / RandomSequenceContainer / Event 残留，
否则孤儿对象会被 SoundBank 的整工作单元引用拉进 bank，撞上评估版
"每 bank ≤200 媒体项"的硬上限（实测 209/200 直接 Fatal）。

删除范围只认**完整对象块**（含嵌套），不会动其他对象；删完后请用
`wwise_wire.py --generate` 重新生成，再用 `unit_bank_chain.py` 验收。

用法：
  python unit_wwise_purge.py <a.wwu> [<b.wwu> ...] --match "Play_X_CH_" [--match ...] [--dry]

  --match 可以是正则，匹配对象 Name 属性；可多次给出。
"""
import argparse
import re
import sys

TAGS = ("Sound", "RandomSequenceContainer", "Event", "ActorMixer", "BlendContainer",
        "SwitchContainer", "MusicSegment", "MusicPlaylistContainer", "SoundSFX")


def blocks(text, tag):
    """按深度返回 [(start, end, name)]，含嵌套同名标签。"""
    out = []
    pat = re.compile(r"<(%s)\b[^>]*\bName=\"([^\"]*)\"" % tag)
    for m in pat.finditer(text):
        start = m.start()
        # 跳过属性里可能的 '>'，从标签结束处开始计深度
        depth = 0
        pos = m.start()
        for t in re.finditer(r"</?%s\b" % tag, text[start:]):
            if t.group(0).startswith("</"):
                depth -= 1
            else:
                depth += 1
            if depth == 0:
                end = start + t.end()
                end = text.find(">", end) + 1
                out.append((start, end, m.group(2)))
                break
    return out


def purge(path, patterns, dry=False, quiet=False):
    text = open(path, encoding="utf-8").read()
    spans = []
    for tag in TAGS:
        for s, e, name in blocks(text, tag):
            if any(p.search(name) for p in patterns):
                spans.append((s, e, tag, name))
    # 去重叠：外层块包含内层块时只保留外层
    spans.sort()
    merged = []
    for s, e, tag, name in spans:
        if merged and s < merged[-1][1]:
            continue
        merged.append((s, e, tag, name))
    if dry:
        for s, e, tag, name in merged:
            print("  would delete %-22s %s" % (tag, name))
        if not quiet:
            print("%s: %d blocks (dry)" % (path, len(merged)))
        return len(merged)
    for s, e, tag, name in reversed(merged):
        text = text[:s] + text[e:]
    # 折叠删除后留下的连续空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    open(path, "w", encoding="utf-8", newline="\n").write(text)
    if not quiet:
        print("%s: deleted %d blocks" % (path, len(merged)))
    return len(merged)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wwu", nargs="+")
    ap.add_argument("--match", action="append", required=True)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    pats = [re.compile(p) for p in a.match]
    n = 0
    for p in a.wwu:
        n += purge(p, pats, a.dry)
    print("total", n)


if __name__ == "__main__":
    main()
