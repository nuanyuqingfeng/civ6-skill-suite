import json
import re

ROOT = "D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi"
ASTS = ["Jinzhou_Jinhsi/Assets/LEAD_JINZ_Jinhsi_QYQXP.ast",
        "Jinzhou_Jinhsi/Assets/LEAD_CHIN_Jinhsi_China_QYQXP.ast"]

out = {}
for rel in ASTS:
    text = open(ROOT + "/" + rel, encoding="utf-8").read()
    body = text[text.index("<m_Timelines>"):]
    rows = []
    for chunk in body.split("<Element>")[1:]:
        name = re.search(r'<m_Name text="([^"]*)"/>', chunk)
        anim = re.search(r'<m_AnimationName text="([^"]*)"/>', chunk)
        dur = re.search(r'<m_fDuration>([0-9.]+)</m_fDuration>', chunk)
        fx = re.search(r'<m_FXName text="([^"]*)"/>', chunk)
        start = re.search(r'<m_fStartTime>([0-9.]+)</m_fStartTime>', chunk)
        if not name:
            continue
        rows.append(dict(name=name.group(1), animation=anim.group(1) if anim else "",
                         timeline_duration=float(dur.group(1)) if dur else None,
                         fx=fx.group(1) if fx else None,
                         start=float(start.group(1)) if start else None))
    out[rel] = rows

json.dump(out, open(ROOT + "/workspace/tmp/audio/ast_timelines.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
for rel, rows in out.items():
    print("==", rel, len(rows))
    for r in rows:
        if r["fx"] or r["name"].startswith("0"):
            print("  %-26s anim=%-20s dur=%.3f fx=%s start=%s" % (r["name"], r["animation"],
                  r["timeline_duration"], r["fx"], r["start"]))
