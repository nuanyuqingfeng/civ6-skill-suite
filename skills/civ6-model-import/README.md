# civ6-model-import 技能包（完整分发版）

把 UE 工程的 psk 模型与 ueanim 动画导入文明6作为领袖 3D 模型的执行依据与工具包。含十步流程、五条采信判据、面部形态键转面骨与循环拼接判据、**面部三层闸门（几何蒙皮 / 曲线权重 / 闭眼通道）**、**失败归因纪律与治标补丁生命周期**、115 条错误处置、成功案例的完整参数、跨会话交接模板，以及随包分发的转换工具链与脚本。鸣潮素材的专有知识单独成章，分享版自动剔除。

## 目录

| 路径 | 内容 |
|------|------|
| `SKILL.md` | 入口：分工、参数槽位、开工自检、任务分流、十步流程、协作契约、随包与上游清单 |
| `references/open-model.md` | 打开模型：两阶段自举独立 GUI 启动器、三种调用方式、硬性验收判据、故障树、禁止事项（只读查看任务，不 cook 不部署） |
| `references/success-case.md` | 成功案例的完整参数与实测值（定稿参数、采信判据前四条、Q/p_Q、命令序列、cook 判据、表情口型） |
| `references/pipeline.md` | 每一步的命令与参数 |
| `references/acceptance.md` | 五条采信判据、仪器自检、Q/p_Q 标定、形态键转面骨、循环插入接缝、两次闸门、伪失败码 |
| `references/face-skin-gate.md` | 几何蒙皮闸门：三层各管什么、三项必查与判据、两种统计口径、跨版本补权重、红旗清单 |
| `references/expression-route.md` | 表情数据链 A 路线硬闸门：全链七步、决策状态机（A/询问/ABSTAIN）、A2 局部补位边界、报告固定字段 |
| `references/unpack-expression-curves.md` | 官方曲线补导：ueasset curves 链路、四个已实证的坑、来源指纹与配套校验 |
| `references/blink-and-eyelids.md` | 闭眼：三层驱动优先级、`E_Close` 不走拟合层、短脉冲/长闭眼分类、合成后限幅、下睑轴向陷阱、验收口径 |
| `references/morph-curves.md` | 官方表情曲线 → 逐帧权重表：白名单与排除、帧对齐实测、拼接与冻结段、互补混合、双实现校验 |
| `references/ast-anim-binding.md` | `.ast` 四处容器引用增删/降级、两种语义区别、保留文件的恢复路径、验收 |
| `references/leader-animation-sequence.md` | 领袖动画播放语义：一次性入场 → 循环待机、LeaderAnimations 序列表与 Lua 队列证据、三条落地路线、最小验证实验、红旗清单 |
| `references/misattribution.md` | 失败归因纪律：案例矩阵、五个触发器、四个取证动作、证据分级、黑箱标定卡 |
| `references/patch-lifecycle.md` | 治标补丁：准入四问、五个停止信号、四类处置、A/B 三步、台账、脚本形态约束 |
| `references/gotchas.md` | 115 条技术错误与处置，简表 |
| `references/handover.md` | 跨会话交接六要素与接手动作 |
| `references/upstream.md` | 分发范围、上游地址、部署命令、核验说明 |
| `references/texture-pass.md` | 贴图侧五道闸门：基色来源、掩膜 DDS 头字段、UV 岛定位、调色曲线、自适应分辨率档位与预览 |
| `references/texture-classes.json` | 54 个贴图类别的像素格式、mip 策略、采样参数与尺寸范围，供 `texpair_check.py` 校验 |
| `references/wuwa-notes.md` | 鸣潮素材专章：解包、骨名、片段语义、二次运动层、贴图、单位侧、完整性边界。分享版删除本文件 <!-- WUWA --> |
| `scripts/open_model_launcher.cmd` + `scripts/_open_detached.cmd` | 两阶段自举启动器（分发模板）：入口投递 explorer、执行器启动 Blender，窗口脱离 agent 会话；双击=默认模型，拖放=指定模型 |
| `scripts/cook_sweep.sh` | 全 XLP cook 扫描与九类告警计数 |
| `tools/CivNexus6/` | 转换工具链：`NexusBatch.exe`、`CivNexus6.exe`、16 个读数工具、全部依赖程序集（35 MB） |
| `scripts/` | `jx_build5.py` 及其依赖模块 `jx_r3_face.py`、`jx_morph_face.py`、`jx_hair_rib.py`、`jx_secondary.py`、`jx_r5_bangs.py`，`jx_assemble.py`、`jx_ast_normalize.py`、`jx_cook.sh`，接缝诊断 `jx_diag_track.py`、`jx_diag_idle_velocity.py`、`jx_diag_spike.py`、`jx_probe_insert.py`；`scripts/archive/` 下 142 个一次性诊断采样脚本（`jx_r3*`…`jx_r16*`、`jx13*`、`jx14*`、`jx_portrait*`、`jx_pmx*`、`jx_voice*`、`jx_wpn*`，不再新增） |
| `scripts/csharp/` | 读数工具与 `NexusBatch` 的 C# 源码 |
| `scripts/`（面部与归因） | `expr_route_gate.py`（G0 曲线来源探测 + A/B 路线状态机，退出码 0/10/11/12）、`face_expr_runtime.py`（curve_blink 长短分层/互补混合/让位/下睑保底/限幅）、`unpack_expr_curves.sh` + `curves_json_check.py` + `curves_manifest.py`（官方曲线补导与来源指纹）、`face_skin_gate.py`（几何蒙皮 + 动画轨迹 + 装配一致 三合一闸门，`--code-map`/`--geo-pattern` 参数化定位，`--inject` 五项供反向自检）、`dump_tracks.py`（逐帧骨头导出与绝对 min–max 摘要）、`morph_curves.py`（官方曲线 → 逐帧权重表 + 双实现 MAE 校验，`--require-source` 默认开）、`ast_bind.py`（`.ast` 四处容器引用增删/降级）、`gate_selftest.py`（反向闸门自检，默认五注入）、`_patch_template.py`（治标补丁模板）。读数类需 `--meshtable` / `--dump` 指向读数 exe |
| `patches/UAnimSequence.cs` | ACL 动画解码补丁 | <!-- WUWA -->
| `MANIFEST.sha256` | 全包 384 个文件的 sha256 清单（`references/community/Nexus-Buddy-2-Blender-Scripts` 是独立子模块，`scripts/tmp/` 是探针运行产物，两者整目录排除、不逐文件入清单），`sha256sum -c MANIFEST.sha256` 校验 |

## 安装

```bash
cp -r civ6-model-import "/c/Users/<用户名>/.agents/skills/"
cp -r civ6-model-import/tools/CivNexus6 "/e/SoftWares/civ6_nexus_work/CivNexus6"
sha256sum civ6-model-import/references/*.md
```

第二条把工具链部署到工程树之外；`tools/CivNexus6` 里的未签名 exe 在 `D:\documents` 树内会被按映像拦截（err=5）。

## 首次使用

1. 打开 `SKILL.md` 第二节，把九个参数槽位替换成本机实际路径。
2. 跑第三节的六条自检命令，全部输出通过标记再开工。
3. 缺插件时按 `references/upstream.md` 第二节逐条获取；工具链已在包内，无需下载。

## 分发说明

- 包内不含游戏资产、密钥与工程文件；FModel 的 AES 密钥存于其自身 `AppSettings.json`，不随包分发。
- `tools/CivNexus6` 内的 Firaxis/Granny/FBX 程序集来自 CivNexus6 的构建产物，随包分发遵循其上游许可。
- 文档中的绝对路径是本机实测值（`E:\SoftWares`、`F:\Steam`、`D:\documents`），换机器只改这些前缀。
- 判据阈值来自达妮娅工程正样本实测；新机器先用正样本复跑四条判据，正样本通不过的阈值按 `acceptance.md` 的规则作废。
<!-- WUWA:BEGIN -->
- 生成分享版：`python scripts/pack_share.py --src . --out ../civ6-model-import-share`。脚本删除鸣潮专章与全部 `WUWA` 标记，按 `scripts/share_terms.tsv` 把案例角色名换成匿名代号，重建 `MANIFEST.sha256`，最后做泄露扫描，命中即退出码 2。`--keep-names` 只剔除专章、保留案例名（本机自用档）。
<!-- WUWA:END -->
- 版本：2026-11-06b（官方短脉冲接管眨眼口径 SHORT_PULSES_DRIVE（默认关，御三家不受影响）+ IDLE 循环铺段；上一版同日表情数据链 A 路线硬闸门：`expression-route.md`/`unpack-expression-curves.md`、`expr_route_gate.py`/`face_expr_runtime.py`/`unpack_expr_curves.sh` 三新脚本、`morph_curves.py` 段边界/冻结取值/白名单 Aa 口径修正与 `--require-source`、`face_skin_gate.py` 去硬编码与退出码判据、`gate_selftest.py` 默认五注入；上一版 2026-11-04 面部三层闸门）。
