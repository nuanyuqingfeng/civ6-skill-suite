#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""烤后 BLP 内「时间线触发点」校验（通用）

.ast 的触发点会以 FNV1a-32 小端的形式烤进 **单位资产 BLP**，命中次数 = 该事件在资产里
被挂了几处。改完 .ast 但忘了 cook、或 cook 没吃到新 ast 时，这里的计数会露馅。

⚠ 只认 `<Mods>/<Mod>/Platforms/Windows/BLPs/<units 等分类>/<unit>.blp` 这一层（整个单位资产）。
  同目录树里的 `SHARED_DATA/ANIMATION_<timeline>` 只是裸动画剪辑，**不含任何触发点**
  （实测：改 .ast 触发点前后该文件逐字节相同，字符串表里也没有 Trigger 类字段），
  拿它校验会得到全 0 的假阴性。

用法：
  python unit_blp_check.py <x.blp> --names Play_X_A,Play_X_B [--json]
  python unit_blp_check.py <x.blp> --expect expect.json    # {"Play_X_A": 2, ...} 逐项判定
"""
import argparse
import json
import os
import struct
import time


def fnv1a(s):
    h = 0x811C9DC5
    for ch in s.encode():
        h ^= ch
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def count(hay, name):
    return hay.count(struct.pack('<I', fnv1a(name)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('blp')
    ap.add_argument('--names', default='')
    ap.add_argument('--expect', help='JSON: {事件名: 期望命中次数}')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    hay = open(a.blp, 'rb').read()
    names = [x for x in a.names.split(',') if x]
    expect = {}
    if a.expect:
        expect = json.load(open(a.expect, encoding='utf-8'))
        names = names or list(expect)

    rows = []
    ok = True
    for n in names:
        c = count(hay, n)
        row = dict(name=n, hits=c)
        if n in expect:
            row['expect'] = expect[n]
            row['pass'] = (c == expect[n])
            ok = ok and row['pass']
        rows.append(row)

    if a.json:
        print(json.dumps(dict(blp=a.blp, size=len(hay), rows=rows, pass_=ok),
                         ensure_ascii=False, indent=1))
        return

    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(a.blp)))
    print('blp %s  %d B  mtime %s' % (a.blp, len(hay), ts))
    for r in rows:
        if 'expect' in r:
            print('  %-34s hits %-3d expect %-3d %s' % (
                r['name'], r['hits'], r['expect'], 'PASS' if r['pass'] else 'FAIL'))
        else:
            print('  %-34s hits %d' % (r['name'], r['hits']))
    if expect:
        print('\n%s' % ('PASS 全部符合' if ok else 'FAIL 存在不符项'))


if __name__ == '__main__':
    main()
