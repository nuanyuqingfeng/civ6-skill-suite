# 补导官方表情曲线（ueasset curves）

> A 路线的数据入口。领袖 `curves/` 目录缺失或命中为空时，先走本文补导，再跑 `expr_route_gate.py probe` 复核；补导后仍无命中才允许进入询问协议（`expression-route.md` §三）。

## 一、链路

```bash
scripts/unpack_expr_curves.sh <角色目录名> <体型/资产目录名> <资产前缀> [额外前缀...]
# 例（御三家）：
unpack_expr_curves.sh 角色_Yangyang FemaleM/Yangyang R2T1YangyangMd10011
# 例（丹瑾，含外交候选 52 条 DialogAnim）：
unpack_expr_curves.sh 角色_DanJin FemaleM/Danjin R2T1MicaiMd10011 DialogAnim/FemaleM/Danjin
```

步骤：钉版 exe 依赖检查 → 挂载诊断（`open`）→ `find` 枚举 `CommonAnim/UiAnim` 与额外前缀的 `.uasset` → 逐条 `curves <anim> --out curves --json` → 双重断言 → `curves_manifest.py` 写来源指纹 `curves/manifest.json`。

产物：`G:/Wuwa_3D_Assets/Characters/<角色目录名>/curves/*.uecurves.json`（ACL 解压的 AnimCurve，`{numFrames, fps, objectPath, codec, curves:{名:{times,values}}}`）+ `manifest.json`（文件数/字节/sha8/轨道数）。

## 二、四个已实证的坑（脚本已内建防御，换工具时逐条复验）

| 坑 | 现象 | 防御 |
|---|---|---|
| 退出码只看「作业跑完」 | 0/N 成功也返回 0；旧 exe / 换新构建坑会回来 | 每条解析响应 JSON 的 `results[].success`，非 true 记失败；退出码只作参考 |
| 空壳产物 | 文件存在但 `numFrames=0` 或 `curves={}` | 等价 `wuwa_export.ueanim_ok` 的 TRACKS 校验：`curves_json_check.py` 要求 numFrames>0 且 curves 非空 |
| `@plan.txt` 批量语法静默失败 | 传 @ 批量文件后无产物、无报错 | **禁止 @ 批量语法**，逐条显式传参（while-read 循环），逐条断言 |
| 裸拷 exe | "Unable to load DLL" 每条失败但退出码仍 0 | 启动前检查 `CUE4Parse-Natives.dll`、`oo2core_9_win64.dll` 与 exe 同目录（钉版 `G:/Wuwa_3D_Assets/_tools/bin/ueasset-*/` 整目录） |

配套的 `wuwa_export.py`（模型/贴图/动画批量导出）同口径：按 `results[].success` 判定、不按退出码；ueanim 产物有 TRACKS 空壳校验。

## 三、配套校验

1. `curves/manifest.json` 指纹入报告（文件数/sha8/轨道数）。
2. `scripts/expr_route_gate.py probe --curves-dir <curves> --morph-keys <形态键清单> --fit-table <拟合表bones>`：严格命中 = 曲线名 ∩ 形态键清单 ∩ 拟合表 bones>0，命中 0 → 询问协议。
3. 命中 > 0 → `scripts/morph_curves.py build/verify` 生成权重表（双实现 MAE=0；targets 的 `source` 用身体动画保持帧）。

## 四、与既有资产的关系

- 模型（含形态键 MRPHINFO/MRPHDATA）与 .ueanim 身体动画走 `unpack_leader.sh`/`wuwa_export.py`，与曲线解包互不覆盖；
- 曲线 fps 30.10–30.86 浮动是派生值，帧对齐一律用 `numFrames-1` 与 targets `source`，不用 fps 反算（`morph-curves.md` §四）；
- 白芷类角色 `Eye01…10`/`Pupil01…` 是眼球材质参数、`morpher_*` 值域非权重，白名单已排除，命中 0 不是异常。
