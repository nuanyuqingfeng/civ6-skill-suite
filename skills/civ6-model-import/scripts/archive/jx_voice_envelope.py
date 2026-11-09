import json
import math
import os
import wave

import numpy as np

ROOT = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi"
TMP = ROOT + "/workspace/tmp/audio"
PCM = TMP + "/pcm"
ORIG = "D:/desktop/Material/Mod_Jinzhou/Audio_Jinhsi/Jinzhou_Jinhsi/Originals/SFX"
REPORT = ROOT + "/workspace/gen/reports/round3_voice_envelope.json"

FPS = 30
SPF = 48000 // FPS
GATE_DB = -45.0
GATE = 10 ** (GATE_DB / 20.0)
GAMMA = 0.65
FLOOR = 0.02
RELEASE = 0.35

ACTIONS = [
    ("JX_IDLE", "JX_IDLE", None, 240),
    ("JX_FirstMeet", "01_FIRST_MEET", "JINZ_JX_FIRST_MEET_A", 210),
    ("JX_DeclareWarHuman", "02_DECLARE_WAR_FROM_HUMAN", "JINZ_JX_DECLARE_WAR_FROM_HUMAN_A", 180),
    ("JX_DeclareWarAI", "03_DECLARE_WAR_FROM_AI", "JINZ_JX_DECLARE_WAR_FROM_AI_A", 330),
    ("JX_Kudos", "04_KUDOS", "JINZ_JX_KUDO_EXIT_A", 459),
    ("JX_Warning", "05_WARNING", "JINZ_JX_WARNING_EXIT_A", 150),
    ("JX_Defeat", "06_DEFEAT", "JINZ_JX_DEFEAT_FROM_AI_A", 90),
]

# 语音起始时刻取自 .ast 的 m_fStartTime：04_KUDOS 为 1.300000 s，其余段为 0.500000 s
VOICE_OFFSET_S = 0.5
VOICE_OFFSETS_S = {"JX_Kudos": 1.3}


def read_wav(path):
    with wave.open(path, "rb") as f:
        ch = f.getnchannels()
        width = f.getsampwidth()
        rate = f.getframerate()
        raw = f.readframes(f.getnframes())
    if width != 2:
        raise RuntimeError("expected 16-bit PCM: " + path)
    x = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, rate


def frame_rms(x, rate):
    spf = rate // FPS
    n = len(x) // spf
    trimmed = x[: n * spf].reshape(n, spf)
    return np.sqrt((trimmed ** 2).mean(axis=1))


def mouth_curve(env_norm):
    shaped = np.clip((env_norm - FLOOR) / (1.0 - FLOOR), 0.0, 1.0) ** GAMMA
    y = np.empty_like(shaped)
    prev = 0.0
    for i, v in enumerate(shaped):
        y[i] = max(v, prev - RELEASE)
        prev = y[i]
    return y


audio_rows = []
decoded = {}
for name in sorted(os.listdir(PCM)):
    if not name.endswith(".wav"):
        continue
    ev = name[:-4]
    x, rate = read_wav(os.path.join(PCM, name))
    rms = frame_rms(x, rate)
    dur = len(x) / rate
    peak = float(np.abs(x).max())
    decoded[ev] = (x, rate, rms, dur)

    orig_path = os.path.join(ORIG, ev + ".wav")
    corr = None
    orig_dur = None
    if os.path.exists(orig_path):
        ox, orate = read_wav(orig_path)
        orms = frame_rms(ox, orate)
        orig_dur = len(ox) / orate
        k = min(len(rms), len(orms))
        corr = float(np.corrcoef(rms[:k], orms[:k])[0, 1])

    audio_rows.append(dict(event=ev, duration_s=round(dur, 6), frames=int(round(dur * FPS)),
                           peak=round(peak, 4), rms_max=round(float(rms.max()), 6),
                           rms_mean=round(float(rms.mean()), 6), orig_duration_s=orig_dur,
                           orig_corr=corr))

json.dump(audio_rows, open(TMP + "/audio_durations.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

entries = []
for action, slot, event, frames in ACTIONS:
    if event is None:
        entries.append(dict(action=action, audio=None, ast_slot=slot, duration_s=0.0,
                            frames=frames, voice_offset_frames=None,
                            voice_start_frame=None, voice_end_frame=None,
                            voice_overrun_frames=0, envelope={str(i): 0.0 for i in range(1, frames + 1)}))
        continue
    x, rate, rms, dur = decoded[event]
    env_norm = rms / rms.max()
    env_norm[rms < GATE] = 0.0
    mouth = mouth_curve(env_norm)

    offset = int(round(VOICE_OFFSETS_S.get(action, VOICE_OFFSET_S) * FPS))
    start_frame = 1 + offset
    voice_frames = int(math.ceil(dur * FPS))
    end_frame = start_frame + voice_frames - 1
    overrun = max(0, end_frame - frames)

    env = {}
    for i in range(1, frames + 1):
        k = i - start_frame
        env[str(i)] = round(float(mouth[k]), 3) if 0 <= k < len(mouth) else 0.0

    first_loud = int(np.argmax(env_norm > 0.02)) if np.any(env_norm > 0.02) else -1
    last_loud = int(len(env_norm) - 1 - np.argmax(env_norm[::-1] > 0.02)) if np.any(env_norm > 0.02) else -1

    entries.append(dict(action=action, audio=event, ast_slot=slot, duration_s=round(dur, 6),
                        frames=frames, voice_offset_frames=offset,
                        voice_start_frame=start_frame, voice_end_frame=end_frame,
                        voice_overrun_frames=overrun,
                        voice_first_loud_frame=int(first_loud), voice_last_loud_frame=int(last_loud),
                        envelope=env))

doc = dict(
    meta=dict(fps=FPS, sample_rate=48000, samples_per_frame=SPF,
              source="Jinzhou_Jinhsi_Speech.bnk DIDX media -> vgmstream-cli r2117 (Wwise 4-bit IMA ADPCM) -> PCM S16 mono 48k",
              normalization="frame RMS / max frame RMS of the same file, gated below -45 dBFS",
              mouth_curve="clip((env-0.02)/0.98,0,1)^0.65 then release limiter 0.35/frame",
              voice_offset_source="LEAD_JINZ_Jinhsi_QYQXP.ast m_fStartTime：04_KUDOS 1.3 s，其余段 0.5 s",
              frame_convention="frame 1 = t 0 s, frame N = t (N-1)/30 s",
              voice_start_frame="1 + round(m_fStartTime×30)：Kudos 40，其余段 16"),
    entries=entries,
)
os.makedirs(os.path.dirname(REPORT), exist_ok=True)
json.dump(doc, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

for e in entries:
    print(e["action"], e["audio"], e["duration_s"], e["frames"], e["voice_offset_frames"],
          e.get("voice_end_frame"), e.get("voice_overrun_frames"), len(e["envelope"]))
print("max_abs_env", max(max(e["envelope"].values()) for e in entries))
