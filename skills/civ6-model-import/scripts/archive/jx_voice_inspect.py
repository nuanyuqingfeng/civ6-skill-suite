import json
import sys

import numpy as np

sys.path.insert(0, "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/_tools")
from jx_voice_envelope import read_wav, frame_rms

PCM = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/tmp/audio/pcm/"
for ev in ["JINZ_JX_KUDO_EXIT_A", "JINZ_JX_DEFEAT_FROM_AI_A", "JINZ_JX_WARNING_EXIT_A"]:
    x, rate = read_wav(PCM + ev + ".wav")
    rms = frame_rms(x, rate)
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    print(ev, "frames", len(rms))
    for k in range(0, len(rms), 10):
        print("  %3d %6.1f dB" % (k, db[k:k + 10].max()))
