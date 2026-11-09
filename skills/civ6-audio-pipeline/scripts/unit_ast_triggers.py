#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""单位 .ast 时间线触发点读写（通用）

单位音效的接入点是「时间线 -> 触发点 -> Wwise 事件」，本脚本只做这一层的读与写，
不碰 bank、不碰 Wwise 工程。

用法：
  python unit_ast_triggers.py <x.ast> --list
  python unit_ast_triggers.py <x.ast> --clear-all [--keep RUN_A,RUN_COMBAT] [--dry]
  python unit_ast_triggers.py <x.ast> --set map.json [--dry]
  python unit_ast_triggers.py <x.ast> --add map.json [--dry]
  python unit_ast_triggers.py <x.ast> --dur dur.json [--dry]

map.json 形如： {"HERO_A": [["Play_X_Probe", 0.4]], "ATTACK_1": [["Play_X_Atk_01", 0.2]]}
  --set  该时间线的触发点整体替换为给定条目（列表为空 = 清空该时间线）
  --add  在已有触发点后追加（同事件+同时刻已存在则跳过，幂等）
  --dur  改时间线总长： {"HERO_A": 2.9}
         时长只是状态停留长度，不必等于动画剪辑长度（原工程 VICTORY 男女 10.033/5.800
         就是手工值）；语音比剪辑长时拉长它，比截断语音或变速更自然。

注意：
  * 单个触发点的 XML 结构固定为 m_eType/m_Name/m_Description/m_FXName/... 十字段，
    m_fDuration 一律 0.000000，m_nTrackIndex 一律 0（写错会导致 cook 报警或静默丢失）。
  * 时间线的 m_fDuration 是动画时长，触发点 m_fStartTime 必须小于它，否则永远求值不到。
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

TL_PAT = re.compile(
    r'<Element>\s*<m_Name text="([^"]+)"/>\s*<m_Description text="[^"]*"/>\s*'
    r'<m_AnimationName text="([^"]*)"/>\s*<m_fDuration>([\d.]+)</m_fDuration>')

TRIG_FIELDS = (
    ('m_eType', 'SOUND'),
    ('m_FXName', None),          # 事件名，占位
    ('m_fStartTime', None),      # 秒，占位
)


def scan(s):
    """返回 [dict(name, anim, dur, trig, start, tracks_pos)]"""
    out = []
    for m in TL_PAT.finditer(s):
        name, anim, dur = m.group(1), m.group(2), m.group(3)
        end = s.find('<m_Tracks>', m.end())
        if end < 0:
            continue
        body = s[m.end():end]
        trig = re.findall(
            r'<m_FXName text="([^"]*)"/>.*?<m_fStartTime>([\d.]+)</m_fStartTime>', body, re.S)
        out.append(dict(name=name, anim=anim, dur=float(dur),
                        trig=[(e, float(t)) for e, t in trig],
                        start=m.start(), end=end))
    return out


def render_triggers(items, indent='\t' * 12):
    if not items:
        return indent + '<m_Triggers/>'
    inner = indent + '\t'
    fld = inner + '\t'
    lines = [indent + '<m_Triggers>']
    for idx, (ev, t) in enumerate(items, 1):
        lines += [
            inner + '<Element>',
            fld + '<m_eType>SOUND</m_eType>',
            fld + '<m_Name text="%d"/>' % idx,
            fld + '<m_Description text=""/>',
            fld + '<m_FXName text="%s"/>' % ev,
            fld + '<m_CollectionName text=""/>',
            fld + '<m_AttachmentPointName text=""/>',
            fld + '<m_fStartTime>%.6f</m_fStartTime>' % t,
            fld + '<m_fDuration>0.000000</m_fDuration>',
            fld + '<m_nTrackIndex>0</m_nTrackIndex>',
            inner + '</Element>',
        ]
    lines.append(indent + '</m_Triggers>')
    return '\n'.join(lines)


def replace_block(s, tl, items, mode):
    """把单个时间线的 <m_Triggers> 区块替换/追加。返回新整串与被替换的旧条目。"""
    region = s[tl['start']:tl['end']]
    m = re.search(r'(?:\t*)<m_Triggers/>|(?:\t*)<m_Triggers>.*?</m_Triggers>', region, re.S)
    if not m:
        raise SystemExit('时间线 %s 找不到 <m_Triggers> 区块' % tl['name'])
    old_indent = re.match(r'\t*', m.group(0)).group(0)
    indent = old_indent if old_indent else '\t' * 12
    if mode == 'set':
        items = list(items)
    else:
        items = list(tl['trig'] ) + [i for i in items if i not in tl['trig']]
    region2 = region[:m.start()] + render_triggers(items, indent) + region[m.end():]
    return s[:tl['start']] + region2 + s[tl['end']:], items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ast')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--clear-all', action='store_true')
    ap.add_argument('--keep', default='', help='--clear-all 时保留的时间线，逗号分隔')
    ap.add_argument('--set', dest='set_map')
    ap.add_argument('--add', dest='add_map')
    ap.add_argument('--dur', dest='dur_map', help='改时间线总长 json: {"HERO_A": 2.9}')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()

    s = open(a.ast, encoding='utf-8').read()
    tls = scan(s)
    if not tls:
        raise SystemExit('未解析到任何时间线，确认是单位 .ast 而不是别的 ast')

    # 时长调整要先做：它会改变字符偏移，之后重新 scan 再处理触发点
    dur_map = json.load(open(a.dur_map, encoding='utf-8')) if a.dur_map else {}
    if dur_map:
        by_name0 = {t['name']: t for t in tls}
        miss = [k for k in dur_map if k not in by_name0]
        if miss:
            raise SystemExit('这些时间线在 ast 里不存在: %s' % miss)
        for name in sorted(dur_map, key=lambda n: -by_name0[n]['start']):
            tl = by_name0[name]
            seg = s[tl['start']:tl['end']]
            seg2, n = re.subn(r'<m_fDuration>[\d.]+</m_fDuration>',
                              '<m_fDuration>%.6f</m_fDuration>' % float(dur_map[name]),
                              seg, count=1)
            if n != 1:
                raise SystemExit('时间线 %s 找不到 m_fDuration' % name)
            s = s[:tl['start']] + seg2 + s[tl['end']:]
        if not a.dry:
            open(a.ast, 'w', encoding='utf-8', newline='').write(s)
        print('\n%s %s' % ('[dry]' if a.dry else '[写入]', a.ast))
        for name in sorted(dur_map):
            print('  %-18s 时长 %.3f -> %.3f' % (name, by_name0[name]['dur'], float(dur_map[name])))
        tls = scan(s)

    if a.list or not (a.clear_all or a.set_map or a.add_map):
        print('%-18s %-26s %8s  %s' % ('timeline', 'animation', 'dur', 'triggers'))
        for t in tls:
            tr = ', '.join('%s@%.3g' % (e, x) for e, x in t['trig']) or '-'
            print('%-18s %-26s %8.3f  %s' % (t['name'], t['anim'], t['dur'], tr))
        print('\n时间线 %d 条，带触发点 %d 条' % (len(tls), sum(1 for t in tls if t['trig'])))
        if not (a.clear_all or a.set_map or a.add_map):
            return

    # 目标
    plan = {}
    if a.clear_all:
        keep = set(x for x in a.keep.split(',') if x)
        for t in tls:
            plan[t['name']] = ('set', [] if t['name'] not in keep else t['trig'])
    if a.set_map:
        for k, v in json.load(open(a.set_map, encoding='utf-8')).items():
            plan[k] = ('set', [(e, float(x)) for e, x in v])
    if a.add_map:
        for k, v in json.load(open(a.add_map, encoding='utf-8')).items():
            plan[k] = ('add', [(e, float(x)) for e, x in v])

    by_name = {t['name']: t for t in tls}
    missing = [k for k in plan if k not in by_name]
    if missing:
        raise SystemExit('这些时间线在 ast 里不存在: %s' % missing)

    # 从后往前替换，避免偏移错位
    changed = []
    for name in sorted(plan, key=lambda n: -by_name[n]['start']):
        mode, items = plan[name]
        tl = by_name[name]
        for ev, t in items:
            if t >= tl['dur']:
                print('  [警告] %s 触发点 %.3fs 超过动画时长 %.3fs，将永远不触发'
                      % (name, t, tl['dur']))
        s, final = replace_block(s, tl, items, mode)
        changed.append((name, final))

    if not a.dry:
        try:
            root_before = ET.fromstring(open(a.ast, encoding='utf-8').read())
            root_after = ET.fromstring(s)
        except ET.ParseError as e:
            raise SystemExit('XML 校验失败，未写入：%s' % e)
        if root_before.tag != root_after.tag:
            raise SystemExit('根节点不一致，未写入')
        open(a.ast, 'w', encoding='utf-8', newline='').write(s)

    print('\n%s %s' % ('[dry]' if a.dry else '[写入]', a.ast))
    for name, final in changed:
        tr = ', '.join('%s@%.3g' % (e, x) for e, x in final) or '(空)'
        print('  %-18s -> %s' % (name, tr))


if __name__ == '__main__':
    main()
