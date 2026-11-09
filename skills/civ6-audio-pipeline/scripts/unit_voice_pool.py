#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""单位语音单个 Sound / Event 的批量落地（通用）

给定一份 spec.json，做三件事：
  1) 把素材按目标响度渲染到 <工程>/Originals/SFX/<name>.wav（可选裁切/淡出）；
  2) 在 Actor-Mixer 工作单元里克隆出一个 Sound 对象（新 GUID/ShortID）；
  3) 在 Events 工作单元里克隆出一个 Event（新 GUID，ObjectRef 指向该 Sound）。

之后照常 `wwise_wire.py --generate` 重建 bank。

spec.json：
{
  "project":       "<Wwise 工程根目录>",
  "am_wu":         "Actor-Mixer Hierarchy/LeaderSpeech_Feline.wwu",
  "ev_wu":         "Events/<xxx>_Events.wwu",
  "template_sound":"Play_RoverMale_Ult_01",      // 克隆模板：一个已有的单声 Sound
  "template_event":"Play_RoverMale_Victory",     // 克隆模板：一个已有的单元素 Event
  "entries": [
    {"src": "...wav", "name": "Play_RoverMale_Probe_A",
     "event": "Play_RoverMale_Probe_A",
     "lufs": -21, "mono": true,
     "trim": [0, 3.5]}                            // 可选 [start, dur] 秒
  ]
}

幂等：Sound / Event 已存在则跳过创建，只重新渲染媒体。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

FF = 'ffmpeg'
FFPROBE = 'ffprobe'


# ---------- 响度渲染 ----------

def _run(args):
    return subprocess.run(args, capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def _measure(src, I, pad=False):
    af = 'loudnorm=I=%s:TP=-1.5:LRA=11:print_format=json' % I
    if pad:
        af = 'apad=pad_dur=5,' + af
    r = _run([FF, '-hide_banner', '-nostats', '-i', src, '-af', af, '-f', 'null', '-'])
    i, j = r.stderr.rfind('{'), r.stderr.rfind('}')
    if i < 0 or j < 0:
        return None
    try:
        return json.loads(r.stderr[i:j + 1])
    except ValueError:
        return None


def render(src, dst, target_lufs, mono=True, trim=None):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    pre = []
    if trim:
        start, dur = float(trim[0]), float(trim[1])
        pre.append('atrim=%.3f:%.3f' % (start, start + dur))
        if dur > 0.12:
            pre.append('afade=t=out:st=%.3f:d=0.06' % (start + dur - 0.06))
    m = _measure(src, target_lufs)
    short = not (m and m.get('input_i') not in ('-inf', 'inf', None))
    if short:
        m = _measure(src, target_lufs, pad=True)
    if not m or m.get('input_i') in ('-inf', 'inf', None):
        raise SystemExit('无法测量响度: ' + src)

    if short:
        gain = target_lufs - float(m['input_i'])
        af = 'volume=%.2fdB,alimiter=limit=0.891:level=false' % gain
        mode = 'gain%+.1fdB' % gain
    else:
        af = ('loudnorm=I=%s:TP=-1.5:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:'
              'measured_thresh=%s:offset=%s:linear=true' %
              (target_lufs, m['input_i'], m['input_tp'], m['input_lra'],
               m['input_thresh'], m['target_offset']))
        mode = 'loudnorm'
    if pre:
        af = ','.join(pre) + ',' + af

    cmd = [FF, '-y', '-hide_banner', '-loglevel', 'error', '-i', src, '-af', af,
           '-ar', '48000', '-ac', '1' if mono else '2', '-c:a', 'pcm_s16le', dst]
    r = _run(cmd)
    if r.returncode != 0:
        raise SystemExit('ffmpeg 失败 %s\n%s' % (src, r.stderr[-500:]))
    return mode


def probe_dur(path):
    r = _run([FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
              '-of', 'csv=p=0', path])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return -1.0


# ---------- Wwise 侧 ----------

def guid():
    return '{%s}' % str(uuid.uuid4()).upper()


def used_shortids(text):
    return set(int(x) for x in re.findall(r'ShortID="(\d+)"', text))


def make_shortids(used, n, seed=20261105):
    import random
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        v = rng.randrange(1, 1 << 31)
        if v not in used:
            used.add(v)
            out.append(v)
    return out


def clone_sound(tpl, old, new, sid_sound, sid_file):
    s = tpl
    s = re.sub(r'(<Sound Name=")%s(" ID=")\{[0-9A-F-]+\}(" ShortID=")\d+(")' % re.escape(old),
               lambda m: m.group(1) + new + m.group(2) + guid() + m.group(3) + str(sid_sound) + m.group(4),
               s, count=1)
    s = re.sub(r'(<AudioFileSource Name=")%s(" ID=")\{[0-9A-F-]+\}(" ShortID=")\d+(")' % re.escape(old),
               lambda m: m.group(1) + new + m.group(2) + guid() + m.group(3) + str(sid_file) + m.group(4),
               s, count=1)
    s = s.replace('<AudioFile>%s.wav</AudioFile>' % old, '<AudioFile>%s.wav</AudioFile>' % new)
    s = re.sub(r'(<ActiveSource Name=")%s(" ID=")\{[0-9A-F-]+\}(")' % re.escape(old),
               lambda m: m.group(1) + new + m.group(2) + guid() + m.group(3), s, count=1)
    return s


def clone_event(tpl, old_ev, new_ev, old_snd, new_snd, new_snd_id):
    s = tpl
    s = re.sub(r'(<Event Name=")%s(" ID=")\{[0-9A-F-]+\}(")' % re.escape(old_ev),
               lambda m: m.group(1) + new_ev + m.group(2) + guid() + m.group(3), s, count=1)
    s = re.sub(r'(<Action Name="Play" ID=")\{[0-9A-F-]+\}(")',
               lambda m: m.group(1) + guid() + m.group(2), s, count=1)
    s = re.sub(r'(<Element ID=")\{[0-9A-F-]+\}(")',
               lambda m: m.group(1) + guid() + m.group(2), s, count=1)
    s = re.sub(r'(<ObjectRef Name=")%s(" ID=")\{[0-9A-F-]+\}(")' % re.escape(old_snd),
               lambda m: m.group(1) + new_snd + m.group(2) + new_snd_id + m.group(3), s, count=1)
    return s


def find_block(text, tag, name):
    return re.search(r'(\t*)<%s Name="%s".*?</%s>\n' % (tag, re.escape(name), tag), text, re.S)


def register_events_to_bank(bank_path, ev_text, names):
    """把事件登记进 SoundBank 的 ObjectInclusionList。

    ⚠️ 极易漏：SoundBank 是显式枚举包含对象的，新建的 Event 不登记就不会进 bank，
    生成出来不报错、bank 里就是没有该事件（症状：t<xt/xml 里查不到、运行时静默）。
    """
    bank = open(bank_path, encoding='utf-8').read()
    wu_id = re.search(r'<WorkUnit [^>]*ID="(\{[0-9A-F-]+\})"', ev_text).group(1)
    added = []
    for name in names:
        if re.search(r'<ObjectRef Name="%s"' % re.escape(name), bank):
            continue
        g = re.search(r'<Event Name="%s" ID="(\{[0-9A-F-]+\})"' % re.escape(name), ev_text)
        if not g:
            raise SystemExit('Events 里找不到事件定义: %s' % name)
        m = re.search(r'(\t*)<ObjectRef [^\n]*/>\s*\n(\t*)</ObjectInclusionList>', bank)
        if not m:
            raise SystemExit('bank 里找不到 ObjectInclusionList')
        indent = m.group(1)
        line = '%s<ObjectRef Name="%s" ID="%s" WorkUnitID="%s" Filter="7" Origin="Manual"/>\n' % (
            indent, name, g.group(1), wu_id)
        bank = bank[:m.start(2)] + line + bank[m.start(2):]
        added.append(name)
    return bank, added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--only', default='', help='只处理这些 name，逗号分隔')
    a = ap.parse_args()

    spec = json.load(open(a.spec, encoding='utf-8'))
    root = spec['project']
    amp = os.path.join(root, spec['am_wu'])
    evp = os.path.join(root, spec['ev_wu'])
    am = open(amp, encoding='utf-8').read()
    ev = open(evp, encoding='utf-8').read()

    tpl_snd = find_block(am, 'Sound', spec['template_sound'])
    tpl_ev = find_block(ev, 'Event', spec['template_event'])
    if not tpl_snd:
        raise SystemExit('Actor-Mixer 里找不到模板 Sound: %s' % spec['template_sound'])
    if not tpl_ev:
        raise SystemExit('Events 里找不到模板 Event: %s' % spec['template_event'])

    only = set(x for x in a.only.split(',') if x)
    used = used_shortids(am) | used_shortids(ev)
    snd_ins, ev_ins = [], []
    log = []

    for e in spec['entries']:
        name, evname = e['name'], e.get('event', e['name'])
        if only and name not in only:
            continue
        wav = os.path.join(root, 'Originals', 'SFX', name + '.wav')
        if not a.dry:
            mode = render(e['src'], wav, e.get('lufs', -21),
                          e.get('mono', True), e.get('trim'))
            dur = probe_dur(wav)
            log.append((name, os.path.basename(e['src']), mode, dur))

        if find_block(am, 'Sound', name):
            pass
        else:
            ids = make_shortids(used, 2)
            snd_ins.append(clone_sound(tpl_snd.group(0), spec['template_sound'], name, ids[0], ids[1]))

        if find_block(ev, 'Event', evname):
            continue
        m = re.search(r'<Sound Name="%s" ID="(\{[0-9A-F-]+\})"' % re.escape(name), am)
        if not m:
            m = re.search(r'<Sound Name="%s" ID="(\{[0-9A-F-]+\})"' % re.escape(name),
                          ''.join(snd_ins))
            if not m:
                raise SystemExit('新 Sound 的 GUID 没生成出来: %s' % name)
        ev_ins.append(clone_event(tpl_ev.group(0), spec['template_event'], evname,
                                  spec['template_sound'], name, m.group(1)))

    if snd_ins:
        am = am.replace(tpl_snd.group(0), tpl_snd.group(0) + ''.join(snd_ins), 1)
    if ev_ins:
        ev = ev.replace(tpl_ev.group(0), tpl_ev.group(0) + ''.join(ev_ins), 1)

    for tag, text in (('AM', am), ('EV', ev)):
        try:
            ET.fromstring(text)
        except ET.ParseError as ex:
            raise SystemExit('%s XML 校验失败，未写入：%s' % (tag, ex))

    if not a.dry:
        open(amp, 'w', encoding='utf-8', newline='').write(am)
        open(evp, 'w', encoding='utf-8', newline='').write(ev)

    bank_added = []
    if spec.get('bank_wu'):
        bankp = os.path.join(root, spec['bank_wu'])
        names = [e.get('event', e['name']) for e in spec['entries']
                 if not only or e['name'] in only]
        bank, bank_added = register_events_to_bank(bankp, ev, names)
        try:
            ET.fromstring(bank)
        except ET.ParseError as ex:
            raise SystemExit('SoundBank XML 校验失败，未写入：%s' % ex)
        if not a.dry:
            open(bankp, 'w', encoding='utf-8', newline='').write(bank)

    print('%s project=%s' % ('[dry]' if a.dry else '[写入]', root))
    for name, src, mode, dur in log:
        print('  %-30s <- %-40s %-12s %.2fs' % (name, src, mode, dur))
    print('  新建 Sound %d 个, 新建 Event %d 个, bank 登记 %d 个'
          % (len(snd_ins), len(ev_ins), len(bank_added)))
    if bank_added:
        print('  bank 新增登记: %s' % ', '.join(bank_added))


if __name__ == '__main__':
    main()
