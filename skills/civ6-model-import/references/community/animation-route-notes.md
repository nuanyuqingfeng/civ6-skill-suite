# 综合笔记：Civ6 动画进出的社区成熟路线（对 skill FBX 反解链的对照）

> 依据：art-assets-guide-extract.md、civnexus6-tool-extract.md、Sukritact/Nexus-Buddy-2-Blender-Scripts 源码（本地克隆）、CivFanatics 线索帖。
> 采集日期：2026-11-01。本笔记修正上一轮调研的一个假设，结论以本页为准。

## 关键事实（按证据强度排列）

1. **na2 是单向读入通道，不是双向交换。**
   社区 Blender 2.8+ 配套脚本是 `io_import_na2.py`（本地克隆 `Nexus-Buddy-2-Blender-Scripts/Blender-2.8-Addons/io_import_na2.py`），文件内只有 `import_na2(path)` 与导入 operator，无导出。CivNexus6 资源页口径也是 ".na2 export for animations ... importable into Blender via the companion scripts"。
   → 用途边界：把原版领袖 .fgx/.anm 动画读进 Blender 做参照/比对/复用评估；不能用它把 Blender 动画送回引擎。

2. **往 Civ6 塞"自定义动画"的社区成熟路径是 Civ5 老链**：
   Blender 2.49（FBX 6.1 导出）→ Nexus Buddy 2（读该 FBX）→ .gr2/.br2 动画 → CivNexus6（重存/批转）→ .fgx/.anm。
   原文（指南）："the Civ 5 pipeline (Blender 2.49 + FBX + Nexus Buddy 2) is going to be the only way of getting custom animations into Civ 6."
   同时 Civ6 自带 FBX 导入 "seems useless"，Deliverator 本人在 2017-03 用 .fbx 导自定义动画即撞旋转问题。

3. **复用原版动画不经过任何导入**：Civ5 .gr2 动画在 Civ6 原样可用（改名 .fgx + 生成 .anm 即可）；在 Civ6 内部则是"复制原版 .ast 只改绑定/交叉混用动画集"。骨架命名一致时零重定向。

4. **旋转/scale 类问题在社区同样是 FBX 环节的老病**（旋转修正帖用 NA2+Blender 3.4 修；指南记 "Rotation problems..."）。skill 的 Q/p_Q、EPS=0.01°、`arm_c.scale=0.01`、identity 通道右乘 R_z(180°) 全部产生于"Blender 4.5 FBX → 自研 C# 导入器（NexusBatch fork）"这一段，与社区病灶同源，但社区用换链（2.49+NB2）或绕链（复用原版动画/ast）解决，skill 用逐骨标定硬解。

## 对 skill 现三条动画相关路线的判定

| skill 现状 | 社区对应 | 判定 |
|-----------|---------|------|
| ueanim → Blender4.5 → FBX → NexusBatch fork(ExportGeometry) → anm；Q/p_Q/EPS/scale 标定 | Blender2.49 + FBX6.1 + NB2 → gr2 → CivNexus6 → fgx/anm | 半被迫（ueanim 源进不了 NB2 老 FBX 链需试点），但标定成本是链选择造成的，应先做 2.49 链最小试点再决定保留 |
| 无原版动画复用（全部自烘） | 复制 .ast 改绑定；gr2 动画改名直用 | 自烘是需求（鸣潮动捕质量）所致，合理；但原版动画集可作为回退与比对基准，na2 只读导入是现成工具 |
| NexusBatch/MintBatch fork 硬编码动画名表 | 官方 NexusBatch 无硬编码名表（按目录批转） | fork 维护成本，应外置配置（gotcha 55 的根因） |

## 试点设计要点（供优化会话执行）

- **E-A（na2 比对，低风险）**：CivNexus6 打开原版领袖 fgx/动画 → export .na2 → Blender 2.83（io_import_na2）读入 → 与自烘焙输出逐骨比对（沿用 jx_diag_track 口径）。顺带验证 na2 读入在 2.83 的兼容性。
- **E-B（2.49 链最小试点，中风险）**：
  - 步骤 0（先做，可能整个跳过 NB2）：直接拿本机 CivNexus6.exe 的 "Open FBX" 喂一条动画 FBX（官方仅证实几何："Open FBX should now work for turning .fbx -> .fgx"，动画未证实）。若它接受动画数据，2.49+NB2 一段整体跳过。
  - 步骤 1：单片段 ueanim → Blender4.5 重定向 → 导出中间格式送 2.49（4.5 与 2.49 的 .blend 不互通，需经 psk/psa 或 FBX 中转——psa 导出是否被 ACL 补丁覆盖需实测）；2.49 端 NB2 → gr2 → CivNexus6 → fgx/anm。
  - 权重上限澄清：NB2 的 4 权重/顶点上限只影响**网格**；动画试点只送骨架+曲线、不送网格（网格走 cn6 链，支持 8 权重），该上限与 E2 无关。
  - 判定：试点产物过现有四判据 + 与现链输出并列，择优固化。

## 证据时效（诚实边界）

"Blender2.49+FBX+NB2 是往 Civ6 塞自定义动画的唯一路径"出自指南 2017 年 3 月原文，且为将来时（"is going to be"）；未检索到其后端到端跑通的教学帖；2023-09 的旋转修正帖仍在用 NA2 路线，说明社区动画线演进很少。因此 E2 是实验而非已知配方：最小试点、判据验收、失败记档、不许据此直接改链。
- 两试点都失败 → 保留现链，但把 Q/p_Q 标定从"逐项目人工标定表"固化为工具自动标定，动画名表外置配置。
