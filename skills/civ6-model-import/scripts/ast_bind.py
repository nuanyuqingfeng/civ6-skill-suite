#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""`.ast` 动画引用的解除与降级（四处容器同步处理）。

口径见 references/ast-anim-binding.md。核心：一段动画出现在四个容器里，
只删 `m_Animations` 是最常见的半吊子改法。

用法
----
  # 解除引用（四处都不出现，文件保留）
  python ast_bind.py --ast X.ast --code YYY --drop DeclareWarHuman,Defeat
  # 降级为 IDLE（槽位保留，改为播待机）
  python ast_bind.py --ast X.ast --code YYY --to-idle Warning
  # 只看会改什么
  python ast_bind.py --ast X.ast --code YYY --drop Defeat --dry-run

同一动画不能在 --drop 与 --to-idle 里同时出现（脚本会报错）。
"""
import argparse
import re
import sys

ELEMENT = re.compile(r"(?P<indent>[ \t]*)<Element>\n")


def section(text, tag):
    """返回 (start, end) 覆盖 <tag>...</tag> 的区间；找不到返回 None。"""
    m = re.search(r"<%s>\s*(.*?)\s*</%s>" % (tag, tag), text, re.S)
    return (m.start(1), m.end(1)) if m else None


def iter_blocks(body, indent):
    """按「顶层缩进 + <Element>」切块，返回 [(start, end)]（相对 body）。"""
    starts = [m.start() for m in re.finditer(r"^%s<Element>\n" % re.escape(indent),
                                             body, re.M)]
    out = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(body)
        out.append((s, e))
    return out


def detect_indent(body):
    m = re.search(r"^([ \t]*)<Element>\n", body, re.M)
    return m.group(1) if m else "\t\t\t\t\t"


def slot_of(block):
    m = re.search(r'<m_Name text="([^"]+)"/>', block)
    return m.group(1) if m else None


def anim_of(block):
    m = re.search(r'<m_AnimationName text="([^"]+)"/>', block)
    return m.group(1) if m else None


def rewrite_timelines(text, code, drop, to_idle):
    span = section(text, "m_timelines")
    if not span:
        return text, 0, set(), []
    s, e = span
    body = text[s:e]
    indent = detect_indent(body)
    kept, removed, removed_slots, retargeted = [], 0, set(), []
    for bs, be in iter_blocks(body, indent):
        block = body[bs:be]
        anim = anim_of(block)
        clip = anim.split("_", 1)[1] if anim and anim.startswith(code + "_") else None
        if clip in drop:
            removed += 1
            slot = slot_of(block)
            if slot:
                removed_slots.add(slot)
            continue
        if clip in to_idle:
            slot = slot_of(block)
            block = block.replace('<m_AnimationName text="%s"/>' % anim,
                                  '<m_AnimationName text="%s_IDLE"/>' % code, 1)
            retargeted.append(slot)
        kept.append(block)
    return text[:s] + "".join(kept) + text[e:], removed, removed_slots, retargeted


def rewrite_bindings(text, tag, slots_removed, code, drop, to_idle):
    span = section(text, tag)
    if not span:
        return text, 0
    s, e = span
    body = text[s:e]
    indent = detect_indent(body)
    kept, removed = [], 0
    for bs, be in iter_blocks(body, indent):
        block = body[bs:be]
        slot = re.search(r'<m_SlotName text="([^"]+)"/>', block)
        slot = slot.group(1) if slot else None
        if slot in slots_removed:
            removed += 1
            continue
        anim = anim_of(block)
        clip = anim.split("_", 1)[1] if anim and anim.startswith(code + "_") else None
        if clip in drop:
            removed += 1
            continue
        if clip in to_idle and anim:
            block = block.replace('<m_AnimationName text="%s"/>' % anim,
                                  '<m_AnimationName text="%s_IDLE"/>' % code, 1)
        kept.append(block)
    return text[:s] + "".join(kept) + text[e:], removed


def rewrite_animations(text, code, drop):
    span = section(text, "m_Animations")
    if not span:
        return text, 0
    s, e = span
    body = text[s:e]
    removed = 0
    for clip in drop:
        pat = r'\s*<Element text="%s_%s"/>' % (re.escape(code), re.escape(clip))
        body, n = re.subn(pat, "", body)
        removed += n
    return text[:s] + body + text[e:], removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ast", required=True)
    ap.add_argument("--code", required=True)
    ap.add_argument("--drop", default="", help="逗号分隔的片段后缀，解除引用")
    ap.add_argument("--to-idle", default="", help="逗号分隔的片段后缀，降级为 IDLE")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    drop = {x.strip() for x in args.drop.split(",") if x.strip()}
    to_idle = {x.strip() for x in args.to_idle.split(",") if x.strip()}
    overlap = drop & to_idle
    if overlap:
        print("CONFLICT 同一动画不能既 drop 又 to-idle:", ", ".join(sorted(overlap)))
        return 2
    if not drop and not to_idle:
        print("ENV_FAIL 至少给 --drop 或 --to-idle")
        return 2

    text = open(args.ast, encoding="utf-8").read()
    before_anims = len(re.findall(r"<m_AnimationName ", text))
    before_slots = len(re.findall(r"<m_SlotName ", text))

    text, tl_removed, removed_slots, retargeted = rewrite_timelines(
        text, args.code, drop, to_idle)
    text, tlb_removed = rewrite_bindings(text, "m_timelineBindings",
                                         removed_slots, args.code, drop, to_idle)
    text, ab_removed = rewrite_bindings(text, "m_animationBindings",
                                        removed_slots, args.code, drop, to_idle)
    text, am_removed = rewrite_animations(text, args.code, drop)

    after_anims = len(re.findall(r"<m_AnimationName ", text))
    after_slots = len(re.findall(r"<m_SlotName ", text))

    print("AST_BIND code=%s drop=%s to_idle=%s" %
          (args.code, sorted(drop) or "-", sorted(to_idle) or "-"))
    print("  timelines removed=%d retargeted=%d" % (tl_removed, len(retargeted)))
    print("  timelineBindings removed=%d  animationBindings removed=%d  assets removed=%d"
          % (tlb_removed, ab_removed, am_removed))
    print("  m_AnimationName  %d -> %d" % (before_anims, after_anims))
    print("  m_SlotName       %d -> %d" % (before_slots, after_slots))

    if args.dry_run:
        print("DRY_RUN 未写回")
        return 0

    try:
        import xml.etree.ElementTree as ET
        ET.fromstring(text)
    except Exception as e:
        print("XML_INVALID 改写后不再是合法 XML，已放弃写回:", e)
        return 1

    open(args.ast, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE", args.ast)
    return 0


if __name__ == "__main__":
    sys.exit(main())
