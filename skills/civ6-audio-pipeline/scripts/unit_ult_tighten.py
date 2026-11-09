#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""unit_ult_tighten.py -- 收紧单位大招语音，避免被动画时间线截断。

背景：HERO_A / HERO_1 时间线必须等于共享剪辑的时长（男 2.200 / 女 2.666667 s），
     长语音不能靠拉长时间线解决，也不能直接截尾。本脚本用三步把语音压进时间线：
       1) 砍掉首尾空白（保留一点点起音/尾音余量）；
       2) 把中间的「死寂段」压缩到 --keep-gap（解包素材常见的 0.5~1.3 s 全零空白）；
       3) 仍超长才对整条音频做 atempo 轻微加速（保音调），而不是砍掉尾部。

用法：
  python unit_ult_tighten.py <Originals/SFX 目录> --limit 2.15 [--pattern '*_UL_*.wav']
                             [--min-tempo 1.03] [--dry]
  # 只报告不改盘：加 --dry

注意：改的是 Wwise 工程的原始 wav（Originals/SFX/*.wav）。改完必须
      1) 删掉 .cache/Windows/SFX 下对应的 .wem（强制 Wwise 重新转码）；
      2) 跑 wwise_wire.py <工程> --generate <BANK>；
      3) 按 references/unit-audio.md §5.1 把 .bnk/.txt/.xml 三件套部署到三处。
"""
import argparse
import array
import glob
import math
import os
import subprocess
import sys
import wave


def read_wav(path):
    w = wave.open(path, 'rb')
    sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
    raw = w.readframes(n)
    w.close()
    if sw != 2:
        raise ValueError('%s 不是 16-bit PCM' % path)
    a = array.array('h')
    a.frombytes(raw)
    if ch == 2:
        a = array.array('h', [(a[i] + a[i + 1]) // 2 for i in range(0, len(a), 2)])
    elif ch != 1:
        raise ValueError('%s 声道数 %d 不支持' % (path, ch))
    return sr, a


def write_wav(path, sr, a):
    w = wave.open(path, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(sr)
    w.writeframes(a.tobytes())
    w.close()


def rms(seg):
    if not seg:
        return 0.0
    return math.sqrt(sum(float(x) * x for x in seg) / len(seg))


def tighten(path, args, ffmpeg):
    sr, a = read_wav(path)
    n = len(a)
    old_dur = n / sr
    win = max(1, int(sr * 0.010))
    thr = 32768 * 10 ** (args.silence_db / 20.0)
    levels = [rms(a[i:i + win]) for i in range(0, n, win)]
    quiet = [v < thr for v in levels]

    loud = [i for i, q in enumerate(quiet) if not q]
    if not loud:
        return dict(name=os.path.basename(path), skipped='整条静音')

    keep_lead = int(sr * args.keep_lead)
    keep_tail = int(sr * args.keep_tail)
    start = max(0, loud[0] * win - keep_lead)
    end = min(n, (loud[-1] + 1) * win + keep_tail)

    # 内部死寂段：连续 quiet 窗口 >= gap_min，起点严格在 [start,end] 内
    gap_min_w = max(1, int(args.gap_min / 0.010))
    keep_gap_s = int(sr * args.keep_gap)
    keep = bytearray(b'\x01') * n
    for i in range(0, start):
        keep[i] = 0
    for i in range(end, n):
        keep[i] = 0
    gaps = []
    i = 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            s, e = i * win, min(n, j * win)
            if (j - i) >= gap_min_w and s > start and e < end:
                drop_s, drop_e = s + keep_gap_s // 2, e - keep_gap_s // 2
                if drop_e > drop_s:
                    for k in range(drop_s, drop_e):
                        keep[k] = 0
                    gaps.append((s / sr, (drop_e - drop_s) / sr))
            i = j
        else:
            i += 1

    out = array.array('h')
    run = None
    for i in range(n):
        if keep[i]:
            if run is None:
                run = i
        else:
            if run is not None:
                out.extend(a[run:i])
                run = None
    if run is not None:
        out.extend(a[run:n])
    if len(out) < sr * 0.05:
        raise ValueError('%s 收紧后过短' % path)

    # 拼接处做 3 ms 线性淡入淡出（切掉的是近静音，理论上听不出，双保险）
    fade = int(sr * 0.003)
    for i in range(min(fade, len(out))):
        out[i] = int(out[i] * i / fade)
    for i in range(min(fade, len(out))):
        out[len(out) - 1 - i] = int(out[len(out) - 1 - i] * i / fade)

    trimmed_dur = len(out) / sr
    # 留 1.5% 余量：atempo 有帧对齐误差，正好卡 limit 会略超
    target = args.limit * 0.985
    tempo = max(args.min_tempo, trimmed_dur / target)
    tempo = min(tempo, args.max_tempo)

    tmp = path + '.tight.wav'
    write_wav(tmp, sr, out)
    cur = tmp
    total_tempo = 1.0
    # 最多两轮补偿，保证最终 <= limit
    for _ in range(3):
        if tempo <= 1.0001:
            break
        nxt = cur + '.atempo.wav'
        subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-i', cur,
                        '-af', 'atempo=%.6f' % tempo, '-ar', str(sr), '-ac', '1',
                        '-c:a', 'pcm_s16le', nxt], check=True)
        if cur != tmp and os.path.exists(cur):
            os.remove(cur)
        cur = nxt
        total_tempo *= tempo
        sr2, b = read_wav(cur)
        new_dur = len(b) / sr2
        if new_dur <= target:
            tempo = 1.0
        else:
            tempo = min(args.max_tempo, new_dur / target)
    final = cur
    sr2, b = read_wav(final)
    new_dur = len(b) / sr2

    if not args.dry:
        os.replace(final, path)
        if tmp != final and os.path.exists(tmp):
            os.remove(tmp)
    else:
        for p in (tmp, final):
            if p != path and os.path.exists(p):
                os.remove(p)

    return dict(name=os.path.basename(path), old=old_dur, trimmed=trimmed_dur,
                new=new_dur, tempo=total_tempo, gaps=gaps,
                lead=(loud[0] * win - start) / sr, tail=(end - (loud[-1] + 1) * win) / sr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sfx_dir')
    ap.add_argument('--pattern', default='*_UL_*.wav')
    ap.add_argument('--limit', type=float, required=True, help='时间线可用时长（秒）')
    ap.add_argument('--min-tempo', type=float, default=1.03)
    ap.add_argument('--max-tempo', type=float, default=1.20)
    ap.add_argument('--silence-db', type=float, default=-55.0)
    ap.add_argument('--keep-lead', type=float, default=0.030)
    ap.add_argument('--keep-tail', type=float, default=0.120)
    ap.add_argument('--keep-gap', type=float, default=0.150)
    ap.add_argument('--gap-min', type=float, default=0.150)
    ap.add_argument('--ffmpeg', default='ffmpeg')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()

    files = sorted(p for p in glob.glob(os.path.join(a.sfx_dir, a.pattern))
                   if '.tight.wav' not in p and '.atempo.wav' not in p)
    if not files:
        print('[FAIL] 没有匹配 %s 的文件' % a.pattern)
        return 1
    print('[TIGHTEN] %s  目标 <= %.3f s  共 %d 条%s' %
          (a.sfx_dir, a.limit, len(files), '（预演）' if a.dry else ''))
    bad = 0
    for p in files:
        r = tighten(p, a, a.ffmpeg)
        if 'skipped' in r:
            print('  %-34s SKIP %s' % (r['name'], r['skipped']))
            continue
        flag = 'OVER!' if r['new'] > a.limit + 0.005 else ''
        if flag:
            bad += 1
        print('  %-34s %.3f -> %.3f -> %.3f s  tempo %.3f  gap -%.2f s %s' %
              (r['name'], r['old'], r['trimmed'], r['new'], r['tempo'],
               sum(g[1] for g in r['gaps']), flag))
    print('[TIGHTEN] 超限 %d 条' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
