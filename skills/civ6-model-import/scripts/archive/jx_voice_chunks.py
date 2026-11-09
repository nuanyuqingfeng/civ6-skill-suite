import json
import os
import struct

TMP = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/audio"
WEM = TMP + "/wem"

tags = {}
for name in sorted(os.listdir(WEM)):
    if not name.endswith(".wem"):
        continue
    blob = open(os.path.join(WEM, name), "rb").read()
    p = 12
    got = []
    while p + 8 <= len(blob):
        t = blob[p:p + 4]
        sz = struct.unpack("<I", blob[p + 4:p + 8])[0]
        got.append(t.decode("latin1"))
        p += 8 + sz + (sz & 1)
    tags[name] = got

seen = sorted({tuple(v) for v in tags.values()})
for s in seen:
    print(s, "count", sum(1 for v in tags.values() if tuple(v) == s))
print("any_loop_chunk", any("smpl" in v or "loop" in v for v in tags.values()))
json.dump(tags, open(TMP + "/wem_chunks.json", "w", encoding="utf-8"), indent=1)
