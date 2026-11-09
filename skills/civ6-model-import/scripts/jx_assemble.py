import os
import re
import shutil

STAGE = r"E:\SoftWares\civ6_nexus_work\jinhsi_fgx"
PROJ = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi"
ANIMS = ["JX_IDLE", "JX_FirstMeet", "JX_DeclareWarHuman", "JX_DeclareWarAI",
         "JX_Kudos", "JX_Warning", "JX_Defeat"]
MATS = ["MI_R2T1JinxiMd10011Bangs", "MI_R2T1JinxiMd10011Hair", "MI_R2T1JinxiMd10011Face",
        "MI_R2T1JinxiMd10011Down", "MI_R2T1JinxiMd10011Skirt", "MI_R2T1JinxiMd10011Eye",
        "MI_6XingStar"]

SLOT_MAP = [
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

TRACKS = ("\t\t\t\t\t\t\t\t<m_Tracks>\n"
          "\t\t\t\t\t\t\t\t\t<Element>\n\t\t\t\t\t\t\t\t\t<m_Name text=\"Sound\"/>\n\t\t\t\t\t\t\t\t\t<m_Type>SOUND</m_Type>\n\t\t\t\t\t\t\t\t</Element>\n"
          "\t\t\t\t\t\t\t\t\t<Element>\n\t\t\t\t\t\t\t\t\t<m_Name text=\"Asset VFX\"/>\n\t\t\t\t\t\t\t\t\t<m_Type>ASSET_FX</m_Type>\n\t\t\t\t\t\t\t\t</Element>\n"
          "\t\t\t\t\t\t\t\t\t<Element>\n\t\t\t\t\t\t\t\t\t<m_Name text=\"Transfer\"/>\n\t\t\t\t\t\t\t\t\t<m_Type>TRANSFER</m_Type>\n\t\t\t\t\t\t\t\t</Element>\n"
          "\t\t\t\t\t\t\t\t\t<Element>\n\t\t\t\t\t\t\t\t\t<m_Name text=\"Action\"/>\n\t\t\t\t\t\t\t\t\t<m_Type>ACTION</m_Type>\n\t\t\t\t\t\t\t\t</Element>\n"
          "\t\t\t\t\t\t\t\t\t<Element>\n\t\t\t\t\t\t\t\t\t<m_Name text=\"ArtDef VFX\"/>\n\t\t\t\t\t\t\t\t\t<m_Type>ARTDEF_VFX</m_Type>\n\t\t\t\t\t\t\t\t</Element>\n"
          "\t\t\t\t\t\t\t\t\t<Element>\n\t\t\t\t\t\t\t\t\t<m_Name text=\"Light\"/>\n\t\t\t\t\t\t\t\t\t<m_Type>LIGHT</m_Type>\n\t\t\t\t\t\t\t\t</Element>\n"
          "\t\t\t\t\t\t\t\t</m_Tracks>\n")

wig_re = re.compile(r"<Element>\s*<m_ID text=\"WIG\"/>\s*<m_RelativePath text=\"[^\"]+\"/>\s*</Element>\s*")


def timeline_element(slot, anim, dur):
    return ("\t\t\t\t\t<Element>\n"
            "\t\t\t\t\t\t<m_Name text=\"%s\"/>\n"
            "\t\t\t\t\t\t<m_Description text=\"\"/>\n"
            "\t\t\t\t\t\t<m_AnimationName text=\"%s\"/>\n"
            "\t\t\t\t\t\t<m_fDuration>%s</m_fDuration>\n"
            "\t\t\t\t\t\t<m_Triggers/>\n" % (slot, anim, dur)) + TRACKS + "\t\t\t\t\t</Element>\n"


def binding_element(slot):
    return ("\t\t\t\t\t<Element>\n"
            "\t\t\t\t\t\t<m_SlotName text=\"%s\"/>\n"
            "\t\t\t\t\t\t<m_TimelineName text=\"%s\"/>\n"
            "\t\t\t\t\t</Element>\n" % (slot, slot))


def group_state(mat):
    return ("\t\t\t\t\t\t<Element>\n"
            "\t\t\t\t\t\t\t<m_Values>\n"
            "\t\t\t\t\t\t\t\t<m_Values>\n"
            "\t\t\t\t\t\t\t\t\t<Element class=\"AssetObjects..ObjectValue\">\n"
            "\t\t\t\t\t\t\t\t\t\t<m_ObjectName text=\"%s\"/>\n"
            "\t\t\t\t\t\t\t\t\t\t<m_eObjectType>MATERIAL</m_eObjectType>\n"
            "\t\t\t\t\t\t\t\t\t\t<m_ParamName text=\"Material\"/>\n"
            "\t\t\t\t\t\t\t\t\t</Element>\n"
            "\t\t\t\t\t\t\t\t\t<Element class=\"AssetObjects..BoolValue\">\n"
            "\t\t\t\t\t\t\t\t\t\t<m_bValue>false</m_bValue>\n"
            "\t\t\t\t\t\t\t\t\t\t<m_ParamName text=\"RecalculateNormals\"/>\n"
            "\t\t\t\t\t\t\t\t\t</Element>\n"
            "\t\t\t\t\t\t\t\t</m_Values>\n"
            "\t\t\t\t\t\t\t</m_Values>\n"
            "\t\t\t\t\t\t\t<m_GroupName text=\"%s\"/>\n"
            "\t\t\t\t\t\t\t<m_MeshName text=\"JinhsiBody\"/>\n"
            "\t\t\t\t\t\t\t<m_StateName text=\"Default\"/>\n"
            "\t\t\t\t\t\t</Element>\n" % (mat, mat))


def text_list(tag, items):
    return ("<%s>\n" % tag + "".join("\t\t<Element text=\"%s\"/>\n" % i for i in items)
            + "\t</%s>" % tag)


def patch_ast(path, mats, anims=None):
    text = open(path, encoding="utf-8").read()
    gs_new = "".join(group_state(m) for m in mats)
    text, n = re.subn(r"<m_GroupStates>.*?</m_GroupStates>",
                      "<m_GroupStates>\n" + gs_new + "\t\t\t\t\t</m_GroupStates>",
                      text, count=1, flags=re.S)
    assert n == 1, "GroupStates not found: " + path
    if anims is not None:
        for tag, items in (("m_Materials", mats), ("m_Animations", anims)):
            text, k = re.subn(r"<%s>.*?</%s>" % (tag, tag), text_list(tag, items), text, count=1, flags=re.S)
            assert k == 1, "block not found: " + tag + " in " + path
    added = 0
    for slot, anim, dur in SLOT_MAP:
        pat = (r'(<m_Name text="' + slot + r'"/>\s*<m_Description text=""/>\s*'
               r'<m_AnimationName text=")[^"]*("/>\s*<m_fDuration>)[0-9.]+(</m_fDuration>)')
        text, n = re.subn(pat, r"\g<1>" + anim + r"\g<2>" + dur + r"\g<3>", text, count=1)
        if n == 0:
            if '<m_SlotName text="%s"/>' % slot not in text:
                text = text.replace("\t\t\t\t</m_Bindings>\n\t\t\t</m_timelineBindings>",
                                    binding_element(slot) + "\t\t\t\t</m_Bindings>\n\t\t\t</m_timelineBindings>", 1)
            text = text.replace("\t\t\t\t</m_Timelines>\n\t\t\t</m_timelines>",
                                timeline_element(slot, anim, dur) + "\t\t\t\t</m_Timelines>\n\t\t\t</m_timelines>", 1)
            added += 1
    open(path, "w", encoding="utf-8", newline="\n").write(text)
    print("AST_PATCHED", os.path.basename(path), "appended=", added)


def main():
    for ext in ("fgx", "geo", "wig"):
        shutil.copy2(os.path.join(STAGE, "LEAD_Jinhsi_QYQXP." + ext),
                     os.path.join(PROJ, "Geometries", "LEAD_Jinhsi_QYQXP." + ext))
    for name in ANIMS:
        for ext in ("anm", "fgx"):
            shutil.copy2(os.path.join(STAGE, name + "." + ext),
                         os.path.join(PROJ, "Animations", name + "." + ext))
        anm = os.path.join(PROJ, "Animations", name + ".anm")
        t = open(anm, encoding="utf-8").read()
        t2 = wig_re.sub("", t)
        open(anm, "w", encoding="utf-8", newline="\n").write(t2)
        wig = os.path.join(PROJ, "Animations", name + ".wig")
        if os.path.exists(wig):
            os.remove(wig)
    print("ASSETS_SYNCED")
    patch_ast(os.path.join(PROJ, "Assets", "LEAD_JINZ_Jinhsi_QYQXP.ast"), MATS, ANIMS)
    print("ASSEMBLE_DONE")


if __name__ == "__main__":
    main()
