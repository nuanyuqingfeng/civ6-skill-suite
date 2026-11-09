#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一个事件、多档加权语音池（嵌套随机容器法，Wwise 2015.x 通用）

背景
----
Wwise 2015.1 的 RandomSequenceContainer 只有「均匀随机」，子项没有权重字段。
想让「语气词占大部分、技能/大招占小部分」，用**槽位数量当权重**：

    父容器（随机）
      ├─ 语气词组 × 26   ← 26/30 = 86.7%
      ├─ 技能组   × 3    ←  3/30 = 10.0%
      └─ 大招组   × 1    ←  1/30 =  3.3%

每条语音的命中率 = 组占比 ÷ 组内条数，所以组内条目越多，单条越稀有。
父容器和组容器都设 MaxSoundPerInstance=1，避免同一次攻击叠两条语音。

为什么不用 DSG / 多槽位
----------------------
实测（见 references/unit-audio.md）：本工程单位的常态攻击只有 ATTACK_A 一条槽
会被引擎请求；ATTACK_1/2/3、VICTORY、ACTION_1 是死槽；改 DSG 图也不会改变
引擎请求哪个状态。所以概率只能在同一事件内部做。

注意 HERO_A / HERO_1 **不是**死槽——它们是突进终结技的战斗变体，会偶发被请求。
正确做法是让它们挂**同一个池**（而不是单条固定语音），并把这两个槽的时间线动画
改回 *_ATTACK_A；否则会出现「偶尔一句固定台词 + 一个固定抬手动作」。

spec.json
---------
{
  "project":  "<Wwise 工程根>",
  "am_wu":    "Actor-Mixer Hierarchy/LeaderSpeech_Feline.wwu",
  "ev_wu":    "Events/RoverUnitAudio_Events.wwu",
  "bank_wu":  "SoundBanks/RoverUnitAudio_Banks.wwu",
  "template_sound":     "Play_RoverMale_Atk_01",      // 单个 Sound（含 AudioFileSource）
  "template_container": "RoverMale_Atk_01_Random",     // 随机容器（RandomOrSequence=1）
  "template_event":     "Play_RoverMale_Victory",      // 单 Action 的 Event
  "root":   "RoverMale_VoicePool",                     // 父容器名
  "event":  "Play_RoverMale_VoicePool",                // 对外事件名
  "hero":   {"event": "Play_RoverMale_Ult", "group": "UL"},  // 可选：HERO 槽专用事件
  "lufs":   -21,
  "groups": [
    {"name": "CH", "slots": 26, "entries": [{"src": "...wav", "name": "Play_RoverMale_CH_001"}, ...]},
    {"name": "SK", "slots": 3,  "entries": [...]},
    {"name": "UL", "slots": 1,  "entries": [...]}
  ]
}

用法
----
  python unit_voice_mixer.py spec.json [--force] [--no-render] [--dry]
                           [--unregister Play_X_A,Play_X_B]
  --force      同名父容器/事件已存在时先删再建（重建池的标准姿势）
  --unregister 从 SoundBank 的 ObjectInclusionList 里摘掉旧事件
  # 之后用 wwise_wire.py <工程> --generate <BANK名> 重建 bank
  # ⚠ 事件重建会让 GUID 变化，本脚本会自动校正 bank 里的 ObjectRef GUID；
  #   生成后必须用 unit_bank_chain.py 确认目标事件出现在清单里（媒体数正常不代表事件进包）
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unit_voice_pool import (render, probe_dur, guid, used_shortids,
                             make_shortids, clone_sound, clone_event, find_block)
import xml.etree.ElementTree as ET


def container_block(text, name):
    """按名字取整块 RandomSequenceContainer（含闭合标签）。"""
    i = text.find('<RandomSequenceContainer Name="%s"' % name)
    if i < 0:
        return None
    depth = 0
    for m in re.finditer(r'</?RandomSequenceContainer\b', text[i:]):
        depth += -1 if m.group(0).startswith('</') else 1
        if depth == 0:
            return text[i:i + m.end() + 1]
    return None


def children_span(s):
    """定位容器自己的 <ChildrenList>…</ChildrenList>。

    ⚠️ 不能用 str.index 找闭合标签：容器里的每个 Sound 自己还有一层
    <ChildrenList>（放 AudioFileSource），第一个 </ChildrenList> 是内层的，
    照它截会把后面的 Sound 留在原地、结构直接坏掉。
    """
    i = s.index('<ChildrenList>')
    depth = 0
    for m in re.finditer(r'</?ChildrenList>', s[i:]):
        depth += -1 if m.group(0).startswith('</') else 1
        if depth == 0:
            return i, i + m.end()
    raise ValueError('ChildrenList 未闭合')


def rebuild_container(tpl, new_name, sid, children_xml):
    """克隆容器模板：换名/换 GUID/换 ShortID，替换 ChildrenList 内容。"""
    s = tpl
    s = re.sub(r'(<RandomSequenceContainer Name=")[^"]*(" ID=")\{[0-9A-F-]+\}(" ShortID=")\d+(")',
               lambda m: m.group(1) + new_name + m.group(2) + guid() +
                         m.group(3) + str(sid) + m.group(4), s, count=1)
    i, j = children_span(s)
    return s[:i] + '<ChildrenList>\n' + children_xml + '\n</ChildrenList>' + s[j:]


def chunk(entries, n):
    """轮转分配，保证每组内容都打散（避免连续同源）。"""
    n = max(1, min(n, len(entries)))
    out = [[] for _ in range(n)]
    for k, e in enumerate(entries):
        out[k % n].append(e)
    return [c for c in out if c]


def register_events_to_bank(bank_path, ev_text, names):
    bank = open(bank_path, encoding='utf-8').read()
    wu_id = re.search(r'<WorkUnit [^>]*ID="(\{[0-9A-F-]+\})"', ev_text).group(1)
    added, fixed = [], []
    for name in names:
        g = re.search(r'<Event Name="%s" ID="(\{[0-9A-F-]+\})"' % re.escape(name), ev_text)
        if not g:
            raise SystemExit('Events 里找不到事件定义: %s' % name)
        exists = re.search(r'<ObjectRef Name="%s" ID="(\{[0-9A-F-]+\})"[^\n]*/>' % re.escape(name), bank)
        if exists:
            # --force 重建后事件 GUID 会变，旧 ObjectRef 指向已消失的对象 → 包不进 bank，
            # 且 Wwise 不报错。必须把 ID 改成新事件的实际 GUID。
            if exists.group(1) != g.group(1):
                bank = bank.replace(exists.group(0), exists.group(0).replace(
                    exists.group(1), g.group(1)))
                fixed.append(name)
            continue
        m = re.search(r'(\t*)<ObjectRef [^\n]*/>\s*\n(\t*)</ObjectInclusionList>', bank)
        if not m:
            raise SystemExit('bank 里找不到 ObjectInclusionList')
        line = '%s<ObjectRef Name="%s" ID="%s" WorkUnitID="%s" Filter="7" Origin="Manual"/>\n' % (
            m.group(1), name, g.group(1), wu_id)
        bank = bank[:m.start(2)] + line + bank[m.start(2):]
        added.append(name)
    return bank, added, fixed


def unregister_events_from_bank(bank_path, names):
    bank = open(bank_path, encoding='utf-8').read()
    removed = []
    for name in names:
        pat = re.compile(r'[ \t]*<ObjectRef Name="%s"[^\n]*/>\n' % re.escape(name))
        if pat.search(bank):
            bank = pat.sub('', bank)
            removed.append(name)
    return bank, removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('--no-render', action='store_true')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--unregister', default='', help='从 bank 里摘掉的旧事件名，逗号分隔')
    ap.add_argument('--force', action='store_true',
                    help='同名父容器/事件已存在时先删除再重建（重建池的常用姿势）')
    a = ap.parse_args()

    spec = json.load(open(a.spec, encoding='utf-8'))
    root_dir = spec['project']
    amp = os.path.join(root_dir, spec['am_wu'])
    evp = os.path.join(root_dir, spec['ev_wu'])
    am = open(amp, encoding='utf-8').read()
    ev = open(evp, encoding='utf-8').read()

    root_name, ev_name = spec['root'], spec['event']
    hero = spec.get('hero') or {}
    if a.force:
        import unit_wwise_purge as P
        P.purge(amp, [re.compile(r'^%s(_|$)' % re.escape(root_name))], quiet=True)
        olds = [re.compile(r'^%s$' % re.escape(ev_name))]
        if hero.get('event'):
            olds.append(re.compile(r'^%s$' % re.escape(hero['event'])))
        P.purge(evp, olds, quiet=True)
        am = open(amp, encoding='utf-8').read()
        ev = open(evp, encoding='utf-8').read()
    if container_block(am, root_name):
        raise SystemExit('父容器已存在，先清理再跑（或加 --force）: %s' % root_name)
    if find_block(ev, 'Event', ev_name):
        raise SystemExit('事件已存在（或加 --force）: %s' % ev_name)
    if hero.get('event') and find_block(ev, 'Event', hero['event']):
        raise SystemExit('HERO 事件已存在（或加 --force）: %s' % hero['event'])

    tpl_snd = find_block(am, 'Sound', spec['template_sound'])
    tpl_cnt = container_block(am, spec['template_container'])
    tpl_ev = find_block(ev, 'Event', spec['template_event'])
    if not (tpl_snd and tpl_cnt and tpl_ev):
        raise SystemExit('模板缺失: sound=%s container=%s event=%s' % (
            bool(tpl_snd), bool(tpl_cnt), bool(tpl_ev)))

    lufs = spec.get('lufs', -21)
    used = used_shortids(am) | used_shortids(ev)
    ev_wu = re.search(r'<WorkUnit [^>]*ID="(\{[0-9A-F-]+\})"', ev).group(1)

    # ---- 1) 渲染媒体（测不出响度的静音素材直接踢出池子）----
    log, dead = [], set()
    total = sum(len(g['entries']) for g in spec['groups'])
    done = 0
    for g in spec['groups']:
        for e in g['entries']:
            done += 1
            wav = os.path.join(root_dir, 'Originals', 'SFX', e['name'] + '.wav')
            if not a.no_render and not a.dry:
                try:
                    mode = render(e['src'], wav, e.get('lufs', lufs),
                                  e.get('mono', True), e.get('trim'))
                except SystemExit as ex:
                    dead.add(e['name'])
                    sys.stderr.write('  SKIP %s（%s）\n' % (e['name'], str(ex)[:60]))
                    continue
                log.append((e['name'], os.path.basename(e['src']), mode,
                            round(probe_dur(wav), 3)))
            if done % 20 == 0 or done == total:
                sys.stderr.write('  render %d/%d\n' % (done, total))
    if dead:
        spec['groups'] = [dict(g, entries=[e for e in g['entries'] if e['name'] not in dead])
                          for g in spec['groups']]
        print('剔除静音/异常素材 %d 条: %s' % (len(dead), ','.join(sorted(dead))))

    # ---- 2) 声音 + 组容器 ----
    plan = [(g, chunk(g['entries'], g.get('slots', 1))) for g in spec['groups']]
    total_slots = sum(len(c) for _, c in plan)
    group_blocks, group_stat = [], []
    for g, chunks in plan:
        for ci, items in enumerate(chunks, 1):
            gname = '%s_%s_G%02d' % (root_name, g['name'], ci)
            children = []
            for e in items:
                ids = make_shortids(used, 2)
                children.append(clone_sound(tpl_snd.group(0), spec['template_sound'],
                                            e['name'], ids[0], ids[1]))
            block = rebuild_container(tpl_cnt, gname, make_shortids(used, 1)[0],
                                      '\n'.join(children))
            group_blocks.append(block)
        group_stat.append((g['name'], len(chunks), len(g['entries']),
                           '%.2f%%' % (100.0 * len(chunks) / total_slots)))

    # ---- 3) 父容器（一个事件只播这一个对象）----
    root_sid = make_shortids(used, 1)[0]
    root_block = rebuild_container(tpl_cnt, root_name, root_sid, '\n'.join(group_blocks))

    # 插到模板容器之后（同一父节点下，保持树结构合法）
    am = am.replace(tpl_cnt, tpl_cnt + '\n' + root_block, 1)

    # ---- 4) 事件：Play → 父容器 ----
    ev = ev.replace(tpl_ev.group(0),
                    tpl_ev.group(0) + '\n' + clone_event(
                        tpl_ev.group(0), spec['template_event'], ev_name,
                        re.search(r'<ObjectRef Name="([^"]+)" ID="(\{[0-9A-F-]+\})"',
                                  tpl_ev.group(0)).group(1),
                        root_name, re.search(r'<RandomSequenceContainer Name="%s" ID="(\{[0-9A-F-]+\})"'
                                             % re.escape(root_name), am).group(1)), 1)

    # ---- 4b) HERO 专用事件：直接指向某个组的容器（复用对象，媒体不翻倍）----
    hero_ev = None
    if hero.get('event'):
        hg = hero['group']
        hn = '%s_%s_G01' % (root_name, hg)
        hm = re.search(r'<RandomSequenceContainer Name="%s" ID="(\{[0-9A-F-]+\})"' % re.escape(hn), am)
        if not hm:
            raise SystemExit('HERO 组容器缺失: %s（该组需 slots=1）' % hn)
        tgt_name = re.search(r'<ObjectRef Name="([^"]+)" ID="(\{[0-9A-F-]+\})"',
                             tpl_ev.group(0)).group(1)
        ev = ev.replace(tpl_ev.group(0),
                        tpl_ev.group(0) + '\n' + clone_event(
                            tpl_ev.group(0), spec['template_event'], hero['event'],
                            tgt_name, hn, hm.group(1)), 1)
        hero_ev = hero['event']

    for tag, text in (('AM', am), ('EV', ev)):
        try:
            ET.fromstring(text)
        except ET.ParseError as ex:
            raise SystemExit('%s XML 校验失败，未写入：%s' % (tag, ex))

    print('父容器 %s：%d 个子容器' % (root_name, len(group_blocks)))
    for name, nchunk, nentry, pct in group_stat:
        print('  组 %-4s 子容器 %2d  条目 %3d  概率 %s' % (name, nchunk, nentry, pct))
    print('事件 %s → %s' % (ev_name, root_name))
    if hero_ev:
        print('HERO 事件 %s → %s（复用组容器，媒体不增）' % (hero_ev, hn))

    if a.dry:
        return

    open(amp, 'w', encoding='utf-8', newline='').write(am)
    open(evp, 'w', encoding='utf-8', newline='').write(ev)

    # ---- 5) SoundBank 登记 / 摘除 ----
    if spec.get('bank_wu'):
        bankp = os.path.join(root_dir, spec['bank_wu'])
        bank = open(bankp, encoding='utf-8').read()
        if a.unregister:
            bank, removed = unregister_events_from_bank(
                bankp, [x for x in a.unregister.split(',') if x])
            open(bankp, 'w', encoding='utf-8', newline='').write(bank)
            print('摘除旧事件 %d 个: %s' % (len(removed), ','.join(removed)))
        bank, added, fixed = register_events_to_bank(
            bankp, ev, [ev_name] + ([hero_ev] if hero_ev else []))
        open(bankp, 'w', encoding='utf-8', newline='').write(bank)
        print('登记事件 %d 个: %s' % (len(added), ','.join(added)))
        if fixed:
            print('修正 ObjectRef GUID %d 个: %s' % (len(fixed), ','.join(fixed)))

    if log:
        print('渲染 %d 条媒体，总时长 %.1f s' % (len(log), sum(r[3] for r in log)))


if __name__ == '__main__':
    main()
