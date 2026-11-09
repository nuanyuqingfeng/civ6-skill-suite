import json
import os

ROOT = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi"
EXTS = (".lua", ".xml", ".sql", ".ast", ".ini", ".txt", ".modinfo")
PATTERNS = ["JINZ_JX", "PlaySound", "UpdateAudio", ".bnk", "Speech"]

hits = []
for base, dirs, files in os.walk(ROOT):
    for name in files:
        if not name.lower().endswith(EXTS):
            continue
        path = os.path.join(base, name)
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        if rel.startswith("Platforms/Windows/Audio"):
            continue
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for p in PATTERNS:
                if p in line:
                    hits.append(dict(file=rel, line=i, pattern=p, snippet=line.strip()[:160]))
                    break

json.dump(hits, open("D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/audio/audio_refs.json", "w",
                     encoding="utf-8"), ensure_ascii=False, indent=1)
print("files_scanned")
counts = {}
for h in hits:
    counts[h["file"]] = counts.get(h["file"], 0) + 1
for k, v in counts.items():
    print(v, k)
