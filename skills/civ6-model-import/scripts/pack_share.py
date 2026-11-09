"""生成 civ6-model-import 的分享版。

做四件事：删除专有素材知识（专章文件、patches、ACL 补丁脚本、匿名词表本身），
删除 `<!-- WUWA:BEGIN -->` 块与 `<!-- WUWA -->` 行尾标记，按词表把案例角色名
换成匿名代号，重建 MANIFEST 并做泄露扫描。

用法：
    python scripts/pack_share.py --src . --out ../civ6-model-import-share
    python scripts/pack_share.py --src . --out ../share --keep-names   # 只剔专章
    python scripts/pack_share.py --src . --out ../share --strict       # 脚本层也硬失败

退出码：0 成功；2 泄露扫描有命中；3 参数或路径不合法。
"""

import argparse
import hashlib
import os
import re
import shutil
import sys

TEXT_EXT = {
    ".md", ".py", ".ps1", ".sh", ".json", ".tsv", ".txt", ".cfg", ".cs",
    ".bat", ".cmd", ".xml", ".civ6proj", ".modinfo", ".ini", ".yaml", ".yml",
}

COPY_IGNORE = shutil.ignore_patterns(
    ".git", "__pycache__", "*.pyc", "tmp", ".pytest_cache",
)

# 分享版不携带的路径（相对技能根）
DROP_PATHS = [
    "references/wuwa-notes.md",
    "patches",
    "scripts/build_acl_patch.ps1",
    "scripts/share_terms.tsv",
    "scripts/pack_share.py",
]

BEGIN = "<!-- WUWA:BEGIN -->"
END = "<!-- WUWA:END -->"
LINE = "<!-- WUWA -->"

# 文档层硬判据；脚本层默认只告警，脚本里本来就有工程常量
DOC_GLOBS = ("SKILL.md", "README.md", "references")
LEAK_WORDS = [
    "鸣潮", "Wuwa", "wuwa", "Wuthering", "Kuro", "R2T1", "Md10011", "Md20011",
    "Jinxi", "jinxi", "Jinhsi", "jinhsi", "Jinzhou", "今汐", "守岸人", "漂泊者",
    "女漂", "男漂", "御三家", "RibbonAnim", "UiAnim", "Stand1_Action", "Cos_Pose",
    "声痕", "wuwa-notes", "Rover", "rover", "ZcodeWorkPlace",
]


def load_terms(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.rstrip("\n")
            if not line or i == 0:
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                raise SystemExit("词表第 %d 行不是三列：%s" % (i + 1, line))
            rows.append(tuple(parts))
    return rows


def strip_markers(text):
    out = []
    removed = 0
    inside = False
    for line in text.splitlines(keepends=True):
        s = line.strip()
        if s == BEGIN:
            inside = True
            removed += 1
            continue
        if s == END and inside:
            inside = False
            removed += 1
            continue
        if inside:
            removed += 1
            continue
        if LINE in line:
            removed += 1
            continue
        out.append(line)
    text = "".join(out)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text, removed


def split_frontmatter(text):
    if not text.startswith("---"):
        return "", text
    lines = text.splitlines(keepends=True)
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            head = "".join(lines[: i + 1])
            return head, "".join(lines[i + 1:])
    return "", text


def apply_terms(text, terms):
    front_rules = [(p, r) for s, p, r in terms if s == "FRONTMATTER"]
    all_rules = [(p, r) for s, p, r in terms if s == "ALL"]
    all_rules.sort(key=lambda x: len(x[0]), reverse=True)

    head, body = split_frontmatter(text)
    count = 0
    for pat, rep in front_rules:
        if pat in head:
            count += head.count(pat)
            head = head.replace(pat, rep)
    for pat, rep in all_rules:
        if pat in head:
            count += head.count(pat)
            head = head.replace(pat, rep)
        if pat in body:
            count += body.count(pat)
            body = body.replace(pat, rep)
    text = head + body
    # 替换后可能留下「案例甲 的」这种西文空格，收敛成中文习惯的写法
    text = re.sub(r"(案例[甲乙丙丁戊己庚](?:工程)?|单位[甲乙丙]|多角色案例|正样本|多角色工程)\s+的", r"\1的", text)
    return text, count


def walk_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "tmp", ".pytest_cache")]
        for name in filenames:
            yield os.path.join(dirpath, name)


def leak_scan(root, strict_scripts):
    hits = []
    for path in walk_files(root):
        rel = os.path.relpath(path, root).replace("\\", "/")
        if rel == "scripts/share_terms.tsv" or rel == "scripts/pack_share.py":
            continue
        is_doc = rel in ("SKILL.md", "README.md") or rel.startswith("references/")
        if not is_doc and not strict_scripts:
            continue
        if os.path.splitext(path)[1].lower() not in TEXT_EXT:
            continue
        try:
            data = open(path, encoding="utf-8").read()
        except UnicodeDecodeError:
            continue
        for no, line in enumerate(data.splitlines(), 1):
            for word in LEAK_WORDS:
                if word in line:
                    hits.append((rel, no, word, line.strip()[:100]))
                    break
    return hits


def rebuild_manifest(root):
    skip_dirs = {".git", "__pycache__", "tmp", ".pytest_cache"}
    skip_prefix = "references/community/Nexus-Buddy-2-Blender-Scripts/"
    entries = []
    for path in walk_files(root):
        rel = os.path.relpath(path, root).replace("\\", "/")
        if rel == "MANIFEST.sha256" or rel.startswith(skip_prefix):
            continue
        if any(part in skip_dirs for part in rel.split("/")):
            continue
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        entries.append("%s *./%s" % (h, rel))
    entries.sort()
    with open(os.path.join(root, "MANIFEST.sha256"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(entries) + "\n")
    return len(entries)


def main():
    ap = argparse.ArgumentParser(description="生成 civ6-model-import 分享版")
    ap.add_argument("--src", default=".", help="技能根目录")
    ap.add_argument("--out", required=True, help="输出目录，必须不存在或为空")
    ap.add_argument("--keep-names", action="store_true", help="只剔除专章，保留案例名")
    ap.add_argument("--strict", action="store_true", help="脚本层泄露也按失败处理")
    args = ap.parse_args()

    src = os.path.abspath(args.src)
    out = os.path.abspath(args.out)
    if not os.path.isfile(os.path.join(src, "SKILL.md")):
        print("SRC_NOT_SKILL: %s" % src)
        return 3
    if os.path.exists(out) and os.listdir(out):
        print("OUT_NOT_EMPTY: %s" % out)
        return 3

    terms_path = os.path.join(src, "scripts", "share_terms.tsv")
    terms = [] if args.keep_names else load_terms(terms_path)

    shutil.copytree(src, out, ignore=COPY_IGNORE, dirs_exist_ok=True)

    dropped = []
    for rel in DROP_PATHS:
        target = os.path.join(out, rel)
        if os.path.isdir(target):
            shutil.rmtree(target)
            dropped.append(rel + "/")
        elif os.path.isfile(target):
            os.remove(target)
            dropped.append(rel)

    files = 0
    stripped = 0
    replaced = 0
    for path in walk_files(out):
        if os.path.splitext(path)[1].lower() not in TEXT_EXT:
            continue
        try:
            text = open(path, encoding="utf-8").read()
        except UnicodeDecodeError:
            continue
        new, n = strip_markers(text)
        if terms:
            new, m = apply_terms(new, terms)
            replaced += m
        if new != text:
            open(path, "w", encoding="utf-8", newline="\n").write(new)
            files += 1
            stripped += n

    count = rebuild_manifest(out)
    hits = leak_scan(out, args.strict)

    print("PACK_OUT %s" % out)
    print("PACK_DROPPED %d %s" % (len(dropped), ",".join(dropped)))
    print("PACK_FILES_CHANGED %d  标记行删除 %d  名词替换 %d" % (files, stripped, replaced))
    print("PACK_MANIFEST %d 条" % count)
    print("LEAK_HITS %d" % len(hits))
    for rel, no, word, line in hits[:40]:
        print("  %s:%d  [%s]  %s" % (rel, no, word, line))
    if hits:
        print("PACK_FAIL 泄露扫描有命中；补标记或补词表后重跑")
        return 2
    print("PACK_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
