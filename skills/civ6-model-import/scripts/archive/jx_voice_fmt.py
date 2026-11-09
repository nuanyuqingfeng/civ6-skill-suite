import sys
import struct

sys.path.insert(0, "C:/Users/Administrator/.agents/skills/civ6-audio-pipeline/scripts")
import wwise_shortid

BANK = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/Jinzhou_Jinhsi/Platforms/Windows/Audio/Jinzhou_Jinhsi_Speech.bnk"
data = open(BANK, "rb").read()
chunks, didx, hirc, data_start = wwise_shortid.parse_bank(data)
fid, off, sz = didx[0]
blob = chunks[b"DATA"][off:off + sz]
p = 12
while p + 8 <= len(blob):
    tag = blob[p:p + 4]
    csz = struct.unpack("<I", blob[p + 4:p + 8])[0]
    print(tag, csz)
    if tag == b"fmt ":
        body = blob[p + 8:p + 8 + csz]
        print("  wFormatTag 0x%04x" % struct.unpack("<H", body[0:2])[0])
        print("  channels", struct.unpack("<H", body[2:4])[0])
        print("  rate", struct.unpack("<I", body[4:8])[0])
        print("  avgbytes", struct.unpack("<I", body[8:12])[0])
        print("  blockalign", struct.unpack("<H", body[12:14])[0])
        print("  bits", struct.unpack("<H", body[14:16])[0])
        print("  cbsize", struct.unpack("<H", body[16:18])[0])
        print("  extra", body[18:].hex(" "))
    if tag == b"data":
        print("  first 32 bytes", blob[p + 8:p + 40].hex(" "))
    p += 8 + csz + (csz & 1)
print("tail", blob[p:p + 16].hex(" "))
