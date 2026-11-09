import argparse
import json
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# 通用 Wwise wem 批量解码：vgmstream-cli 多进程转 PCM WAV（保持源采样率，鸣潮为 48kHz）。
# RIFF 魔数检测：非 RIFF 的私有媒体（Kuro PLUG 等）与 vgmstream 拒收文件原样保留 .wem 并登记清单。
#
# 目录约定：
#   --stage  下镜像目标树的 .wem 文件，文件名为最终目标名 + ".wem"（如 BGM/xxx__1.wav.wem）
#   转码成功 -> 输出 --out-root 下对应 .wav，并删除 stage 源
#   失败/非 RIFF -> 移动到 --plug-dir（默认 <out-root>/Unreferenced/PLUG_wem）保留 .wem


def transcode(stage_file: Path, out_root: Path):
    head = stage_file.read_bytes()[:4]
    dest = stage_file.with_suffix('')  # 去掉 .wem 得最终目标路径（跨盘时由主进程相对化）
    if head != b'RIFF':
        return ('plug', stage_file, dest, 'not RIFF magic')
    out = out_root / dest.relative_to(out_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([VGM, '-o', str(out), str(stage_file)], capture_output=True, text=True)
    if r.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        if out.exists():
            out.unlink()
        return ('failed', stage_file, dest, (r.stderr or r.stdout or '')[-200:])
    stage_file.unlink()
    return ('ok', stage_file, out, '')


VGM = 'vgmstream-cli'


def main():
    global VGM
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', required=True, help='镜像目标树的 .wem 中转目录')
    ap.add_argument('--out-root', required=True, help='最终输出根目录')
    ap.add_argument('--vgmstream', default=VGM, help='vgmstream-cli 可执行路径')
    ap.add_argument('--plug-dir', default=None, help='无法解码文件的保留目录（默认 <out-root>/Unreferenced/PLUG_wem）')
    ap.add_argument('--report', default=None, help='清单输出目录（默认与 stage 同级的 _work）')
    ap.add_argument('--workers', type=int, default=16)
    args = ap.parse_args()

    VGM = args.vgmstream

    stage = Path(args.stage).resolve()
    out_root = Path(args.out_root).resolve()
    plug_dir = Path(args.plug_dir) if args.plug_dir else out_root / 'Unreferenced' / 'PLUG_wem'
    report = Path(args.report) if args.report else stage.parent / '_work'
    plug_dir.mkdir(parents=True, exist_ok=True)
    report.mkdir(parents=True, exist_ok=True)

    files = sorted(stage.rglob('*.wem'))
    print('stage wem files:', len(files))
    plug_rows = []   # 保留原样的文件（PLUG 私有媒体 / vgmstream 拒收）
    errors = []
    ok = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(transcode, f, out_root): f for f in files}
        for i, fut in enumerate(as_completed(futs), 1):
            kind, stage_file, dest, msg = fut.result()
            if kind == 'ok':
                ok += 1
            else:
                target = plug_dir / (dest.stem + '.wem')
                if target.exists():
                    target = plug_dir / (dest.stem + '_2.wem')
                if not target.exists() or kind == 'plug':
                    shutil.move(str(stage_file), target)
                if kind == 'plug':
                    plug_rows.append({'plug_file': target.relative_to(out_root).as_posix(), 'dest': dest.relative_to(out_root).as_posix(), 'bytes': target.stat().st_size, 'reason': msg})
                else:
                    errors.append({'dest': dest.relative_to(out_root).as_posix(), 'plug_file': target.relative_to(out_root).as_posix(), 'reason': msg})
            if i % 5000 == 0:
                print(f'{i}/{len(files)} ok={ok} plug={len(plug_rows)} failed={len(errors)}')
    (report / 'plug_rows.json').write_text(json.dumps(plug_rows, ensure_ascii=False, indent=1), encoding='utf-8')
    (report / 'transcode_errors.json').write_text(json.dumps(errors, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'DONE ok={ok} plug={len(plug_rows)} failed={len(errors)}')


if __name__ == '__main__':
    main()
