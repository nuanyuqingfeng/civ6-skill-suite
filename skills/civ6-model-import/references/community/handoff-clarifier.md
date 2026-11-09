# 澄清说明（交接给新会话：先读这段，再读 skill-optimize-prompt.md 全文，然后动手）

## 三点澄清（防止最常见的三种误做）

1. **这次不是重写管线，也不是引入新框架。** skill 的架构与社区工具链同源，验收体系（四判据、九类告警、部署指纹）比社区教程更强，全部保留。要做的是把四个"自造层"——手写 .tex/.mtl 元数据、手工 .geo/.anm/.wig 与 ast 补丁脚本、Blender4.5-FBX→自研 C# 导入器（Q/p_Q/EPS/缩放三套标定全是这条链的病）、FModel ACL 私有补丁——替换或降级为工具链自带能力。已验证的成功链路（success-case.md）一个字不许坏。

2. **"以后不犯"靠两个机制，不靠加更多探测脚本。** 机制一：替换根因路径（E1–E7）。机制二：gotchas 顶部加"根因 → 新路径"映射表，每条旧痛点要么标注"已由新路径消除（实验号）"要么"保留（原因+兜底）"。scripts/ 已有 200+ 个一次性诊断脚本（jx_r3…r16、jx13/jx14 系列），那就是过去弯路的化石层——本轮只许移入 archive，不许新增同类。

3. **na2 不是双向通道（修正一个容易踩的假设）。** 社区脚本 `io_import_na2.py` 只读：它能把原版领袖动画读进 Blender 做比对/复用评估，不能把 Blender 动画送回引擎。往 Civ6 塞自定义动画的社区成熟路径是 Blender2.49 + FBX6.1 + Nexus Buddy 2 → gr2 → CivNexus6。所以动画链的走向由 E1（na2 比对）与 E2（2.49 链最小试点）的实验结论决定，不要预先写死进文档。

## 第一个动作

并行跑 E1（na2 只读比对，约 30 分钟量级）和 E2 最小试点（单片段）。两者结论决定动画链路由；E3–E7 与其无依赖，可并行推进。

## 环境注意

- 社区资料已本地化在 `references/community/`（README.md 有索引与未落盘清单）；CivFanatics 有 bot 校验，**禁止重爬**。
- CivNexus6 上游基准是 v1.3.3（`community/civnexus6-tool-extract.md`）；skill 包内 NexusBatch.exe 是私有 fork，对比时以资源页口径为准。
- Blender：4.5.9 是现管线唯一实例，2.83.0 已装 cn6+na2（io_import_na2），2.49 链试点如需 NB2 工具本体需另行获取（CivFanatics resource 52997）。
- **NB2 本机不存在**：`E:\SoftWares\civ6_nexus_work\` 下的 NexusBuddy.dll/.csproj 是 CivNexus6 fork 的核心库，不是 Civ5 时代的 NB2 独立工具。NB2 只经 CivFanatics 分发，无编译版 GitHub 镜像：
  - 原始发布帖（附件下载）：https://forums.civfanatics.com/threads/nexus-buddy-2-granny-editor-for-civ-5.496855
  - 资源页（Nexus Buddy 2.1 编译版）：https://forums.civfanatics.com/resources/nexus-buddy-2-1.52997/
  - Blender 2.49 脚本 V12：https://forums.civfanatics.com/resources/nexus-buddy-2-scripts-for-blender-2-49-v12.53037/
  - 下载需人工浏览器过 bot 校验后完成；NB2 开源，源码也在发布帖内。
- **NB2 拿不到时 E2 的降级变体**：改测 Blender 2.79（FBX 7.4 导出）→ 现有 NexusBatch fork，验证老版 FBX 是否同样触发 Q/p_Q/R_z(180°) 病灶；此变体不需要 NB2，结论同样能决定"换导出端"还是"保留 4.5.9"。E2 还有更靠前的步骤 0：先测本机 CivNexus6 "Open FBX" 能否直接吃动画 FBX——能则 NB2 与 2.49 链整个跳过。NB2 的 4 权重上限只影响网格，与动画试点无关（动画只送骨架+曲线）。
