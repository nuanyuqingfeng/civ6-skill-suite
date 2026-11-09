#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""unit_bank_resign.py -- 按名称派生 ShortID，解决「两个 mod 的 bank 同时加载」撞号。

口径同 mechanism.md §10 / voice_shortid.py：非 Event 对象的编号由
    FNV-1("<mod 目录名>/<资产名>") 位段算出，不靠 GUID、不靠随机、可用 --check 复算。
Event 不碰：其 ID = FNV-1(小写事件名)，引擎按名字重算，只能靠唯一命名区分。

用法：
  python unit_bank_resign.py <Wwise 工程目录> --project <mod 目录名> \
      [--exclude-bank <另一个 mod 的 .bnk> --exclude-glob "<游戏>/Base/.../*.bnk"] \
      [--rename-event 旧名:新名 ...] [--drop-event 事件名 ...] [--dry | --check]

  --exclude-* 只是兜底：把原版 / 其它 mod 已占用的 ID 加入避让集合（命中时按 §10.2 追加 /2 重算）。
  --check 只复算 .wwu 不写盘，异常数作退出码。
  重签后必须跑 wwise_wire.py <工程> --generate <BANK>，新编号才会进产物。

铁律：
  * 三个锚点 88602518 / 854467727 / 424381547 是 Stop_Leader_Speech 的寻址目标，跳过不改；
  * 显式 ShortID 必须 <= 2147483647，否则 Wwise 会换成随机值；
  * Event 编号由名字哈希决定，写死无效 —— 同名事件必须靠 --rename-event / --drop-event 处理；
  * Sound 与 AudioFileSource 常同名，主体键必须带类型前缀，否则两者会同号。
"""
import argparse
import glob
import os
import re
import sys
import uuid
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unit_bank_chain as ubc
import voice_shortid as vs

ANCHORS = (88602518, 854467727, 424381547)
TARGET_TAGS = ('Sound', 'AudioFileSource', 'RandomSequenceContainer',
               'ActorMixer', 'Action', 'SwitchContainer', 'BlendContainer')
GUID_RE = r'\{[0-9A-Fa-f-]{36}\}'
START_TAG_RE = re.compile(r'<([A-Za-z][A-Za-z0-9]*)\b([^>]*?)>')
SHORT_RE = re.compile(r'\s+ShortID="(\d+)"')
ID_RE = re.compile(r'\s+ID="(' + GUID_RE + r')"')
NAME_RE = re.compile(r'\s+Name="([^"]*)"')


def exclude_ids(banks):
    out = set(ANCHORS)
    for p in banks:
        try:
            _d, _sec, media, objs = ubc.load(p)
        except Exception as e:
            print('  [WARN] 跳过 %s: %s' % (p, e))
            continue
        out |= set(media)
        out |= set(objs)
        print('  [EXCLUDE] %-28s 对象 %4d / 媒体 %4d' %
              (os.path.basename(p), len(objs), len(media)))
    return out


def wwu_files(proj):
    out = []
    for sub in ('Actor-Mixer Hierarchy', 'Events', 'SoundBanks'):
        out.extend(sorted(glob.glob(os.path.join(proj, sub, '*.wwu'))))
    return out


def files_of(proj, sub):
    return sorted(glob.glob(os.path.join(proj, sub, '*.wwu')))


def role_asset(tag, name, event):
    """§10.2 主体键。Action 一律叫 Play/Pause，必须带事件名；Sound 与媒体源同名要分桶。"""
    if tag == 'Action':
        return 'action', (event or 'NoEvent') + '/' + name
    if tag == 'Sound':
        return 'sound', name
    if tag == 'AudioFileSource':
        return 'sound', 'afs/' + name
    return 'container', tag.lower() + '/' + name


def derive(project, asset, role, used, banned):
    """命名派生 + 冲突追加 /2 /3（口径同 voice_shortid.compute）。"""
    n = 1
    while True:
        key = asset if n == 1 else '%s/%d' % (asset, n)
        v = vs.compute(project, key, role)
        if v not in used and v not in banned:
            return v
        n += 1
        if n > 10000:
            raise RuntimeError('无法为 %s 找到唯一 ID' % asset)


def iter_targets(text):
    """按文档顺序产出 (起始, 属性串, tag, 期望主体键)，同时跟踪 Action 所属事件名。"""
    event = ''
    seen = {}
    for m in START_TAG_RE.finditer(text):
        tag, attrs = m.group(1), m.group(2)
        nm = NAME_RE.search(attrs)
        if tag == 'Event' and nm:
            event = nm.group(1)
            continue
        if tag not in TARGET_TAGS:
            continue
        idm = ID_RE.search(attrs)
        if not idm:
            continue
        name = nm.group(1) if nm else idm.group(1)
        role, asset = role_asset(tag, name, event)
        seen[(role, asset)] = seen.get((role, asset), 0) + 1
        if seen[(role, asset)] > 1:
            asset = '%s/%d' % (asset, seen[(role, asset)])
        yield m, attrs, idm, SHORT_RE.search(attrs), role, asset


def resign(proj, project, banned, dry, check=False):
    used = set()
    total = bad = 0
    for path in wwu_files(proj):
        text = open(path, encoding='utf-8', errors='replace').read()
        edits = []
        for m, attrs, idm, sm, role, asset in iter_targets(text):
            old = int(sm.group(1)) if sm else None
            if old in ANCHORS:
                continue
            v = derive(project, asset, role, used, banned)
            used.add(v)
            if check:
                if old != v:
                    bad += 1
                    if bad <= 8:
                        print('  [FAIL] %s %s 现为 %s 应为 %s' %
                              (os.path.basename(path), asset, old, v))
                continue
            if sm:
                new_attrs = attrs[:sm.start()] + ' ShortID="%d"' % v + attrs[sm.end():]
            else:
                new_attrs = attrs[:idm.end()] + ' ShortID="%d"' % v + attrs[idm.end():]
            edits.append((m.start(2), m.end(2), new_attrs))
        if check or not edits:
            continue
        for s, e, rep in reversed(edits):
            text = text[:s] + rep + text[e:]
        try:
            ET.fromstring(text)
        except ET.ParseError as ex:
            raise RuntimeError('%s 改后 XML 非法: %s' % (path, ex))
        if not dry:
            open(path, 'wb').write(text.encode('utf-8'))
        print('  [RESIGN] %-46s %3d 个对象' % (os.path.basename(path), len(edits)))
        total += len(edits)
    if check:
        print('[CHECK] 期望编号不符 %d 个' % bad)
        return bad
    print('[RESIGN] 共重签 %d 个 ShortID%s' % (total, '（预演）' if dry else ''))
    return total


def event_guids(proj, name):
    out = set()
    for p in files_of(proj, 'Events'):
        s = open(p, encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'<Event\s+Name="' + re.escape(name) + r'"\s+ID="(' + GUID_RE + r')"', s):
            out.add(m.group(1))
    return out


def rename_event(proj, old, new, dry):
    n = 0
    # Events 工作单元：只改 <Event Name>，Action 里指向 Sound 的 ObjectRef 保持原名
    for p in files_of(proj, 'Events'):
        s = open(p, encoding='utf-8', errors='replace').read()
        orig = s
        s = re.sub(r'(<Event\s+)Name="' + re.escape(old) + r'"',
                   lambda m: m.group(1) + 'Name="' + new + '"', s)
        if s != orig:
            _write_checked(p, s, dry)
            n += 1
            print('  [RENAME] %-38s Event %s -> %s' % (os.path.basename(p), old, new))
    # SoundBanks 工作单元：bank 引用按 GUID 解析，Name 同步改掉便于人工核对
    for p in files_of(proj, 'SoundBanks'):
        s = open(p, encoding='utf-8', errors='replace').read()
        orig = s
        s = re.sub(r'(<ObjectRef\s+)Name="' + re.escape(old) + r'"',
                   lambda m: m.group(1) + 'Name="' + new + '"', s)
        if s != orig:
            _write_checked(p, s, dry)
            n += 1
            print('  [RENAME] %-38s 引用 %s -> %s' % (os.path.basename(p), old, new))
    return n


def _write_checked(path, text, dry):
    try:
        ET.fromstring(text)
    except ET.ParseError as ex:
        raise RuntimeError('%s 改后 XML 非法: %s' % (path, ex))
    if not dry:
        open(path, 'wb').write(text.encode('utf-8'))


def drop_event(proj, name, dry):
    n = 0
    for p in files_of(proj, 'Events'):
        s = open(p, encoding='utf-8', errors='replace').read()
        orig = s
        s = re.sub(r'\s*<Event\s+Name="' + re.escape(name) + r'".*?</Event>',
                   '', s, flags=re.S)
        if s != orig:
            try:
                ET.fromstring(s)
            except ET.ParseError as ex:
                raise RuntimeError('%s 删事件后 XML 非法: %s' % (p, ex))
            if not dry:
                open(p, 'wb').write(s.encode('utf-8'))
            n += 1
            print('  [DROP] %-40s 删 Event %s' % (os.path.basename(p), name))
    for p in files_of(proj, 'SoundBanks'):
        s = open(p, encoding='utf-8', errors='replace').read()
        orig = s
        s = re.sub(r'\s*<ObjectRef\s+Name="' + re.escape(name) + r'"[^>]*/>', '', s)
        if s != orig:
            try:
                ET.fromstring(s)
            except ET.ParseError as ex:
                raise RuntimeError('%s 删引用后 XML 非法: %s' % (p, ex))
            if not dry:
                open(p, 'wb').write(s.encode('utf-8'))
            n += 1
            print('  [DROP] %-40s 删 bank 引用 %s' % (os.path.basename(p), name))
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('proj')
    ap.add_argument('--project', required=True, help='工程/mod 目录名，作为命名派生的唯一前缀')
    ap.add_argument('--exclude-bank', action='append', default=[])
    ap.add_argument('--exclude-glob', action='append', default=[],
                    help='通配符批量加入避让 bank（路径含空格时用这个）')
    ap.add_argument('--rename-event', action='append', default=[])
    ap.add_argument('--drop-event', action='append', default=[])
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--check', action='store_true', help='只复算 .wwu 编号，不写盘')
    a = ap.parse_args()
    project = a.project
    if not os.path.isdir(a.proj):
        print('[FAIL] 工程目录不存在: %s' % a.proj)
        return 1
    print('[BANK-RESIGN] %s  project=%s%s' %
          (a.proj, project, '（校验）' if a.check else '（预演）' if a.dry else ''))
    banks = list(a.exclude_bank)
    for g in a.exclude_glob:
        banks.extend(sorted(glob.glob(g)))
    banned = exclude_ids(banks)
    print('[EXCLUDE] 避让 ID 合计 %d 个' % len(banned))
    if a.check:
        return 1 if resign(a.proj, project, banned, dry=True, check=True) else 0
    for pair in a.rename_event:
        if ':' not in pair:
            print('[FAIL] --rename-event 需要 旧名:新名 -> %s' % pair)
            return 1
    # 先改名 / 删事件（避免重签后 GUID 映射混淆），再重签
    for pair in a.rename_event:
        old, new = pair.split(':', 1)
        if not rename_event(a.proj, old, new, a.dry):
            print('  [WARN] 未找到事件 %s' % old)
    for name in a.drop_event:
        if not drop_event(a.proj, name, a.dry):
            print('  [WARN] 未找到事件 %s' % name)
    resign(a.proj, project, banned, a.dry)
    return 0


if __name__ == '__main__':
    sys.exit(main())
