# civ6-modeltool

《文明6》3D 资产链路的公共技能容器：Blender 5.2 + CivModelTool 插件 + 型态键转骨 + civhash + AssetEditor + DllProxy。全部工具随本目录携带，本机任何工程都按同一组路径调用。

本目录是用户级技能（`~/.agents/skills/civ6-modeltool`），不属于 `civ6-modding` 等既有技能合集。

## 目录

| 路径 | 内容 |
| --- | --- |
| `SKILL.md` | 入口：导出 / 型态键转骨 / 清网格 / 排错四个分支，前置约束与热重载流程 |
| `reference/api.md` | 两个设置根的全部字段、30 个 `cmt.*` 算子、导出阶段的执行顺序 |
| `reference/model-requirements.md` | 网格硬性要求、插件不校验的项、导出时的坐标与缩放约定 |
| `reference/troubleshooting.md` | 按报错字符串排序的排查条目 |
| `scripts/preflight.py` | 只读体检，输出 `PREFLIGHT {json}`，有 error 时退出码 1 |
| `tools/blender/` | Blender 5.2.3 LTS 便携版，Python 3.13.13 |
| `tools/blender/blender-5.2.3-windows-x64/portable/` | 偏好与用户插件；插件已启用，偏好随包存放 |
| `tools/vendor/CivModelTool/` | 插件源码快照（GitHub `main`），`tools/vendor/CivModelTool.commit` 记提交号 |
| `tools/civhash/` | `bin/civhash.exe`、`cli/` 源码、LICENSE、NOTICE |
| `tools/asseteditor/` | AssetEditor 增强版 1.1 |
| `tools/dllproxy/version.dll` | 模型上限翻倍代理，DX11 |

## 工具

| 工具 | 版本 | 用途 |
| --- | --- | --- |
| Blender | 5.2.3 LTS | 建模、绑定、动画，承载导出插件 |
| CivModelTool | 1.0.0（`main` @ 7ffafcf） | 导出 `.fgx` 模型与动画、`.ast`、材质贴图、ArtDef；型态键转骨骼；网格清理；按骨骼上限分割 |
| civhash | `main` | Civ 风格 CRC32、引擎 FNV-1a、骨骼链 hash、按前缀反推后缀 |
| AssetEditor | 1.1 | 生成并维护 Civ6 工程目录树、`.ast`/`.artdef` 编辑、热更新 |
| DllProxy | 1.0 | 把模型上限提高一倍（仅 DX11），放入游戏 `Base/Binaries/Win64Steam` |

## 调用

带偏好启动（插件已启用）：

    tools\blender\blender-5.2.3-windows-x64\blender.exe

无头跑一趟体检：

    tools\blender\blender-5.2.3-windows-x64\blender.exe -b --factory-startup --python scripts\preflight.py -- --out report.json

`--factory-startup` 不读偏好，脚本里先 `addon_utils.enable("CivModelTool")`。

hash 计算与反推：

    tools\civhash\bin\civhash.exe TERRAIN_COAST --json
    tools\civhash\bin\civhash.exe --reverse 0x16D22538 --prefix TERRA --max 2

## 本机验收

| 项目 | 结果 |
| --- | --- |
| Blender 归档 sha256 | `723f08a4401502561eb763cdeacf8745b31e5f3f154d287d3830d97cf75dc2fb`，与官方 `blender-5.2.3.sha256` 一致 |
| 解释器 | Python 3.13.13，与 `cmt_exporter/libs/_cffi_backend.cp313-win_amd64.pyd` 一致 |
| 插件注册 | 30 个 `cmt.*` 算子；`scene.CMT.ExporterSettings` 与 `scene.CMT.S2BSettings` 均可读 |
| preflight（空场景） | 退出码 1，报出「导出阶段全关」「ProjectPath 为空」两条 error |
| preflight（构造场景） | 退出码 0，`errors=0` |
| 端到端导出 | `{'FINISHED'}`，写出 `Geometries/smoke_geo.fgx`（10624 字节）与 `Assets/smoke_ast.ast`（1038 字节） |
| 动画导出 | 带骨骼关键帧的动作导出 `Animations/smoke_anim.fgx`（5284 字节） |
| AssetEditor 启动 | 从 `tools/asseteditor/AssetEditor/AssetEditor.exe` 启动，进程驻留、占用 132 MB，随即终止 |
| 领袖规模导出 | 256 骨骼 + `Standard_Leader`（58 个动作槽）场景：preflight `errors=0`，导出 `leader_geo.fgx`（21612 字节）与 `leader_ast.ast`（2714 字节） |
| civhash 向量 | `123456789` → `raw=0x340BC6D9`；`Idle` + `Root/Spine/Head` → `0xFF0361A1` |

## 已知限制

Blender 5.2 移除了 `Action.fcurves`，插件的型态键转骨模块仍按旧接口读取，`cmt.s2b_ot_convert` 在 5.2 上抛 `AttributeError: 'Action' object has no attribute 'fcurves'`。受影响位置：

- `cmt_shapekey_to_bone/operations.py:58`、`:250`、`:319`
- `cmt_shapekey_to_bone/utils.py:56`
- `cmt_shapekey_to_bone/panels.py:18`
- `cmt_shapekey_to_bone/properties.py:5`

导出链路（模型、动画、Ast）已按新接口实现，不受影响。

## 维护

- 更新插件：把新源码放进 `tools/vendor/CivModelTool`，再覆盖到 `tools/blender/blender-5.2.3-windows-x64/portable/scripts/addons/CivModelTool`。不要调 `cmt.updater_run`，它会用远端 `main` 覆盖整个插件目录。
- 更新 Blender：整目录替换 `tools/blender/`，保留 `portable/` 里的偏好与插件。
- AssetEditor 增强版按作者说明覆盖 SDK 原版；本容器只保留解压结果，覆盖动作由使用者决定。
- `version.dll` 只在需要突破模型上限时装进游戏目录。

## 来源

- CivModelTool：`Sumcam-L/CivModelTool`，基于 Deliverator 的 CivNexus6
- civ6-modeltool-skill：`Sumcam-L/civ6-modeltool-skill`（本容器主体）
- dsh-civhash：`Sumcam-L/dsh-civhash`，BSD-3-Clause，NOTICE 中有 CivNexus6 署名
- AssetEditor：`Sumcam-L/AssetEditor` 1.1
- DllProxy：`Sumcam-L/DllProxy` 1.0
- Blender：5.2.3 LTS，GPL
