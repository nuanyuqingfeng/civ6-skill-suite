import json
import os
import subprocess

ROOT = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi"
TMP = ROOT + "/workspace/tmp/audio"
CLI = TMP + "/tools/vgmstream/vgmstream-cli.exe"
PCM = TMP + "/pcm"

manifest = json.load(open(TMP + "/speech_media_manifest.json", encoding="utf-8"))
os.makedirs(PCM, exist_ok=True)

for m in manifest:
    out = os.path.join(PCM, m["event"] + ".wav")
    r = subprocess.run([CLI, "-o", out, m["path"]], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(m["event"] + " decode failed: " + r.stderr)
    print(m["event"], os.path.getsize(out))

print("decoded", len(manifest))
