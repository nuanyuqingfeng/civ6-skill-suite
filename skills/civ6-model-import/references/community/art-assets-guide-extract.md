# 提取：Art Assets in Civilization 6 — A Modding Guide（CivFanatics thread 612050）

> 来源：https://forums.civfanatics.com/threads/art-assets-in-civilization-6-a-modding-guide.612050
> 采集日期：2026-11-01（WebFetch 服务端缓存，全文提取）。社区公认的 Civ6 3D 资产权威指南，作者 Deliverator 系。
> 用途：civ6-model-import skill 优化对照。以下为按主题整理的要点，工具菜单名保留原文。

## 1. 模型导入工作流（CivNexus6 + Blender）

给既有骨架挂新网格的标准步骤：

1. Load the base model into CivNexus6
2. Export to `.nb2` format
3. Import into Blender（Nexus Buddy 2 / CivNexus6 脚本包）
4. 建模与绑骨（顶点组→骨权重）
5. Export to `.cn6` format
6. 二选一：
   - (a) "use Import to import your .cn6 file then Save to create your .fgx"
   - (b) **复制原版 .fgx 换名，用 Overwrite 只替换网格数据——"All skeleton data will be left intact"**（复用原版资产的推荐做法）
7. 可能需要在 CivNexus6 内 rename/add/delete/reassign 材质到网格（名字被 .ast 和 .geo 引用）

几何元数据生成：**"Save Geometry (.geo) file" 在 Additional Actions 标签页**。
权重迁移参考 Wolfdog's Transfer Weights tutorial（只涉及该教程第 3、5–8 步）。
沿革：CivNexus6 取代 Nexus Buddy 2；FGX Viewer 取代 Granny Viewer；.fgx 取代 .gr2。

## 2. 贴图与材质

每个 `.tex`（元数据）配一张 `.dds`；`.mtl` 材质指向多个 .tex。单位材质六层：

| 层 | 默认值 | 备注 |
|----|--------|------|
| BaseColor | — | 无压缩+mipmap，Kaiser 算法推荐；Asset Editor：Tools→new→Texture→Class Name 选 **Generic_BaseColor**→设 Source File Path→保存（生成 .tex + 改写过的 .dds 副本） |
| Normal | 4×4 RGB(128,128,255) | Class "Generic_Normal" |
| AO | 4×4 白 | 可 Blender 烘 2D AO |
| Metalness | 4×4 黑 | 只允许纯黑或纯白，无灰 |
| Glossiness | 4×4 黑 | 白=全反射 |
| TintMask | 4×4 黑 | 白=透明、黑=不透明；供 Units.artdef 的 Tint 换色 |

- 结果 12 个文件（六层 × .tex/.dds）。4×4 是最小 .dds；**.tex/.dds 对可跨材质复用**（4×4 占位复用是常规操作）。
- 编辑器口径：Photoshop DDS 插件（无压缩导出）；Gimp 2 DDS 插件 "Export as ABGR8 format, .DDS with Compression=None"；Paint.NET 用 B8G8R8A8；部分原版 .dds 只能用 Gimp 2 打开。

## 3. .ast 结构与动画绑定复用

- .ast 在 cook 前把 Geometries、Materials、Animations 拉在一起。T-34 例：**复制原版 TankA.ast 到工程 Assets 目录 → 改名 T34_Tank.ast → Add > Existing Item → 改 m_Name → 换 m_Geometry**。
- 几何块：m_ModelInstances 含 m_GeoName / m_ObjectName（.mtl 材质）/ m_GroupName（.fgx 内绑定的材质）/ m_MeshName。
- **纯换肤只需把相关网格指到新 .mtl**。
- 骨架/动画结构 Civ5 .gr2 与 Civ6 .fgx 完全一致，只有网格格式变了。**Armor 人类骨架命名一致 → 一套 Armor .fgx 可交叉混用任意动画集（弩手甲配弓手动画），只需编辑复制的 .ast**。
- 三个关键集合（.ast/.bhv）：
  - `m_animationBindings`：SlotName（ATTACK_A、RUN_A、IDLE_A/B 等）→ 动画名；不再有动画码
  - `m_timelineBindings`：事件槽 → 时间线
  - `m_timelines`：经 Triggers 关联音效/视效（类型 ACTION、TRANSFER、ASSET_FX、SOUND；含 m_FXName、m_AttachmentPointName、m_fStartTime）
- `.bhv`（behaviors）打包动画/音效/VFX 时间线复用（如 SingleBiped_Deaths.bhv、Archer.bhv）。
- `.anm` 是 .fgx 动画的元数据，由 CivNexus6 生成。

## 4. XLP / BLP / ArtDefs / Mod.Art.xml / .dep 接线

- `.xlp`：XML Library Package 定义；关键字段 m_ClassName（"Unit"）、m_PackageName（"units/units"）、条目 m_EntryID + m_ObjectName（指 .ast）。资产 cook 进 `.blp`——**.fgx 不能裸发**。
- `.artdef`：Units.artdef（另有 Rough Guide to Units.artdef）；UnitAttachmentBins 经 BLPEntryValue（m_EntryName、m_XLPClass、m_XLPPath、m_BLPPackage）把 UnitMemberTypes 连到附件条目。引用写 "Vehicles/T34_Tank"；全路径 "Vehicles/T34_Tank/Any/T34_Tank" 也能用但会堵死文化变体；无文化变体时用 "Any"。
- `Mod.Art.xml`：最后一步用 TheCrazyScotsman 的 Mod Art Generator 生成，否则手改；含 consumer 条目（relativeArtDefPaths、libraryDependencies（Unit、VFX、Light））+ libraryName/relativePackagePaths 块（"units/units.blp"）。
- `.dep/.modinfo`：含 artdef/xlp 的构建产出 .dep，经 .modinfo 的 `<UpdateArt>` 动作里 "Mod Art Dependency File" 占位符引用。
- **构建后只需要 .modinfo/.dep、Platforms（ cooked .blp）、ArtDefs；Animations/Assets/Behaviours/Geometries/Materials/Textures/XLPs 目录都可删**。
- Pantry（Dev Assets）里的 .ast/.geo/.mtl/.tex/.anm 等可直接当自己 mod 的一部分用。

## 5. 已知 bug 与绕法

- **Asset Editor 在工程含自定义 .ast 时崩溃**（Firebug's KeyNotFoundException）。绕法：开两个 ModBuddy——一个专跑 Asset Editor，一个装配/构建/cook，文件（.tex/.dds 等）在两个工程 Textures 目录间拷贝 + Add > Existing Item。
- Asset Editor 有 Asset Previewer 可预览资产在游戏内的渲染，可测试武器/身体/头盔挂点。
- Civ6 自带 FBX 导入 "seems useless"。
- T-34 例的枪口焰例外：挂在新增骨 FX_Bone_Muzzle.002 而非 FX_Bone_Muzzle。

## 6. 动画导入与领袖备注

- **旋转问题**：Deliverator 2017-03 在 .fbx 自定义动画导入时即撞上 "Rotation problems..."。
- **解法**：Civ5 .gr2 动画在 Civ6 原样可用——NB2 打开 .gr2 → CivNexus6 ".br2 overwrite" 注入网格数据 → .fgx 直接配原动画。猛犸实测：只需改名为 .fgx + 生成 .anm 元数据（下一版 CivNexus6 加入）。
- 结论：**Civ5 管线（Blender 2.49 + FBX + Nexus Buddy 2）"is going to be the only way of getting custom animations into Civ 6"**。
- 领袖专项：本线程无领袖专属流程（只有模型类型列举时提到 Leaders）；单位/奇观分步教程委托给 Leugi、ShiroToraRyu、esosorcdc 的链接教程。动画槽位间过渡是否引擎自动混合，作者存疑未答。
