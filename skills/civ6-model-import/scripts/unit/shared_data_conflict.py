import argparse
import hashlib
import json
import os
import sys

ROOT = r"D:\documents\My Games\Sid Meier's Civilization VI\Mods"
SUBDIRS = ("SHARED_DATA",)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def collect(mod, mods_root, subdirs):
    base = os.path.join(mods_root, mod, "Platforms", "Windows", "BLPs")
    names = {}
    for sub in subdirs:
        d = os.path.join(base, sub)
        if not os.path.isdir(d):
            continue
        for entry in os.listdir(d):
            names.setdefault(entry, []).append((sub, os.path.join(d, entry)))
    return names


def main():
    parser = argparse.ArgumentParser(
        description="列出两个 mod 部署目录里同名但内容不同的引擎资源条目。引擎按名字全局寻址，"
                    "内容不同时后装载的一方覆盖前者；内容相同只是共用一份，不算冲突。")
    parser.add_argument("--mods", nargs="+", required=True, help="mod 名，取部署目录下的文件夹名")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--subdir", action="append",
                        help="限定子目录，可重复；默认只查 SHARED_DATA。UI / units / vfx 是各 mod 自己的文件容器，"
                             "同名文件不会互相覆盖，传进来只会得到无关告警")
    parser.add_argument("--json")
    args = parser.parse_args()

    subdirs = args.subdir if args.subdir else list(SUBDIRS)
    table = {}
    for mod in args.mods:
        table[mod] = collect(mod, args.root, subdirs)
        print("%-24s 条目 %d" % (mod, len(table[mod])))

    total = 0
    shared = 0
    detail = []
    for i in range(len(args.mods)):
        for j in range(i + 1, len(args.mods)):
            a, b = args.mods[i], args.mods[j]
            common = sorted(set(table[a]) & set(table[b]))
            bad = []
            same = []
            for name in common:
                pa = table[a][name][0][1]
                pb = table[b][name][0][1]
                if digest(pa) == digest(pb):
                    same.append(name)
                else:
                    bad.append(name)
                    detail.append({"name": name, "a": pa, "b": pb})
            shared += len(same)
            total += len(bad)
            print("SHARED %s <> %s = %d（同名同内容，可共存）" % (a, b, len(same)))
            print("CONFLICT %s <> %s = %d（同名异内容）" % (a, b, len(bad)))
            for name in bad:
                print("  %s" % name)

    ok = total == 0
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"mods": args.mods, "subdirs": subdirs,
                       "conflicts": total, "shared": shared, "detail": detail, "ok": ok},
                      fh, ensure_ascii=False, indent=1)
        print("JSON %s" % args.json)
    print("SHARED_DATA_CONFLICT_%s" % ("NONE" if ok else "FOUND"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
