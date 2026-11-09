# 任务：优化 civ6-model-import skill，使 UE→Civ6 模型导入全流程不再重犯已识别的四类问题

## 背景与现状

- 目标 skill：`C:\Users\Administrator\.agents\skills\civ6-model-import\`（SKILL.md + references/ + scripts/ + tools/）。
- 2026-11-01 联网调研结论（证据已本地化在 `references/community/`，直接读本地文件；CivFanatics 有 bot 校验，禁止重爬）：skill 管线架构与社区成熟工具链（Deliverator 系 CivNexus6 / Nexus Buddy 2）同源，实机验收体系（四判据、九类告警、部署指纹）超过社区水平——这些不动。但四个环节自造，`references/gotchas.md` 60+ 条痛点多数是这四项的直接后果：
  1. **贴图/.tex/.mtl 元数据手工自造**（CivNexus6 自带 Texture Import / Process All Textures in Directory；Asset Editor 有 Class 模板与 4×4 占位复用惯例）→ 痛点 gotchas 17–22、48–60、152；
  2. **动画链走 Blender4.5 FBX → 自研 C# 导入器 fork**，Q/p_Q、EPS=0.01°、`arm_c.scale=0.01`、identity 通道 R_z(180°) 全部产生于此（社区成熟路线见 `community/animation-route-notes.md`；na2 是只读通道这一事实也在该笔记）→ 痛点 10、13、14、16、55；
  3. **.geo/.anm/.wig 与 .ast 手工补丁**（CivNexus6 按 class 生成、Leader 自动带 dummy .wig、可生成 m_GeometrySet XML；ast 成熟做法是复制原版只改绑定）→ 痛点 15、24、26、54；
  4. **周边自造**：FModel ACL 私有补丁（"仓库更新会丢失"）、Blender 4.5.9 独苗（官方推荐 2.7x 导出 binormals/tangents、法线经 VERTEX_KEYS 保留）。

## 硬边界（违反任何一条即停）

1. **不破坏已验证链路**：`success-case.md` 定稿参数、四判据、九类告警、部署指纹全部保持有效；全量重跑一次今汐链（或最小子集）证伪无回归。
2. **先实验后改文**：任何替代路径必须 round-trip 实验通过（用现有判据验收）才能写入 SKILL.md 主流程；实验失败也要把数值结论记入 gotchas，禁止把未验证假设写成事实。
3. **判据体系是资产**，不许绕过、弱化或新增绕过它的捷径。
4. scripts/ 现有 200+ 一次性诊断脚本不再新增同类；验证一律走现有判据工具；旧脚本移入 `scripts/archive/` 保留历史。

## 工作项（按序执行，每项先实验、后落文）

**E1 na2 只读比对（低风险，先行）**
CivNexus6 打开原版领袖 fgx → export .na2 → Blender 2.83.0（本机已装 io_import_na2，注意它只读）导入 → 与现烘焙输出逐骨比对（jx_diag_track 口径）。产出：兼容性结论 + 逐骨差异数值。用途：建立原版动画基准，作为比对与回退通道。

**E2 成熟动画链最小试点（中风险，与 E1 可并行）**
按 `community/animation-route-notes.md` 的 E-B 设计，三档递进：
- 步骤 0：先测本机 CivNexus6.exe "Open FBX" 是否接受动画 FBX（官方仅证实几何）；能则跳过 NB2 整段。
- 步骤 1：单片段走 Blender2.49 + FBX6.1 + Nexus Buddy 2 → gr2 → CivNexus6 → fgx/anm（NB2 获取路径与降级变体见 community/handoff-clarifier.md；动画不送网格，NB2 的 4 权重上限与此无关）。
- 降级：Blender 2.79 FBX → 现有 NexusBatch fork，验证病灶是否出在 FBX 版本而非自研导入器。
产物一律过四判据并与现链输出并列，择优定链。全部不可行则：保留现链，把 Q/p_Q 标定固化为工具自动标定、动画名表外置为配置文件（消 gotcha 55）。注意证据时效：2.49 链的"唯一路径"论断是 2017-03 原文，E2 是实验不是已知配方。

**E3 贴图与材质改造**
新贴图一律经 CivNexus6 Texture Import / Process All Textures in Directory 生成 dds/tex 对；材质按"只有名字重要"口径，缺省层用 4×4 占位复用；手写 .tex 降级为兜底并在文档标注。逐条映射 gotchas 17–22、48–60、152 到新路径， cook 前置校验加"贴图对必须由工具生成"检查。

**E4 几何/动画/ast 生成改造**
.geo/.anm 用 CivNexus6 按 class 生成（Leader 自动 dummy .wig，消 gotcha 15 手工删 WIG）；m_GeometrySet 用 "Create GeometrySet .xml" 生成；**ast 一律从原版领袖 ast 复制后只改绑定/时长**（原版已含 4 个迁移槽，消 gotcha 54），`jx_assemble.py`/`jx_ast_normalize.py` 降级为兜底并保留顺序守卫。

**E5 Blender 导出 A/B**
2.7x/2.83（cn6 插件已装）vs 4.5.9 各导一版，用 `cn6_corner_normals.py`、`jx_dark_seam.py` 探针与实机发片两色为裁决（官方理由：2.7x 导出 binormals/tangents；法线经 VERTEX_KEYS 保留）。结论写回 SKILL.md §〇。

**E6 ACL 上游去私有化**
测 UE Viewer（umodel）原生 ACL 支持能否导出鸣潮 psk/psa/ueanim；可行则 FModel+CUE4Parse 私有补丁降级为备份（消除"仓库更新会丢失"漂移）；不可行则把补丁构建脚本纳入 skill 包随包携带。

**E7 fork 维护性**
NexusBatch/MintBatch 硬编码动画名表外置为随包配置文件；fork 与上游 CivNexus6 v1.3.3 的 diff 写一页说明（`community/civnexus6-tool-extract.md` 为上游基准）。

## 文档产出（全部完成后）

1. SKILL.md 增设「与社区工具链对齐」一节，至少含三条路由规则：贴图一律工具生成；动画链按 E2 结论选路；ast 从原版复制改绑。
2. gotchas.md 顶部加「根因 → 新路径」映射表：17–22、48–60、152（贴图）、10、13、14、16、55（FBX 链）、15、24、26、54（geo/anm/ast），每条标注「已由新路径消除（实验号）」或「保留（原因 + 兜底）」。
3. `references/community/README.md` 索引核对补全（引用处标注 URL 与提取日期）。
4. 实验记录写入 `workspace/gen/reports/`：数值 + 文件出处，格式沿用现有报告惯例。
5. 分节更新 SKILL.md §四 任务分流：新增「贴图异常先怀疑手工 tex」「动画链改动先查本节路由」条目。

## 验收标准

- 上述映射表全部条目有着落；每项实验有数值记录与文件出处。
- 全量管线一次重跑通过（九类告警 0、部署指纹入留痕）。
- SKILL.md 中不再存在与 `community/` 证据冲突的流程描述。
