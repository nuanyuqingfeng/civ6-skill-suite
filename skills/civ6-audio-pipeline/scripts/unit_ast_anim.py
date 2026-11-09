#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""unit_ast_anim.py — 单位 .ast 的「槽位 → 动画」映射读写 / 槽位移除

背景（2026-11-05 实测）：
  原版通用 DSG `potential_any_graph` 的 IDLE / IDLE_COMBAT / REACT_RANGED /
  IDLE_FORTIFY 状态是双层结构：Normal 基础层请求 `BREATHING_A` /
  `BREATHING_COMBAT_A`（全局通用细微呼吸动画），Additive 叠加层请求
  `IDLE_*` / `IDLE_COMBAT_*`。原版单位 .ast **不定义** BREATHING 槽，
  基础层回落到全局呼吸动画，只叠一份姿势。

  自定义单位若在 .ast 里补了 BREATHING 槽并指向自己的完整待机动画，
  基础层就被劫持成完整姿势，与 Additive 层叠加 → 固定抬手姿势、
  躯干错位、观感不协调。修法是移除这些槽，让引擎回落全局默认值。

用法：
  python unit_ast_anim.py <x.ast> --list [--animdir <Animations 目录>]
  python unit_ast_anim.py <x.ast> --drop BREATHING_A [更多槽...] [--dry]
  python unit_ast_anim.py <x.ast> --set map.json [--animdir <dir>] [--dry]

map.json：
  {"IDLE_COMBAT_A": "roverunit_IDLE_A"}                  # 时长自动取 .anm
  {"IDLE_COMBAT_A": ["roverunit_IDLE_A", 4.033334]}      # 显式给时长

--set 会同步改写 m_behaviorDataSets/m_animationBindings 里的同名槽位
（编辑器映射表，不决定播放，但保持一致以免误导）。

--drop 会删除该槽的三处定义：
  m_timelines/m_Timelines 的 Element（含嵌套 m_Tracks，需配平）
  m_animationBindings 的 Element
  m_timelineBindings   的 Element
"""
import re
import os
import json
import argparse
import xml.etree.ElementTree as ET

TL_TPL = (r'<m_Name text="%s"/>\s*<m_Description text="[^"]*"/>\s*'
          r'<m_AnimationName text=")[^"]*("/>\s*<m_fDuration>)[\d.]+(</m_fDuration>)')
BIND_TPL = r'<m_SlotName text="%s"/>\s*<m_AnimationName text=")[^"]*(">)'


def timelines(text):
    pat = re.compile(
        r'<m_Name text="([^"]+)"/>\s*<m_Description text="[^"]*"/>\s*'
        r'<m_AnimationName text="([^"]*)"/>\s*<m_fDuration>([\d.]+)</m_fDuration>')
    return [(m.group(1), m.group(2), float(m.group(3))) for m in pat.finditer(text)]


def clip_dur(animdir, anim):
    if not animdir:
        return None
    p = os.path.join(animdir, anim + '.anm')
    if not os.path.exists(p):
        return None
    m = re.search(r'<m_fDuration>([\d.]+)</m_fDuration>',
                  open(p, encoding='utf-8', errors='ignore').read())
    return float(m.group(1)) if m else None


def set_slot(text, slot, anim, dur):
    tl = re.compile(TL_TPL % re.escape(slot))
    new = tl.sub(lambda m: m.group(1) + anim + m.group(2) + ('%.6f' % dur) + m.group(3), text)
    if new == text:
        raise SystemExit('%s: 时间线未替换（匹配 0 处），已中止' % slot)
    bd = re.compile(BIND_TPL % re.escape(slot))
    new = bd.sub(lambda m: m.group(1) + anim + m.group(2), new)
    return new


def elem_end(text, start):
    """start 指向某个 '<Element>'；返回与之配平的 '</Element>' 之后的位置。
    时间线 Element 内含 <m_Tracks><Element>…</Element></m_Tracks>，必须配平。"""
    depth = 0
    for m in re.finditer(r'<Element>|</Element>', text[start:]):
        if m.group(0) == '<Element>':
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return start + m.end()
    return None


def drop_slot(text, slot):
    """删除一个槽的三处定义，返回 (新文本, 删掉的绑定 Element 数)。"""
    m = re.search(r'(?m)^[ \t]*<Element>\s*<m_Name text="%s"/>' % re.escape(slot), text)
    if not m:
        raise SystemExit('%s: 时间线 Element 未找到，已中止' % slot)
    st = m.start()
    first = text.index('<Element>', st)
    en = elem_end(text, first)
    if en is None:
        raise SystemExit('%s: 时间线 Element 标签未配平，已中止' % slot)
    text = text[:st] + text[en:].lstrip('\r\n')

    # animationBindings / timelineBindings 的 Element 无嵌套，非贪婪即可
    pat = re.compile(
        r'(?m)^[ \t]*<Element>\s*<m_SlotName text="%s"/>.*?</Element>[ \t]*\r?\n?'
        % re.escape(slot), re.S)
    text, nb = pat.subn('', text)
    return text, nb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ast')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--set', dest='set_map')
    ap.add_argument('--drop', nargs='+', metavar='SLOT')
    ap.add_argument('--animdir')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()

    s = open(a.ast, encoding='utf-8').read()
    tls = timelines(s)
    if not tls:
        raise SystemExit('未解析到任何时间线，确认是单位 .ast')
    cur = {n: (an, d) for n, an, d in tls}

    if a.list or not (a.set_map or a.drop):
        print('%-20s %-30s %9s %9s' % ('slot', 'animation', 'ast.dur', 'clip.dur'))
        for n, an, d in tls:
            cd = clip_dur(a.animdir, an)
            flag = '  <<< 与剪辑不一致' if (cd is not None and abs(cd - d) > 1e-3) else ''
            print('%-20s %-30s %9.3f %9s%s'
                  % (n, an, d, ('%.3f' % cd) if cd is not None else '-', flag))
        return

    if a.drop:
        miss = [k for k in a.drop if k not in cur]
        if miss:
            raise SystemExit('这些槽位不在 ast 里：%s' % ', '.join(miss))
        before_tl = len(tls)
        before_bd = len(re.findall(r'<m_SlotName text="', s))
        for slot in a.drop:
            s, nb = drop_slot(s, slot)
            print('移除槽 %-22s 绑定 Element %d 个' % (slot, nb))
        after_tl = len(timelines(s))
        after_bd = len(re.findall(r'<m_SlotName text="', s))
        print('时间线 %d -> %d，槽位绑定 %d -> %d'
              % (before_tl, after_tl, before_bd, after_bd))
        if after_tl != before_tl - len(a.drop) or after_bd != before_bd - 2 * len(a.drop):
            raise SystemExit('删除数量不符合预期，已中止（未写盘）')
        # .ast 里还有 <Element text="..."/> 这类带属性写法，简单计数天然不配平；
        # 用真正的 XML 解析判断结构是否被改坏。
        try:
            ET.fromstring(s)
        except Exception as ex:
            raise SystemExit('XML 结构校验失败，已中止（未写盘）: %s' % ex)
        if a.dry:
            print('（dry run，未写盘）')
            return
        open(a.ast, 'w', encoding='utf-8', newline='').write(s)
        print('已写入 %s' % a.ast)
        return

    spec = json.load(open(a.set_map, encoding='utf-8'))
    miss = [k for k in spec if k not in cur]
    if miss:
        raise SystemExit('这些槽位不在 ast 里：%s' % ', '.join(miss))

    for slot, val in spec.items():
        if isinstance(val, str):
            anim, dur = val, clip_dur(a.animdir, val)
            if dur is None:
                raise SystemExit('%s: 找不到 %s.anm 的时长，请显式给 ["动画", 时长]' % (slot, val))
        else:
            anim, dur = val[0], float(val[1])
        oa, od = cur[slot]
        print('%-20s %s (%.3f) -> %s (%.3f)' % (slot, oa, od, anim, dur))
        if not a.dry:
            s = set_slot(s, slot, anim, dur)

    if a.dry:
        print('（dry run，未写盘）')
        return
    open(a.ast, 'w', encoding='utf-8', newline='').write(s)
    print('已写入 %s' % a.ast)


if __name__ == '__main__':
    main()
