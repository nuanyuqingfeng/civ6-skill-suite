#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""bank 内「事件 → 动作 → 目标 → 声音 → 媒体」链路解析（通用）

用途：判断某个事件到底有没有进 bank、指向的是单 Sound 还是随机容器、容器里有几条声音、
媒体是否真的落在 DIDX/DATA 里。单位音效无声排查的第一站。

⚠️ 事件 ID 别自算：Wwise 的事件 ShortID = 小写事件名的 FNV-1 32 位
   （例 Play_RoverMale_Atk_01 → 2583211744）。本脚本优先从同目录的 <bank>.xml
   的 <Event Id=".." Name=".."/> 取 ID，取不到才回退哈希。

用法：
  python unit_bank_chain.py <x.bnk> [--xml <x.xml>] [--names A,B,C] [--json]
"""
import argparse
import json
import os
import re
import struct
import sys

TYPE = {1: 'Sound SFX?', 2: 'Sound', 3: 'Event', 4: 'Action', 5: 'RandomSequence',
        6: 'SwitchContainer', 7: 'ActorMixer', 8: 'Bus', 9: 'LayerContainer'}


def fnv1_lower(s):
    h = 0x811C9DC5
    for ch in s.lower().encode():
        h = (h * 0x01000193) & 0xFFFFFFFF
        h ^= ch
    return h


def load(bnk):
    d = open(bnk, 'rb').read()
    off, sec = 0, {}
    while off < len(d) - 8:
        fourcc = d[off:off + 4]
        size = struct.unpack('<I', d[off + 4:off + 8])[0]
        if fourcc.strip(b'\x00') not in (b'BKHD', b'DIDX', b'DATA', b'HIRC',
                                         b'STID', b'STMG', b'PLAT', b'ENVS', b'FXPR', b'BUSN'):
            break
        sec[fourcc] = (off + 8, size)
        off += 8 + size
    media = {}
    if b'DIDX' in sec:
        o, s = sec[b'DIDX']
        i = o
        while i < o + s:
            fid, fo, fs = struct.unpack('<III', d[i:i + 12])
            media[fid] = (fo, fs)
            i += 12
    objs = {}
    if b'HIRC' in sec:
        o, s = sec[b'HIRC']
        p = o
        n = struct.unpack('<I', d[p:p + 4])[0]
        p += 4
        for _ in range(n):
            t = d[p]
            sz = struct.unpack('<I', d[p + 1:p + 5])[0]
            oid = struct.unpack('<I', d[p + 5:p + 9])[0]
            objs[oid] = (t, d[p + 9:p + 9 + sz - 4])
            p += 9 + sz - 4
    return d, sec, media, objs


def actions_of(objs, ev_id):
    t, b = objs[ev_id]
    n = struct.unpack('<I', b[0:4])[0]
    return [struct.unpack('<I', b[4 + 4 * i:8 + 4 * i])[0] for i in range(n)]


def children(objs, oid):
    """在对象体里按 u32 扫描，找出指向已知 HIRC 对象的引用（用于容器子节点/声音媒体）"""
    t, b = objs[oid]
    out = []
    for i in range(0, len(b) - 4):
        v = struct.unpack('<I', b[i:i + 4])[0]
        if v in objs and v != oid:
            out.append(v)
    return out


def media_of(objs, media, oid):
    t, b = objs[oid]
    return sorted({m for m in media if struct.pack('<I', m) in b})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bnk')
    ap.add_argument('--xml')
    ap.add_argument('--names', default='')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    d, sec, media, objs = load(a.bnk)
    xml = a.xml
    if not xml:
        guess = os.path.splitext(a.bnk)[0] + '.xml'
        xml = guess if os.path.exists(guess) else None

    evmap = {}
    if xml and os.path.exists(xml):
        xs = open(xml, encoding='utf-8', errors='replace').read()
        evmap = {n: int(i) for i, n in re.findall(r'<Event Id="(\d+)" Name="([^"]+)"/>', xs)}

    names = [x for x in a.names.split(',') if x]
    if not names:
        names = sorted(evmap) or sorted(
            (fnv for fnv in []))
    if not names:
        names = ['(未提供事件名)']

    rows = []
    for name in names:
        eid = evmap.get(name) or fnv1_lower(name)
        row = dict(name=name, event_id=eid, in_bank=eid in objs, target_type=None,
                   sounds=0, media=0)
        if row['in_bank']:
            acts = actions_of(objs, eid)
            if acts:
                ab = objs[acts[0]][1]
                tgt = struct.unpack('<I', ab[2:6])[0]
                if tgt in objs:
                    tt = objs[tgt][0]
                    row['target_type'] = TYPE.get(tt, str(tt))
                    if tt == 2:
                        row['sounds'] = 1
                        row['media'] = len(media_of(objs, media, tgt))
                    else:
                        kids = sorted({c for c in children(objs, tgt) if objs[c][0] == 2})
                        row['sounds'] = len(kids)
                        row['media'] = len({m for k in kids for m in media_of(objs, media, k)})
        rows.append(row)

    if a.json:
        print(json.dumps(dict(bank=a.bnk, size=len(d), media_total=len(media),
                              objects=len(objs), events=rows), ensure_ascii=False, indent=1))
        return

    print('bank %s  %d B  media %d  HIRC objects %d' % (a.bnk, len(d), len(media), len(objs)))
    print('%-34s %-12s %-6s %-16s %6s %6s' % ('event', 'id', 'in_bank', 'target', 'sounds', 'media'))
    for r in rows:
        print('%-34s %-12s %-6s %-16s %6d %6d' % (
            r['name'], r['event_id'], 'Y' if r['in_bank'] else 'N',
            r['target_type'] or '-', r['sounds'], r['media']))


if __name__ == '__main__':
    main()
