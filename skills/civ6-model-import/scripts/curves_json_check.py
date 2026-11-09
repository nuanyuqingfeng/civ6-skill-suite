#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""曲线 JSON 非空壳校验：numFrames>0 且 curves 非空（等价 wuwa_export 的 TRACKS 校验）。"""
import json
import sys

path = sys.argv[1]
try:
    d = json.load(open(path, encoding="utf-8"))
except Exception as e:
    print("CURVES_JSON_BAD 解析失败 %s" % e)
    sys.exit(1)
nf = int(d.get("numFrames") or 0)
curves = d.get("curves") or {}
if nf <= 0 or not curves:
    print("CURVES_JSON_BAD numFrames=%d curves=%d（空壳）" % (nf, len(curves)))
    sys.exit(1)
print("CURVES_JSON_OK numFrames=%d curves=%d" % (nf, len(curves)))
