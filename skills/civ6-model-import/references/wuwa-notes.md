# 鸣潮素材专章（分享版整篇剔除）

本文件是 `civ6-model-import` 的鸣潮专用补充。`scripts/pack_share.py` 生成分享版时删除本文件，并删除主文件里 `<!-- WUWA -->` 行尾标记的行与 `<!-- WUWA:BEGIN -->` 块。绝对路径、角色名、资产代号一律只在这里出现，不写进其他章节。

新增鸣潮相关内容一律写进本文件；确需写在主文件的，必须带标记，否则打包器的泄露扫描以退出码 2 终止。

## 一、解包链路（FModel）

| 环节 | 做法 |
| --- | --- |
| 挂载 | 主包 410／455 档。`pakchunk111-113` 缺密钥时从 `yarik0chka/wuwa-keys` 补 GUID，写回 FModel 的 `AppSettings.json`，重挂到 419。剩余未挂载的多为视频包，与模型无关 |
| 导出格式 | 模型 psk（ActorX），动画 ueanim（UEFormat） |
| 代号反查 | 本地化反查（Kuro 自研文本，`zh-Hans` 无数据）→ ConfigDB（`db_phantom.db`）→ Prefab 引用反查（最可靠：角色 Prefab 引用其本体资产名） |
| 产物布局 | `G:\Wuwa_3D_Assets\Characters\<角色>\`：`converted\` 放 psk／ueanim／贴图，`raw\` 放原始 uasset／uexp |

ACL 障碍与补丁：ActorX 动画导出器对鸣潮的 ACL 压缩动画崩溃，报 DDC handle 不匹配。修法是给 `UAnimSequence.SerializeCompressedData3` 加 ACLSafe 兜底（`patches/UAnimSequence.cs`），覆盖 CUE4Parse 同名文件后重编 `CUE4Parse-Natives.dll`（VS2022 + CMake，`dotnet build` 21/21 通过）。UE Viewer build 1590 替代不了：33 次导出 0 文件，ACL 命中 0。

补丁装入由人工执行：先比对产物的 `ProductVersion` 与现役 `CUE4Parse.dll` 的提交哈希，一致才复制。`CUE4Parse-Natives.dll` 不复制，浅克隆重建出的 native 库不含 ACL 能力。

## 二、骨架与骨名

| 骨名族 | 含义 | 备注 |
| --- | --- | --- |
| `Root`、`Bip001`、`Bip001Pelvis/Spine/Neck/Head` | UE Biped 主链 | 与 Civ6 领袖骨架同名，可直接对应 |
| `Bip001*Twist`、`Bip001*UpArmTwist1/2`、`Bip001_L_CalfTwist` | 扭转辅助骨 | 缩减骨数时优先删这一族 |
| `Bone_Hair001`…`027` | 发链，编号即节序 | `Hair009→017` 与 `019→027` 是两条 8 节长链 |
| `Bone_Piao*`、`Piao_*` | 飘带 | 单位链常作附属骨补足 60 |
| `skirt_*`、`skrit_*` | 裙摆 | `skrit` 是素材自身的拼写，照抄 |
| `R_ChestBone01`、`L_ChestBone01` | 胸骨挂点 | 无蒙皮权重 |
| `WeaponProp01`…`07` | 武器挂点 | 权重顶点 0 |
| `MarkCase` | 头顶挂点，父 `Bip001Head` | 权重顶点 0 |
| `LongLin` | 挂点骨，父 `Bip001RForeTwist1` | 权重顶点 0，无角网格 |

骨数量级：源骨架 204 根（今汐）／189 根（男漂缩减前）；导出后模型侧 218～222 根；动画通道 205 根，其中 204 根命中。

资产与骨架同名：骨架名、TrackGroup 名、`MODEL[0]` 名都等于 `R2T1<角色>Md<编号>`（今汐 `R2T1JinxiMd10011`，守岸人 `R2T1ShouanrenMd10011`）。`Md10011` 主形态有完整网格；`Md20011` 第二形态只有 `pskx` 与贴图，没有网格。

源骨架朝向差：psk／ueanim 家族骨架与 cn6 游戏骨架的静止姿态差为 `Rz(90.000009°)`，60 骨残差 ≤0.0003 厘米。

## 三、片段语义与目录分布

```
CommonAnim\
  UiAnim\                     角色界面展示，只有 14 条
  Stand1_Action01/02/03\      待机表演动作
  Stand2、StandChange\        第二套站姿、站姿切换
  AM_*\                       与无前缀同名动作的 Montage 版本
  Skill*、Attack*、Burst*、Execute*、AirSkill*、Move*、Jump*\  战斗与移动
RibbonAnim\  RibbonAnim3\  Gameplay\Motor\RibbonAnim\        二次运动层
```

`UiAnim` 的 14 条：`Cos_Pose`、`Team_Stand1`、`Team_Stand2`、`Team_Stand3`、`Ui_Chip_End`、`Ui_Nature_Start`、`Ui_Nature_Loop`、`Ui_Nature_End`、`Ui_Resonant_Start`、`Ui_Resonant_Loop`、`Ui_Resonant_End`、`Ui_Weapon_Start`、`Ui_Weapon_Loop`、`Ui_Weapon_End`。

| 片段族 | 语义 | 常见误判 |
|--------|------|----------|
| `Ui_Nature_Start` / `Loop` / `End` | 角色界面「自然」页的展示待机，`_Start` 登场、`_Loop` 循环、`_End` 收尾 | 当成唯一的待机来源 |
| `Stand1`、`Stand1_Action01`…`03` | 站立待机本体与待机表演动作，`_ActionNN` 全部属于待机动作族 | 看见 `Action` 就归进技能或战斗类，待机因此没有表演动作 |
| `Stand2`、`Stand1_Turn_L90D` / `R90D`、`StandChange` | 第二套站姿、90 度转身、站姿切换 | 与 `Stand1` 混用，各片段首帧朝向不一致 |
| `Team_Stand1`…`3` | 队伍界面的站姿 | 当成战斗待机 |
| `Ui_Weapon_*`、`Ui_Resonant_*`、`Ui_Chip_*` | 武器页、共鸣页、碎片页各自的展示动作 | 当成剧情动作或战斗动作 |
| `Cos_Pose` | 换装展示姿势 | 与待机片段混用 |
| `AM_*` | 同名动作的 Montage 版本，带位移与分段 | 与无前缀版本一起导入，同一组通道被写两次 |
| `Skill*`、`Attack*`、`Burst*`、`Execute*`、`AirSkill*`、`Move*`、`Jump*` | 战斗与移动动作 | 填进界面槽位 |
| `Rib_*`（RibbonAnim 目录） | 发丝与飘带的二次运动叠加层 | 当主序列导入，骨骼数量与主序列不一致 |

三条判据：

1. `Stand1_Action01` 就是待机动作。今汐工程取它第 80…380 帧插进待机循环，`Stand1_Action03` 的 0…458 帧做称赞槽（祈愿），`Stand1_Action02` 尚未使用。
2. `UiAnim` 里没有倒地或战败动作，战败槽只能借待机片段（今汐借 `Ui_Nature_Loop` 240 帧）。
3. 发骨运动不是每段都有：144 条里只有 `Cos_Pose`、`Cos_Pose_A`、`AirSkill` 三族带发骨关键帧，其余发丝动画要靠二次运动层或程序化解算。

`TURN_L` / `TURN_R` 的 `Root` 自带正负 90 度旋转，末帧髋线分别是 −108.950° 与 71.049°，这是转身动作的正常收尾，不参与站立朝向修正。

## 四、二次运动层（RibbonAnim）

三个目录，条数按 `Md10011` 计：`RibbonAnim` 175 条、`RibbonAnim3` 95 条、`Gameplay/Motor/RibbonAnim` 25 条；`Md20011` 同构 289 条。

- 语义：`Rib_*` 的轨道存相对 RefPose 的绝对局部姿态；基座发丝、裙摆、披帛的静止姿态恒为 RefPose，因此可以整条覆盖旋转四元数，按 1:1 写入，不做增益、不做偏移。
- 帧数与主序列逐帧吻合，196 轨全骨架、其中 31 根发骨逐帧有 key，命名体系与主骨架一致。
- 判据：`NexusAnimAmp.exe` 读轨道，节点数大于 1 才算真有曲线；发骨局部峰值 21 到 83 度、裙骨 4 到 23 度、披帛 20 到 126 度是御三家工程的实测区间。

素材里没有 `Rib_*`、只剩身体片段可借时，借用会带来两个必然缺陷：

- 借用片段帧长远短于输出片段，逐帧取整把运动变成阶梯，待机表现为低幅度高频抖动。
- 借用片段的发丝摆幅是那一段动作的量级（实测 165 到 178 度），换到别的身体动画上就是乱飘。

## 五、贴图与材质

| 项 | 鸣潮侧的事实 |
| --- | --- |
| 材质命名 | `MI_R2T1<角色>Md<编号><部件>`，如 `MI_R2T1JinxiMd10011Bangs` |
| 贴图命名 | `T_R2T1<角色>Md<编号><部件>_D`，同族带 `_D2`、`_N`、`_LD`、`_M`、`_HM`、`_VC`、`_ID` |
| 透明阈值 | 材质 JSON 的 `OpacityMaskClipValue` 为 0.3333，乘 255 得 85，即掩膜二值化阈值 |
| 薄纱替身 | 半透版本带 `Nosi` 后缀（如 `Up02Nosi_D`，不透明占比 0.173、均值 79.0）；实体版本是 `Upal2`（0.998、129.2）。matte 下用实体版本 |
| 面部形态键 | 今汐 86 个，转面骨后 18 根面骨里 17 根参与拟合（`JX_LipLo` 无蒙皮权重） |

今汐骨骼分组实测（贴图局部调色按主导骨骼定位时用）：

| 骨骼 | 面数 | u 范围 | 平均 z（厘米） | 部位 |
| --- | --- | --- | --- | --- |
| `Bip001Head` | 2846 | 0.010–0.984 | 131.6 | 头帽与耳上 |
| `Hair002/006` | 227／238 | 0.011–0.750 | 125.5 | 两侧垂发第一段 |
| `Hair003/007` | 731／722 | 0.011–0.750 | 120.8 | 两侧垂发第二段 |
| `Hair009/019` | 208 | 0.765–0.984 | 125.2 | 垂发上段 |
| `Hair010/020` | 320 | 0.738–0.985 | 111.8 | 垂发上段 |
| `Hair011/021` | 173 | 0.728–0.967 | 95.7 | 垂发中段 |
| `Hair012/022` | 332 | 0.696–0.987 | 80.3 | 垂发中段 |
| `Hair013/023` | 448 | 0.685–0.988 | 66.8 | 垂发下段 |
| `Hair015/025` | 246 | 0.047–0.976 | 48.4 | 长垂发 |
| `Hair017/027` | 392／404 | 0.190–0.861 | 28.5 | 发尾 |

`Hair002/003/006/007` 是两侧垂发的一二段，不是双马尾；漏掉这两组时垂发中段一直留灰。今汐定稿共十二段骨骼、7,726 个三角。

## 六、单位侧

- 女漂（`UnitRoverFemale`）与男漂（`UnitRover`）共用一套基础动作，公共动画在 `...\Characters\公共动画_体型BaseAnim\...\FemaleM\BaseAnim` 与 `MaleM\BaseAnim`；角色专属战斗动作在 `角色_Nvzhu\CommonAnim`、`角色_Nanzhu\CommonAnim`。
- 单位类只用 60 根骨：42 根核心骨固定，18 根附属骨按角色替换。男漂取 12 根 `Bone_Hair*` 加 6 根 `Piao_*`；女漂取 `skirt_*`、`skrit_*`、`Piao_F01/F02`、`R_ChestBone01`、`L_ChestBone01`、`Hair_*`。
- `Stand2` 的首帧被用作待机（`IDLE_A`）的源片段：源帧 0..80 共 81 个采样点，输出帧数超过 81 就会产生重复帧。
- 右手声痕是独立面片，贴图 `STAR <角色>.png` 的 alpha 只有星芒处不透明（0.003 均值、98.9% 像素低于 0.05），单位材质没有 `Opacity` 槽，轮廓必须写进几何。

## 七、数值口径

| 项 | 值 | 说明 |
| --- | --- | --- |
| ueanim 通道换算 | 通道值 ×100 | 通道存米，模型是厘米 |
| 动画骨架缩放 | `arm_c.scale=(0.01,0.01,0.01)` | 抵消 FBX 导入器写入的 `diag(100,100,100)` |
| 烘焙微旋 | EPS = 0.01° | 通道旋转恰为 identity 时输出被额外右乘 `R_z(180°)`，204/204 骨命中 |
| Q/p_Q | 动画侧 fgx 的静态基准 | 与模型 rest 夹角 mean 49.80°，把模型 rest 当 Q 是历轮散架的根因 |
| 帧率 | 30 fps | 动画与口型包络同一时基 |

## 八、解包完整性边界

| 项 | 读数 | 影响 |
| --- | --- | --- |
| 游戏内动画类资产 | 725 条 | 基准总量 |
| 本地 `converted` | 144 条 | 覆盖率约 19.9%，只有 `CommonAnim` 与 `UiAnim` |
| 本地 `raw` | 93 个资产 | 比 `converted` 还少，是后来被裁剪过的副本 |
| RibbonAnim 家族 | 本地缺失，需补导 | 缺它就只剩角度弹簧与质点链两条路 |
| PhysicsAsset | 已导出 27 条（`Md10011`）／38 条（`Md20011`）约束 | 限角、刚度、阻尼、线性驱动、碰撞体在该 fork 里未序列化，只能取约束骨对与约束坐标系 |
| `Md20011` | 只有 `pskx` 与贴图 | 第二形态无法直接建模 |

## 九、星芒 / 声痕类贴花特例（**仅鸣潮触发**）

鸣潮解包出来的星芒（共鸣纹、声痕）贴图，RGB 通道存的是 **mask 语义**，不是最终颜色。把它当颜色直出会踩两个坑，本节是唯一处置口径。

### 9.1 为什么它是特例

源图形态（今汐 `MI_6XingStar_BaseColor_1024.png` 实测）：

| 区域 | alpha | RGB | 语义 |
|---|---|---|---|
| 背景 | 94.54% = 0 | **(255, 0, 0) 纯红** | 占位色，不是"红色背景" |
| 星芒 | 4.75% = 255 | **(255, 130, 39) 橙黄** | mask 编码，不是"橙色星星" |
| 过渡 | 0.71% 中间 | — | 抗锯齿 |

关键点：**这张图是非预乘的**，切形完全靠 alpha；而 RGB 里的纯红／橙黄只是 UE 侧的通道用途。文明6 的 `Leader_Matte` 直出 BaseColor，于是：

- 按「透明区 RGB 置 0」→ 纯红背景变**纯黑**；
- 再按「领袖基色压平 alpha 255」→ **蒙版清空**；
- 结果：一整块黑底方块画在角色背上，中间嵌着彩色星星。

### 9.2 三重门（全满足才进特例）

| 门 | 判据 | 目的 |
|---|---|---|
| 一 · 主题门 | 源图来自鸣潮解包产物；或槽名命中星芒族（`XingStar`、`STAR <角色>`、声痕/共鸣纹类，参见 §五 与 §六） | 把特例锁在鸣潮内 |
| 二 · mask 语义门 | alpha 双峰：`=0` 占 **>20%** 且 `=255` 占 **<50%**，**且** alpha=0 区 RGB 是纯饱和占位色（通道最大值 =255 且通道极差 **>200**） | 证明 RGB 不是颜色 |
| 三 · 材质门 | 材质同时挂 `BaseColor` + `Opacity` 双槽 | 确认切形另有通道，基色可以只留形状 |

**任一门不满足 → 判为「非鸣潮贴花」**，走 `texture-rules-matrix.md` 的通用贴花行：保留蒙版 + 透明区 RGB 置 0，**可见区 RGB 原样保留**，并打印 `WUWA_SPECIAL=skip`。文明6 原版贴图、其他游戏的贴花即使 alpha 双峰也走通用行，不会被误刷黑。

### 9.3 处置步骤

1. 源图 **RGB 全置 0**（含 alpha=255 的可见区——这一步是特例独有，通用规则绝不做）；
2. **alpha 原样保留**，禁止压平；
3. `E3TextureImport.exe <src.png> <name> Leader_BaseColor <outdir>` 生成 dds/tex 对；
4. `Opacity` 槽不动（它的 0/255 分布本来就是对的）；
5. 入库、cook、部署。

### 9.4 验收闸门

| 项 | 阈值 | 今汐实测 |
|---|---|---|
| 成品 alpha=0 占比 vs 源图 | 差 ≤1 个百分点 | 94.54% vs 94.54% ✓ |
| 成品 RGB 最大值 | **= 0** | 0 ✓ |
| Opacity 槽 =0 占比 | 与修改前一致 | 93.62% ✓ |
| Blender 探针 `frac` | ≈源图 alpha=0 占比（切形生效） | 0.9479 ✓ |

判据脚本：`scripts/probes/wuwa_star_decal_audit.py`（同时负责三重门判定与验收）。

### 9.5 与其他规则的互斥

`texture-rules-matrix.md` 里「蒙版/星芒/轮廓贴花」与「领袖基色」两行会同时命中这类贴图，而后者要求压平 alpha——**特例优先**。判定顺序：先跑三重门，命中就按本节走，不再看领袖基色行。

## 十、素材边界

- psk、ueanim、贴图与密钥不进任何分发包；密钥存于 FModel 自身的 `AppSettings.json`。
- ACL 补丁随包携带时按 `ProductVersion` 的提交哈希核对后人工装入，脚本不复制文件。
- 本文件与主文件里的 `WUWA` 标记在分享版中一并删除；打包器的泄露扫描是本节的执行判据。
