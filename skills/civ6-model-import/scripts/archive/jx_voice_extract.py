import sys
import os
import csv
import json

sys.path.insert(0, "C:/Users/Administrator/.agents/skills/civ6-audio-pipeline/scripts")
import wwise_shortid

ROOT = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi"
AUDIO = ROOT + "/Jinzhou_Jinhsi/Platforms/Windows/Audio"
OUT = ROOT + "/workspace/tmp/audio/wem"

bank = open(AUDIO + "/Jinzhou_Jinhsi_Speech.bnk", "rb").read()
chunks, didx, hirc, data_start = wwise_shortid.parse_bank(bank)

names = {}
section = None
with open(AUDIO + "/Jinzhou_Jinhsi_Speech.txt", encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\r\n")
        if line.startswith("In Memory Audio"):
            section = "mem"
            continue
        if line.startswith("Event") or not line.strip():
            continue
        cells = line.split("\t")
        if section != "mem" or len(cells) < 7:
            continue
        wrote = cells[1].strip()
        if not wrote.isdigit():
            continue
        names[int(wrote)] = cells[2].strip()

os.makedirs(OUT, exist_ok=True)
manifest = []
for fid, off, sz in didx:
    blob = chunks[b"DATA"][off:off + sz]
    name = names[fid]
    path = os.path.join(OUT, name + ".wem")
    with open(path, "wb") as f:
        f.write(blob)
    manifest.append(dict(file_id=fid, event=name, bytes=len(blob), path=path))

json.dump(manifest, open(ROOT + "/workspace/tmp/audio/speech_media_manifest.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("media", len(manifest))
print("named", len(names))
missing = [m["file_id"] for m in manifest if m["event"] is None]
print("missing names", missing)
