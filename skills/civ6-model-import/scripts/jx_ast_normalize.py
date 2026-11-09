import re

ASTS = [r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi\Assets\LEAD_JINZ_Jinhsi_QYQXP.ast"]

DIPLO = [
    ("01_FIRST_MEET", "JX_FirstMeet", "6.966667", "JINZ_JX_FIRST_MEET_A", "1"),
    ("02_DECLARE_WAR_FROM_HUMAN", "JX_DeclareWarHuman", "5.966667", "JINZ_JX_DECLARE_WAR_FROM_HUMAN_A", "2"),
    ("03_DECLARE_WAR_FROM_AI", "JX_DeclareWarAI", "10.966670", "JINZ_JX_DECLARE_WAR_FROM_AI_A", "3"),
    ("04_KUDOS", "JX_Kudos", "15.266667", "JINZ_JX_KUDO_EXIT_A", "4"),
    ("05_WARNING", "JX_Warning", "7.400001", "JINZ_JX_WARNING_EXIT_A", "5"),
    ("06_DEFEAT", "JX_Defeat", "7.966667", "JINZ_JX_DEFEAT_FROM_AI_A", "6"),
]
MOOD = [
    ("NEUTRAL_IDLE_A", "JX_IDLE", "36.666667"),
    ("HAPPY_IDLE_A", "JX_IDLE", "36.666667"),
    ("UNHAPPY_IDLE_A", "JX_IDLE", "36.666667"),
    ("NEUTRAL_POSITIVE_A", "JX_Kudos", "15.266667"),
    ("NEUTRAL_POSITIVE_B", "JX_Kudos", "15.266667"),
    ("NEUTRAL_NEGATIVE_A", "JX_Warning", "7.400001"),
    ("NEUTRAL_NEGATIVE_B", "JX_Warning", "7.400001"),
    ("HAPPY_POSITIVE_A", "JX_Kudos", "15.266667"),
    ("HAPPY_POSITIVE_B", "JX_Kudos", "15.266667"),
    ("HAPPY_NEGATIVE_A", "JX_Warning", "7.400001"),
    ("HAPPY_NEGATIVE_B", "JX_Warning", "7.400001"),
    ("UNHAPPY_POSITIVE_A", "JX_Kudos", "15.266667"),
    ("UNHAPPY_POSITIVE_B", "JX_Kudos", "15.266667"),
    ("UNHAPPY_NEGATIVE_A", "JX_Warning", "7.400001"),
    ("UNHAPPY_NEGATIVE_B", "JX_Warning", "7.400001"),
    ("DECLARE_WAR_A", "JX_DeclareWarAI", "10.966670"),
]
ALL_SLOTS = [(s, a, d) for s, a, d, _fx, _i in DIPLO] + MOOD

TRACKS = ("\t\t\t\t\t\t<m_Tracks>\n"
          "\t\t\t\t\t\t\t<Element>\n\t\t\t\t\t\t\t\t<m_Name text=\"Sound\"/>\n\t\t\t\t\t\t\t\t<m_Type>SOUND</m_Type>\n\t\t\t\t\t\t\t</Element>\n"
          "\t\t\t\t\t\t\t<Element>\n\t\t\t\t\t\t\t\t<m_Name text=\"Asset VFX\"/>\n\t\t\t\t\t\t\t\t<m_Type>ASSET_FX</m_Type>\n\t\t\t\t\t\t\t</Element>\n"
          "\t\t\t\t\t\t\t<Element>\n\t\t\t\t\t\t\t\t<m_Name text=\"Transfer\"/>\n\t\t\t\t\t\t\t\t<m_Type>TRANSFER</m_Type>\n\t\t\t\t\t\t\t</Element>\n"
          "\t\t\t\t\t\t\t<Element>\n\t\t\t\t\t\t\t\t<m_Name text=\"Action\"/>\n\t\t\t\t\t\t\t\t<m_Type>ACTION</m_Type>\n\t\t\t\t\t\t\t</Element>\n"
          "\t\t\t\t\t\t\t<Element>\n\t\t\t\t\t\t\t\t<m_Name text=\"ArtDef VFX\"/>\n\t\t\t\t\t\t\t\t<m_Type>ARTDEF_VFX</m_Type>\n\t\t\t\t\t\t\t</Element>\n"
          "\t\t\t\t\t\t\t<Element>\n\t\t\t\t\t\t\t\t<m_Name text=\"Light\"/>\n\t\t\t\t\t\t\t\t<m_Type>LIGHT</m_Type>\n\t\t\t\t\t\t\t</Element>\n"
          "\t\t\t\t\t\t</m_Tracks>\n")


TRIGGER = ("\t\t\t\t\t\t<m_Triggers>\n"
           "\t\t\t\t\t\t\t<Element>\n"
           "\t\t\t\t\t\t\t\t<m_eType>SOUND</m_eType>\n"
           "\t\t\t\t\t\t\t\t<m_Name text=\"%s\"/>\n"
           "\t\t\t\t\t\t\t\t<m_Description text=\"\"/>\n"
           "\t\t\t\t\t\t\t\t<m_FXName text=\"%s\"/>\n"
           "\t\t\t\t\t\t\t\t<m_CollectionName text=\"\"/>\n"
           "\t\t\t\t\t\t\t\t<m_AttachmentPointName text=\"\"/>\n"
           "\t\t\t\t\t\t\t\t<m_fStartTime>%s</m_fStartTime>\n"
           "\t\t\t\t\t\t\t\t<m_fDuration>0.000000</m_fDuration>\n"
           "\t\t\t\t\t\t\t\t<m_nTrackIndex>0</m_nTrackIndex>\n"
           "\t\t\t\t\t\t\t</Element>\n"
           "\t\t\t\t\t\t</m_Triggers>\n")

START = {"04_KUDOS": "1.300000"}


def gen_timeline(slot, anim, dur, fx=None, index=None):
    triggers = "\t\t\t\t\t\t<m_Triggers/>\n" if fx is None else TRIGGER % (index, fx, START.get(slot, "0.500000"))
    return ("\t\t\t\t\t<Element>\n"
            "\t\t\t\t\t\t<m_Name text=\"%s\"/>\n"
            "\t\t\t\t\t\t<m_Description text=\"\"/>\n"
            "\t\t\t\t\t\t<m_AnimationName text=\"%s\"/>\n"
            "\t\t\t\t\t\t<m_fDuration>%s</m_fDuration>\n" % (slot, anim, dur)) + triggers + TRACKS + "\t\t\t\t\t</Element>\n"


def normalize(path):
    text = open(path, encoding="utf-8").read()
    tl_s = text.index("<m_timelineBindings>")
    tl_e = text.index("</m_timelineBindings>")
    ln_s = text.index("<m_timelines>")
    ln_e = text.index("</m_timelines>")

    bindings = text[tl_s:tl_e]

    kept = [gen_timeline(slot, anim, dur, fx, index) for slot, anim, dur, fx, index in DIPLO]

    for slot, anim, dur in MOOD:
        kept.append(gen_timeline(slot, anim, dur))

    new_timelines = "<m_timelines>\n\t\t\t\t<m_Timelines>\n" + "".join(kept) + "\t\t\t\t</m_Timelines>\n"

    # 绑定唯一化：每槽仅保留一个，且只保留 ALL_SLOTS 白名单内的槽（清除指向已删时间线的悬空绑定）
    valid = {s for s, _a, _d in ALL_SLOTS}
    seen = set()

    def dedup(m):
        hit = re.search(r'<m_SlotName text="([^"]+)"/>', m.group(0))
        if hit is None or hit.group(1) in seen or hit.group(1) not in valid:
            return ""
        seen.add(hit.group(1))
        return m.group(0)

    bindings = re.sub(r"\t{5}<Element>\n(?:[^\n]*\n)*?\t{5}</Element>\n", dedup, bindings)

    for slot, _a, _d in ALL_SLOTS:
        if ('m_SlotName text="%s"' % slot) not in bindings:
            bindings = bindings.replace(
                "\t\t\t\t</m_Bindings>",
                "\t\t\t\t\t<Element>\n\t\t\t\t\t\t<m_SlotName text=\"%s\"/>\n\t\t\t\t\t\t<m_TimelineName text=\"%s\"/>\n\t\t\t\t\t</Element>\n\t\t\t\t</m_Bindings>" % (slot, slot),
                1)

    open(path, "w", encoding="utf-8", newline="\n").write(
        text[:tl_s] + bindings + text[tl_e:ln_s] + new_timelines + text[ln_e:])
    import xml.etree.ElementTree as ET
    ET.parse(path)
    print("NORMALIZED_OK", path.split("\\")[-1], "diplo_blocks=", len(kept) - len(MOOD))


for p in ASTS:
    normalize(p)
