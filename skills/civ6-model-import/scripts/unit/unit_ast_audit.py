import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

def local(tag):
    return tag.split("}")[-1].split(".")[-1]

def text_of(elem):
    """Civ6 AST 的取值写在 text 属性上，例如 <m_SlotName text="IDLE_A"/>。"""
    if elem is None:
        return None
    v = elem.get("text")
    if v is None and elem.text:
        v = elem.text
    return (v or "").strip()

def read_anm_durations(anim_dir):
    out = {}
    for f in sorted(os.listdir(anim_dir)):
        if not f.lower().endswith(".anm"):
            continue
        p = os.path.join(anim_dir, f)
        text = open(p, encoding="utf-8-sig", errors="replace").read()
        m_dur = re.search(r"<m_fDuration>([0-9.eE+-]+)</m_fDuration>", text)
        m_name = re.search(r'<m_Name text="([^"]+)"', text)
        if not m_dur:
            continue
        name = m_name.group(1) if m_name else os.path.splitext(f)[0]
        out[name] = float(m_dur.group(1))
    return out

def read_fgx_names(anim_dir):
    return {os.path.splitext(f)[0] for f in os.listdir(anim_dir) if f.lower().endswith(".fgx")}

def parse_ast(path):
    return ET.parse(path)

def ast_profile(path):
    """返回 (类名, DSG, 时间线条数)，用于在没有显式 --ast 时自动挑出单位 AST。"""
    root = ET.parse(path).getroot()
    cls = dsg = ""
    timelines = 0
    for e in root.iter():
        t = local(e.tag)
        if t == "m_ClassName" and not cls:
            cls = text_of(e)
        elif t == "m_dsgName" and not dsg:
            dsg = text_of(e)
        elif t == "m_timelines":
            for sub in e.iter():
                if local(sub.tag) == "m_Timelines":
                    timelines += sum(1 for x in list(sub) if local(x.tag) == "Element")
    return cls, dsg, timelines

def pick_unit_ast(asset_dir):
    """在 Assets 下挑出单位 AST：类名为 Unit 且带时间线的优先，其次看动画绑定数。

    不依赖文件名、不依赖大小写、不依赖前后缀。
    """
    cands = []
    for f in sorted(os.listdir(asset_dir)):
        if not f.lower().endswith(".ast"):
            continue
        p = os.path.join(asset_dir, f)
        try:
            cls, dsg, tl = ast_profile(p)
        except ET.ParseError:
            continue
        root = ET.parse(p).getroot()
        binds = len(anim_bindings(root))
        cands.append((cls, tl, binds, p))
    if not cands:
        raise SystemExit("Assets 下没有可解析的 .ast")
    units = [c for c in cands if c[0] == "Unit" and c[1] > 0]
    pool = units or sorted(cands, key=lambda c: (c[1], c[2]), reverse=True)
    pool = sorted(pool, key=lambda c: (c[1], c[2]), reverse=True)
    best = pool[0]
    if len(cands) > 1:
        print("AST_CANDIDATES %d -> 选中 %s (class=%s timelines=%d binds=%d)"
              % (len(cands), os.path.basename(best[3]), best[0], best[1], best[2]))
    return best[3]

def timeline_entries(root):
    """返回 [(slot_name, anim_name, duration_text)]，按 m_timelines 段顺序。

    不依赖固定顺序：在 m_AnimationName 之后找同一条时间线对象的 m_fDuration。
    时间线是 m_timelines 的直接子元素，因此按子元素逐个数更稳。
    """
    entries = []
    for tl in root.iter():
        if local(tl.tag) != "m_timelines":
            continue
        container = None
        for sub in tl.iter():
            if local(sub.tag) == "m_Timelines":
                container = sub
                break
        if container is None:
            container = tl
        for item in list(container):
            if local(item.tag) != "Element":
                continue
            name = anim = dur = None
            for ch in item:
                t = local(ch.tag)
                if t == "m_Name" and name is None:
                    name = text_of(ch)
                elif t == "m_AnimationName":
                    anim = text_of(ch)
                elif t == "m_fDuration":
                    dur = text_of(ch)
            if anim or name:
                entries.append((name, anim, dur))
    return entries

def anim_bindings(root):
    pairs = []
    for item in root.iter():
        if local(item.tag) != "m_animationBindings":
            continue
        for e in item.iter():
            if local(e.tag) != "Element":
                continue
            slot = anim = None
            for ch in e.iter():
                t = local(ch.tag)
                if t == "m_SlotName":
                    slot = text_of(ch)
                elif t == "m_AnimationName":
                    anim = text_of(ch)
            if slot or anim:
                pairs.append((slot, anim))
        break
    return pairs

def fill_durations(ast_path, anim_dir, write):
    durs = read_anm_durations(anim_dir)
    if not durs:
        raise SystemExit("%s 下没有任何 .anm" % anim_dir)
    lines = open(ast_path, encoding="utf-8").read().splitlines(keepends=True)
    start = None
    for i, l in enumerate(lines):
        if "<m_timelines>" in l:
            start = i
            break
    if start is None:
        raise SystemExit("AST 里找不到 <m_timelines>")
    cur = None
    changed = 0
    missing = []
    for i in range(start, len(lines)):
        m = re.search(r'<m_AnimationName text="([^"]+)"/>', lines[i])
        if m:
            cur = m.group(1)
            continue
        m2 = re.search(r"<m_fDuration>([0-9.eE+-]+)</m_fDuration>", lines[i])
        if m2 and cur:
            want = durs.get(cur)
            if want is None:
                missing.append((i + 1, cur))
            elif abs(want - float(m2.group(1))) > 1e-6:
                lines[i] = lines[i].replace(
                    m2.group(0), "<m_fDuration>%f</m_fDuration>" % want)
                changed += 1
            cur = None
    if write and changed:
        open(ast_path, "w", encoding="utf-8", newline="").write("".join(lines))
    return changed, missing

def main():
    ap = argparse.ArgumentParser(description="单位 AST 审计：绑定完整性、时长一致性、引用闭合；可回填时长")
    ap.add_argument("project", help="工程根，例如 D:/.../UnitRover")
    ap.add_argument("--ast", default=None, help="AST 路径，默认取 Assets 下 Class=Unit 的第一个 .ast")
    ap.add_argument("--anim-dir", default=None, help="片段目录，默认 <project>/Animations")
    ap.add_argument("--fill", action="store_true", help="把时间线时长按 .anm 实际值回填")
    ap.add_argument("--write", action="store_true", help="配合 --fill 真正写盘，否则只报告")
    ap.add_argument("--json", default=None, help="把结果写成 JSON 到该路径")
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    anim_dir = args.anim_dir or os.path.join(project, "Animations")
    ast = args.ast
    if ast is None:
        ast = pick_unit_ast(os.path.join(project, "Assets"))
    print("AST %s" % ast)
    print("ANIM_DIR %s" % anim_dir)

    durs = read_anm_durations(anim_dir)
    fgx = read_fgx_names(anim_dir)
    print("ANM %d  FGX %d" % (len(durs), len(fgx)))

    tree = parse_ast(ast)
    root = tree.getroot()
    dsg = None
    for e in root.iter():
        if local(e.tag) == "m_dsgName":
            dsg = text_of(e)
            break
    print("DSG %s" % dsg)

    binds = anim_bindings(root)
    empty_bind = [(s, a) for s, a in binds if not a]
    print("BINDINGS %d  EMPTY %d" % (len(binds), len(empty_bind)))

    entries = timeline_entries(root)
    print("TIMELINES %d" % len(entries))

    bad_ref = []
    bad_dur = []
    zero = []
    for name, anim, dur in entries:
        if anim and anim not in fgx and anim not in durs:
            bad_ref.append((name, anim))
        d = float(dur) if dur else 0.0
        if d <= 0.0:
            zero.append((name, anim))
        elif anim in durs and abs(d - durs[anim]) > 1e-3:
            bad_dur.append((name, anim, d, durs[anim]))
    print("REF_MISSING %d %s" % (len(bad_ref), bad_ref[:10]))
    print("DUR_MISMATCH %d %s" % (len(bad_dur), bad_dur[:10]))
    print("ZERO_DUR %d %s" % (len(zero), zero[:10]))

    changed = 0
    missing = []
    if args.fill:
        changed, missing = fill_durations(ast, anim_dir, args.write)
        print("FILL_CHANGED %d  FILL_MISSING %d %s" % (changed, missing[:5] and len(missing) or 0, missing[:5]))
        if not args.write:
            print("FILL_DRYRUN 未写盘，加 --write 生效")

    ok = not bad_ref and not bad_dur and not zero and not empty_bind
    result = {
        "ast": ast,
        "dsg": dsg,
        "bindings": len(binds),
        "bindings_empty": len(empty_bind),
        "timelines": len(entries),
        "ref_missing": bad_ref,
        "dur_mismatch": bad_dur,
        "zero_dur": zero,
        "fill_changed": changed,
        "fill_missing": missing,
        "ok": ok,
    }
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=1)
        print("JSON %s" % args.json)
    print("AST_AUDIT_%s" % ("OK" if ok else "FAIL"))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
