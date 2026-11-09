# CivNexus6 fork 与上游 v1.3.3 差异说明

状态：定稿，已随 skill 包分发（包根 C:\Users\Administrator\.agents\skills\civ6-model-import，配置化产物在 `tools/CivNexus6/`）。

对照基准：references/community/civnexus6-tool-extract.md（第 1 行标注 v1.3.3 与作者 Deliverator；第 9 行记录官方资源页没有独立 NexusBatch 条目，批量功能属于 CivNexus6 自身，skill 包内的 NexusBatch.exe 是私有 fork；第 56 行记录上游的批量方式是界面菜单 “Convert all .gr2 Files in Directory to .fgx/.anm”）。

## 差异总表

| 编号 | 差异项 | 理由 | 影响面 | 回归证据 |
|---|---|---|---|---|
| D1 | 增加无人值守批处理入口 NexusBatch.exe 与 MintBatch.exe（3 个位置参数：素材目录、输出目录、动画根节点） | 管线脚本需要无界面批量转换，上游只有界面菜单 | 调用方 scripts/jx_rot_pipeline.py:36、jx_rot_pipeline2.py:39、jx_rot_pipeline3.py:21；参数个数固定为 3，不读取第 4 个参数 | 本轮实测 NexusBatch.exe 与 MintBatch.exe 均完成 7 段动画转换，日志 log_new.txt、log_mint_jx.txt |
| D2 | 把动画名表从源码外置为随包 TSV：<exe 名>.animset.tsv | gotcha 55（references/gotchas.md:108）：资产改名后转换静默跳过动画，必须同步重编 exe | NexusBatch.cs 42-127、270-302；MintBatch.cs 41-116、236-265；配置缺失或条目缺失时退出码 2 | 25/32 产物字节一致、曲线转储 99 行一致、改名后 0 次 ANIM_SKIP（见报告第 8、9 节） |
| D3 | 模型侧文件名与 FBX 节点名从源码外置为配置项 model.cn6／model.fbx／model.tmp／model.dst／model.node | 换项目必须改源码并重编，改错名字只表现为产物取名异常 | NexusBatch.cs 270-281；MintBatch.cs 236-247 | 本次以配置驱动的转换产物 LEAD_Jinhsi_QYQXP.fgx 与改前字节一致 |
| D4 | 模型初始摆放由“保留源值”改为“位置归零 + 朝向按候选索引写入”，候选表 QUATS 共 7 项，索引来自 model.placement | 源 FBX 的初始朝向与引擎竖直方向不一致，需要按项目选择绕轴角度 | NexusBatch.cs 156-182（候选表）、256（越界报错）、292（调用点）；MintBatch 无此步骤 | placement=0 时产物与改前一致；placement=2 时回显 PLACEMENT_SET idx=2 q=[0,0,-0.7071,0.7071] 且模型 fgx 哈希改变 |
| D5 | 动画源 .fbx 缺失时由“回显 ANIM_SKIP 后继续”改为“报错退出” | 静默跳过会把缺段问题推迟到 cook 或实机 | NexusBatch.cs 302；MintBatch.cs 265；退出码 2 | 改名前后对照：改前 ANIM_SKIP JX_IDLE 且只有 6 段，改后 7 段 0 次 ANIM_SKIP |
| D6 | 写入 .geo 元数据时固定类名与标签 “Leader”，并复制随包 dummy.wig | 领袖资产的类名在引擎侧固定取值；wig 必须与 fgx 同名同目录 | NexusBatch.cs 135、149、88（File.Copy 源为窗体 dummyWigFilename） | LEAD_Jinhsi_QYQXP.geo 与 .wig 在四组运行比对中字节一致 |
| D7 | 随包存在两份同一程序：NexusBatch.cs（JX 名表）与 MintBatch.cs（HM 名表），两者除名表外逐行相同 | 历史项目分叉，改一个项目的名表需要重编一次 | 两个 exe 各自读取 <exe 名>.animset.tsv，互不冲突；退役 MintBatch 需要 Hethereau 管线同步改动，本轮未执行 | 两份源码哈希见报告第 2 节；本次改造后两份源码的配置机制逐行相同 |
| D8 | 修复源文件无法编译的缺陷：ZeroPlacement 内引用不存在的 args（原行 169），placement 索引改由 model.placement 提供 | 该引用使 csc 报 CS0103，任何构建都无法产出可执行文件 | 原行 168-172 的四行分支被替换为越界校验（现 256 行）；第 4 个位置参数不再被读取 | 编译退出码 0（NexusBatch.exe 16384 字节），placement=0 与 placement=2 两次运行均可完成 |

## 产物形态与上游的关系

上游批量转换产出 .fgx／.anm 两类文件；fork 在此之外还写出 .geo（XML 元数据）与 .wig（dummy 骨对应文件），并且每个动画额外保留一份 <名字>_src.fgx（FBX 导入的中间结果）。.geo 由 MetadataWriter.WriteGeoAnimFile 产生，调用参数固定为 (file, 0, "Leader")，与上游 NebBuddy 的元数据写法一致。

## 编译真源与构建约束

三份 NexusBatch.cs（skill 的 tools/CivNexus6、skill 的 scripts/csharp、宿主 E:\SoftWares\civ6_nexus_work\CivNexus6）sha256 完全一致，取值 c4cd06f46607815f5408dbe33ef9c1a86498ccbf80fe53dbe45030512e53e1d5，字节数 9731，行数 238，构成编译真源。上游 clone（E:\SoftWares\civ6_nexus_work\CivNexus6_src，HEAD fc3ac86c，2023-04-17）内没有 NexusBatch.cs，与该文件属于 fork 产物的判断一致。

MintBatch.cs 不在 skill 包内。现役的一份在 D:\documents\Firaxis ModBuddy\Civilization VI\Hethereau_Mint\Hethereau_Mint\workspace\_tools\MintBatch.cs（sha256 5037be55…，8273 字节，207 行，HM 名表）；宿主目录另有一份 sha256 94ab1bf9…（8273 字节，207 行，JX 名表）。两份逐行相同，差别只在第 40-41 行的动画名。

编译引用必须是 CivNexus6.exe：窗体类型 CivNexusSixApplicationForm 及其 .resources 都在这份 648192 字节的 x86-64 程序集内（manifest 资源 5 项，其中 NexusBuddy.CivNexusSixApplicationForm.resources 长度 201986 字节）。运行目录里的 NexusBuddy.dll 内部程序集名为 NexusBuddy_mint、manifest 资源数为 0，作为编译引用会导致窗体构造阶段报 MissingManifestResourceException。Firaxis.Granny.dll 与 CivNexus6.exe 均为 x86-64（PE machine 0x8664），因此产物按 AnyCPU 编译（PE machine 0x14c，运行在 64 位宿主），指定 -platform:x86 会在加载 Firaxis.Granny 时报 BadImageFormatException。

## 尚未覆盖的对照

上游 v1.3.3 没有 NexusBatch 的可执行实现，无法做源码级逐行比对；本稿的可对照面限于功能面（入口形态、产出文件种类、名表来源、失败行为）。上游对名表的处理无法判定，现有证据只能说明上游工具本身不含此名表。

## 回归证据索引

- 改前基线日志：E:\SoftWares\civ6_nexus_work\wp5\log_base.txt（随包 NexusBatch.exe，eafd12da）
- 源码修订版对照：E:\SoftWares\civ6_nexus_work\wp5\log_out_pre.txt、log_out_pre2.txt（NexusBatch_pre.exe，40b7da44）
- 外置配置版：E:\SoftWares\civ6_nexus_work\wp5\log_new.txt、log_new2.txt（NexusBatch.exe，efbc6b5b）
- 改名前后：log_rename_before.txt、log_rename_after.txt
- 曲线转储：curvedump_out_pre.txt、curvedump_out_new.txt
