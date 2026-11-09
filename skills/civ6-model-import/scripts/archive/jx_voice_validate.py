import json
import math

PATH = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/gen/reports/round3_voice_envelope.json"
doc = json.load(open(PATH, encoding="utf-8"))

assert doc["meta"]["fps"] == 30
assert doc["meta"]["samples_per_frame"] == 1600
assert len(doc["entries"]) == 7, len(doc["entries"])

seen = [e["action"] for e in doc["entries"]]
assert seen == ["JX_IDLE", "JX_FirstMeet", "JX_DeclareWarHuman", "JX_DeclareWarAI",
                "JX_Kudos", "JX_Warning", "JX_Defeat"], seen

for e in doc["entries"]:
    for key in ("action", "audio", "duration_s", "frames", "voice_offset_frames", "envelope"):
        assert key in e, (e["action"], key)
    assert len(e["envelope"]) == e["frames"], (e["action"], len(e["envelope"]), e["frames"])
    assert sorted(int(k) for k in e["envelope"]) == list(range(1, e["frames"] + 1)), e["action"]
    vals = [e["envelope"][str(i)] for i in range(1, e["frames"] + 1)]
    assert all(0.0 <= v <= 1.0 for v in vals), e["action"]
    if e["audio"] is None:
        assert e["voice_offset_frames"] is None and max(vals) == 0.0
    else:
        off = e["voice_offset_frames"]
        assert e["voice_start_frame"] == off + 1, (e["action"], off, e["voice_start_frame"])
        assert e["voice_end_frame"] == off + math.ceil(e["duration_s"] * 30), (
            e["action"], off, e["duration_s"], e["voice_end_frame"])
        assert max(vals) > 0.9, (e["action"], max(vals))
        assert all(v == 0.0 for v in vals[:off]), e["action"]

print("PASS entries", len(doc["entries"]))
print("PASS frames", sum(e["frames"] for e in doc["entries"]))
