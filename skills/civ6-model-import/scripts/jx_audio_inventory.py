import json
import os
import re
import subprocess
import sys

sys.path.insert(0, "C:/Users/Administrator/.agents/skills/civ6-audio-pipeline/scripts")
import wwise_shortid

ROOT = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi"
AUDIO = ROOT + "/Jinzhou_Jinhsi/Platforms/Windows/Audio"
TMP = ROOT + "/workspace/tmp/audio"
CLI = TMP + "/tools/vgmstream/vgmstream-cli.exe"


def probe(path):
    r = subprocess.run([CLI, "-m", path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = r.stdout + r.stderr
    dur = re.search(r"play duration: .*\((\d+):([0-9.]+) seconds\)", out)
    enc = re.search(r"encoding: (.+)", out)
    rate = re.search(r"sample rate: (\d+) Hz", out)
    ch = re.search(r"channels: (\d+)", out)
    return dict(duration_s=round(int(dur.group(1)) * 60 + float(dur.group(2)), 6) if dur else None,
                encoding=enc.group(1).strip() if enc else None,
                rate=int(rate.group(1)) if rate else None,
                channels=int(ch.group(1)) if ch else None)


streams = []
for name in sorted(os.listdir(AUDIO)):
    if not name.endswith(".wem"):
        continue
    path = os.path.join(AUDIO, name)
    info = probe(path)
    info.update(file=name, bytes=os.path.getsize(path), id=int(name[:-4]))
    streams.append(info)

banks = {}
for bnk in ["Jinzhou_Great_People.bnk", "Jinzhou_Jinhsi_Speech.bnk", "Jinzhou_Jinhsi_Music_Bank.bnk"]:
    data = open(os.path.join(AUDIO, bnk), "rb").read()
    chunks, didx, hirc, data_start = wwise_shortid.parse_bank(data)
    media = []
    for fid, off, sz in didx:
        blob = chunks[b"DATA"][off:off + sz]
        ext = os.path.join(TMP, "bank_" + bnk.replace(".bnk", ""), "%d.wem" % fid)
        os.makedirs(os.path.dirname(ext), exist_ok=True)
        open(ext, "wb").write(blob)
        info = probe(ext)
        info.update(file_id=fid, bytes=sz)
        media.append(info)
    banks[bnk] = dict(bytes=len(data),
                      hirc={str(t): sum(1 for x, _ in hirc if x == t) for t in sorted({x for x, _ in hirc})},
                      didx_count=len(didx), media=media)

json.dump(dict(streamed=streams, banks=banks),
          open(TMP + "/audio_inventory.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("streamed", len(streams))
for s in streams:
    print(" ", s["file"], s["duration_s"], s["encoding"], s["rate"], s["channels"])
for k, v in banks.items():
    print(k, v["bytes"], v["hirc"], "media", v["didx_count"])
    for m in v["media"]:
        print("  ", m["file_id"], m["duration_s"], m["encoding"], m["rate"], m["channels"])
