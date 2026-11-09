import sys
import os
import json
import struct

sys.path.insert(0, "C:/Users/Administrator/.agents/skills/civ6-audio-pipeline/scripts")
import wwise_shortid

BANK = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Platforms/Windows/Audio/Jinzhou_Jinhsi_Speech.bnk"
OUT = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/audio/speech_bank_media.json"

data = open(BANK, "rb").read()
chunks, didx, hirc, data_start = wwise_shortid.parse_bank(data)

print("CHUNKS", sorted(k.decode("ascii", "replace") for k in chunks))
print("HIRC counts", {t: sum(1 for x, _ in hirc if x == t) for t in sorted({x for x, _ in hirc})})
print("DIDX entries", len(didx))
print("DATA start", data_start, "DATA len", len(chunks[b"DATA"]))

entries = []
for fid, off, sz in didx:
    blob = chunks[b"DATA"][off:off + sz]
    tag = blob[:4]
    riff_size = struct.unpack("<I", blob[4:8])[0] if len(blob) >= 8 else -1
    wave = blob[8:12]
    fmt_tag = None
    channels = None
    rate = None
    bits = None
    p = 12
    while p + 8 <= len(blob):
        ctag = blob[p:p+4]
        csz = struct.unpack("<I", blob[p+4:p+8])[0]
        if ctag == b"fmt ":
            fmt_tag = struct.unpack("<H", blob[p+8:p+10])[0]
            channels = struct.unpack("<H", blob[p+10:p+12])[0]
            rate = struct.unpack("<I", blob[p+12:p+16])[0]
            bits = struct.unpack("<H", blob[p+22:p+24])[0]
        p += 8 + csz + (csz & 1)
    entries.append(dict(id=fid, offset=off, size=sz, riff=tag.decode("latin1"),
                        wave=wave.decode("latin1"), fmt_tag=fmt_tag,
                        channels=channels, rate=rate, bits=bits))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(json.dumps(entries, ensure_ascii=False, indent=1))
print("WROTE", OUT)
for e in entries:
    print(e["id"], e["size"], e["riff"], e["wave"], "fmt=0x%04x" % e["fmt_tag"] if e["fmt_tag"] is not None else "fmt=?",
          e["channels"], e["rate"], e["bits"])
