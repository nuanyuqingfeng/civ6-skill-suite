#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""曲线来源指纹 manifest：文件数/字节/sha8/轨道数，供 expr_route_gate 与报告引用。"""
import glob
import hashlib
import json
import os
import sys


def sha8(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


char, out = sys.argv[1], sys.argv[2]
entries = []
total_tracks = 0
for path in sorted(glob.glob(os.path.join(out, "curves", "*.uecurves.json"))):
    if os.path.getsize(path) == 0:
        continue
    d = json.load(open(path, encoding="utf-8"))
    tracks = len(d.get("curves") or {})
    total_tracks += tracks
    entries.append({"file": os.path.basename(path),
                    "bytes": os.path.getsize(path), "sha8": sha8(path),
                    "objectPath": d.get("objectPath"), "codec": d.get("codec"),
                    "numFrames": int(d.get("numFrames") or 0), "fps": d.get("fps"),
                    "tracks": tracks})

manifest = {"character": char, "root": out, "file_count": len(entries),
            "tracks_total": total_tracks, "files": entries,
            "total_bytes": sum(e["bytes"] for e in entries)}
target = os.path.join(out, "manifest.json")
json.dump(manifest, open(target, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("CURVES_MANIFEST %s" % target)
print("CURVES_SUMMARY char=%s files=%d tracks=%d bytes=%d"
       % (char, len(entries), total_tracks, manifest["total_bytes"]))
