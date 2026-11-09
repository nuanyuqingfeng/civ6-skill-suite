# 领袖模型通用烘焙与导入流程（2026-11-02 守岸人工程实机验证）

本文是**领袖链**的主干，十步流程每一步的判据与踩坑都收在这里。单位链走 `unit-template.md`，两者不混用。
路径约定：`<方案根>` 是 `.civ6sln` 所在目录，`<工程名>` 是项目主体目录名。

## 一、管线骨架（唯一正确顺序）

```
psk ──导入──> 缩放定标 ──缩放──> 面骨建骨 ──建骨──> 面部权重 ──写权重──> 朝向修正 ──旋转──> cn6 ──NexusBatch──> fgx ──assemble──> 工程 ──cook──> BLP
```

顺序铁律，四步的先后不可换：

| # | 动作 | 为什么必须在这一位 |
|---|------|-------------------|
| 1 | `Matrix.Scale(k, 4)` 施加到骨架与网格 | 面骨的所有尺寸常量都以「厘米 / 目标身高」为单位推出，缩放没做就先建骨，骨长会按源模型尺度算，差出几十厘米 |
| 2 | `face_rig.build_face_rig` + `apply_weights` | 面骨位置写成 `(x, y, z)` 直觉坐标（眼球 `center_dome`、嘴 `MOUTH_Y/MOUTH_Z`、眉 `(±2.4K, MOUTH_Y, MOUTH_Z)`）。**任何绕轴旋转都必须排在它之后** |
| 3 | `Matrix.Rotation(δ, 4, 'Z')` 朝向修正 | 只转骨架会让网格留在原位，必须骨架与网格同转 |
| 4 | `bpy.ops.export_shape.cn6` | 导出插件按 UV 接缝与硬边拆点，顶点数会涨（守岸人 54,998 → 59,608），三角数不变。这是正常行为 |

守岸人把第 2 步排在第 3 步之前时踩到的坑：网格已绕 Z 转 90°，面骨仍按直觉坐标算，结果 `SK_Eye_L` 落在 `[-2.8, -2.2, 124.4]`、`SK_Eye_R` 落在 `[2.8, -2.2, 124.4]`——两眼落在 X 的 ±2.8，Y 都是 −2.2，左右分量塌到同一数上，整张脸错位。正确顺序下为 `[2.2, -2.8, 124.4]` 与 `[2.2, 2.8, 124.4]`，两眼分居 Y 的 ±2.8。

判据：面骨与 `Bip001Head` 都取世界坐标，两眼应分居模型左右轴的正负两侧、X 值相同；嘴在两眼中间的正下方。

## 二、NexusBatch 转换（不写死载体名）

`NexusBatch.exe` 读 animset.tsv 决定输入输出。tsv 由脚本按 `bs_leaders.json` 生成，六行全部取自配置：

```
model.cn6	<ast_target>.cn6
model.tmp	<ast_target>_src.fgx
model.dst	<ast_target>.fgx
model.node	<mesh_name>
model.class	Leader
model.placement	0
```

`model.class` 必须是 `Leader`（`NexusBatch.cs:197` 的 `isLeader = cfgClass == "Leader"` 决定是否写 WIG 条目）。写成 `Character` 会得到 `<AssetObjects..GeometryInstance>` 单点写法，cook 报 `Entity name in XML file ... does not match` 并替换成 `Error/Leader_Error_Asset`。

几何文件（.geo）的实体名由 `NexusBatch.cs:194` 的 `Path.GetFileNameWithoutExtension(dst)` 决定。产物名必须是 `ast_target`，不要在转换后改名——改名会让 geo 内部名与 XLP 期望的名字不一致，cook 同样拒绝。

装配脚本的正确做法是**断言**而非替换：

```python
assert '<m_Name text="%s"/>' % target in t, (
    "geo 内部实体名不是 %s：转换环节的 animset model.dst 未按 ast_target 命名" % target)
```

## 三、表情骨（一处工具，全部领袖共用）

`scripts/face_rig.py` 是唯一实现，禁止在工程 `_tools/` 下复制。19 根骨的名称后缀与角色无关：

Jaw、LipUp、LipLo、MouthCorner_L/R、LidUp_L/R、LidLo_L/R、Eye_L/R、Brow_L/R、BrowIn_L/R、Cheek_L/R、Nose

调用顺序固定：

```python
import face_rig
face_rig.set_prefix(cfg["code"])          # 骨名 = <code>_<后缀>
face_rig.configure(parts, MODEL_SCALE)    # parts 是该角色的测量结果
face_rig.build_face_rig(arm, body)        # 建骨，父骨 Bip001Head
face_rig.apply_weights(body)              # 按面部顶点索引写权重
```

`parts_<code>.json` 必备字段：`eyeball.L/R` 的 `center_dome` 与 `radius_fit`、`mouth_z`、`mouth_y`、`mouth_half_w`、`browL`、`browR`、`lashL`、`lashR`、`face_verts`（顶点索引）。这些全部由测量脚本从 psk 量出，量的是哪个角色就填哪个角色。

判据：`FACE_BONES 18`（19 个后缀里 `LipUp` 与 `LipLo` 共享一个骨位时为 18）、`FACE_WEIGHT_VERTS` 应为面部槽顶点数的量级（守岸人 2,007）。

### 3.1 命名契约（实测口径）

引擎唯一的硬约束是**几何骨名集合与动画轨道名集合逐名相等**。骨名本身没有语义，不需要任何前缀。

| 事实 | 证据 |
|---|---|
| CN6 插件无改名功能 | `io_export_cn6.py` 的算子只有 `triangulate`、`use_selection` 两个属性 |
| ast / artdef / mtl 不引用骨名 | `grep -c 'Bip001' Assets/*.ast` 六个文件全 0 命中；ast 只记片段名 `m_AnimationName` |
| 零前缀资产在役 | 工坊 3811836710 用 `bone2`、`ALL`、`ATT_arm_L1__arm_L1` 这类 Blender 默认名，181 骨对 181 轨，集合差集为空 |

三条硬口径：

1. **源骨架零改名。** `Bip001*`、`Bone_Hair*`、`WeaponProp*` 一律保持 psk 原样。改名只会把骨表、geo、轨道、顶点组四处变成必须同步的耦合面，且加前缀不产生任何功能性收益。
2. **自建骨必须有命名空间。** 面骨按 `<code>_<后缀>`（`SK_Jaw`、`CM_Jaw`）。这是工程约定，便于在 269/433 根的骨表里一眼分区。
3. **同文件内的第二套骨链必须加后缀。** 双形态（`_Red` / `_Dark`）不是可选项：两套网格完全重合，靠两条独立骨链 + 形态根骨缩放互斥来显隐，同名骨会在骨表里塌成一根。

面骨的 **tail 方向**是命名之外的另一条契约，必须与动画侧同一套实现对齐。骨骼局部坐标系由 tail 定义，旋转通道作用在该坐标系上；tail 差 90° 会让整张脸被扯开，权重和骨名都看不出来。守岸人实测：`Brow_L` 的 tail 若沿水平轴伸（`[2.88, −4.57, 125.72]`）与沿垂直轴伸（`[2.89, −3.00, 126.68]`）是两种不兼容的实现。

### 3.2 命名闭合闸门

cook 之前跑一次，纯只读、秒级。四条判据任一不通过即停下：

| # | 判据 | 工具 |
|---|---|---|
| 1 | `.geo` 的 `<m_Bones>` 与 fgx 骨表逐名相等 | 解析 geo XML 与 cn6 骨表 |
| 2 | 每段动画 `TRACK ⊆ BONES` 且 `BONES - TRACK` 为空 | `NexusNames.exe <模型.fgx> <动画.fgx>` |
| 3 | 面骨数量 = 18 × 形态数，全部以当前 `code` 开头 | 骨表过滤 |
| 4 | `_Red` 集合与白链逐骨加后缀一一对应 | 集合差 |

判据 2 的两个方向都要查。多余轨道被引擎静默忽略（守岸人七段各多 9 根蝴蝶骨），缺轨道则那根骨不动，同样不报错。

## 四、网格修整：默认关闭

`bs_meshfix.py` 的 `push_cloth` 会逐轮把裙摆顶点推向碰撞面外侧。它的三个判据在跨角色时会失效：

- `body_names = [m for m in names if m.endswith("Body") or m.endswith("Up")]` —— `endswith("Up")` 只命中恰好以 `Up` 结尾的槽，`Up02`、`Up03`、`Alpha` 全部漏掉，碰撞体不完整；
- `arm_words = ("Hand", "Finger", "Forearm", "UpperArm", "Clavicle")` —— 这是 Civ6 领袖骨架的骨名。源骨架另有扭转骨与飘带骨，全不在表里，袖口与飘带顶点照样被推走；
- `for _ in range(3)` —— 无条件三轮，每轮以推过的坐标重建 BVH，位移累积，没有收敛判据。

守岸人实测：源模型 Z 100~120 段的 X 范围 −21.7~8.3，跑完三轮 `push_cloth` 后撑到 −62.2~62.5。游戏内表现为肩胛骨下方、双臂背面、右半裙摆的白色尖锐穿插。

`fill_surface_holes` 另有 UV 坑：UV 映射表必须在 `bm.faces.new()` **之前**取样。新面一建出来就并入 `link_faces`，其未初始化的零 UV 会覆盖映射表，补面的全部环 UV 压到贴图原点（守岸人 121 个补面把 `Bangs` 槽 3,330 面拖成退化 UV，占该槽 53.4%）。

默认口径：**源资产没有问题就不要修整**。跑纯插件链路（导入 → 缩放 → 面骨 → 旋转 → 导出），用下面的对称性判据确认无损：

```
源模型 X 范围 / Y 范围 / Z 范围  ==  产物反导后的同三项（逐材质）
UV1 退化面（面的 UV 包围盒跨度 < 1e-5）== 0
三角数不变，顶点数涨幅 = 导出插件的接缝拆点数
```

只有确认存在真实缺面时才启用修整，并且修整前后各跑一次上述判据。

## 五、贴图侧

八段材质各出一对 `.dds` + `.tex`：

| 参数 | 值 |
|------|-----|
| BaseColor | `PF_R8G8B8A8_UNORM`、**自适应档位**（默认随源图，鸣潮 `_D` 通常 2048²）、`mips = size.bit_length()`（2048²→12 级）、未压缩 |
| Opacity | `PF_R8_UNORM`、256²、`OPACITY_CLIP=85` 二值化、逐级多数决 |
| `.mtl` 的 Opacity | 只在真镂空槽绑，实心槽留空串 |
| `.mtl` 的材质类 | 一律 `Leader_Matte` |

**档位口径**：出图尺寸随源图自适应，不做静默降采样；`TARGET_SIZE`、mip 数、`.tex` 的 W/H/mips 三处一致，细节与验收见 `texture-pass.md` §五。`Leader_BaseColor` 类别上限 4096²，2048² 已验证可 cook 且无压缩回退。早期写死 1024² / 11 级 mip 的规格作废。

判定「真镂空」：源图 alpha 的两端占比 `full >= 0.01` 且 `hole >= 0.01`（`full = frac(alpha >= 0.99)`、`hole = frac(alpha < 0.10)`）。缺任一端判实心：只有 hole 没有 full 的是明暗蒙版，绑上会让整片材质变淡。工具 `scripts/probes/alpha_bind_verdict.py`。

### 5.1 颜色判断只用纯反照率渲染

`Leader_Matte` 不参与光照计算，它把 BaseColor 贴图直接输出。因此**三点布光的 EEVEE 预览不能用来判断颜色**——那张图上的明暗来自 Blender 的灯，游戏里没有。

两类预览分工写作硬规矩：

| 用途 | 工具 | 判据 |
|---|---|---|
| 颜色、亮度、贴图选取 | `workspace/_tools/bs_render_flat.py` | 材质换成 `ShaderNodeEmission`、Strength 1.0、背景 (0.05, 0.05, 0.08) |
| 几何、穿模、拓扑、朝向 | 任意三点布光 EEVEE 渲染 | 不看颜色 |

`bs_render_flat.py` 已实现上述材质替换，直接用它出图。

### 5.2 matte 实机色闸门

导 cn6 之前，逐槽算三项读数，任一不通过就换图：

| 读数 | 算法 | 判据 |
|---|---|---|
| 不透明区亮度 | 该槽 BaseColor 上 `alpha ≥ 0.5` 的像素 RGB 均值 | ≥ 120 通过；100~120 偏暗；< 100 不通过 |
| 透明占比 | `hole = frac(alpha < 0.10)` 与 `full = frac(alpha >= 0.99)` | **在压平前的源图上量**；该槽本就该镂空时除外，否则必须 `hole < 0.005`。alpha 一旦压平到 255，此项恒过、判据失效 |
| UV 足迹亮度 | 在该槽实际使用的 UV 范围内重算前两项 | 与整图读数差超 20% 时以足迹为准 |

阈值 120 来自实测：`Down_D` 202.8 与 `Upal2` 129.2 在游戏内可读，`Up02Nosi_D` 79.0 糊成一团。

### 5.3 薄纱与拖尾的特殊情况

有一类槽在 UE 的 PBR 里是半透薄纱，在 `Leader_Matte` 下会变成 83% 的洞，透出领袖场景的深色背景。代表是守岸人的 `Up02` 槽（披帛与后两条长拖尾）。

判定条件三条同时成立：

1. 该槽的 UV 足迹覆盖模型的两侧大幅面（`X` 跨度接近模型总宽）；
2. 存在一张同名但带 `Nosi`、`Alpha` 之类的半透版本贴图，其不透明占比低于 0.3；
3. 该槽在 UE 侧绑了 alpha 混合。

处理方式：**不用半透版本，改用同主体的不透明版本**。守岸人 `Up02` 用 `T_R2T1ShouanrenMd10011Upal2.png`（不透明占比 0.998、RGB 均值 129.2）而不是 `Up02Nosi_D.png`（0.173、79.0）。判定为实心，Opacity 留空串。

这条规则的依据：matte 下透明区等于空洞，洞后面的背景亮度不可控；亮而实心的贴图才能稳定呈现。

### 5.4 基色透明区怎么落色（三态判据）

`Leader_Matte` 把 BaseColor 直接输出、不参与光照，**基色 alpha 也不参与绘制**。因此透明区的 RGB 就是游戏里看到的颜色，把它当"看不见的 padding"处理会直接改观感。基色 alpha 一律压平到 255，镂空只由 `Opacity` 槽承载。

先按可见性分三态，再决定落色：

| 态 | 判定 | 落色 | 验收 |
|---|---|---|---|
| **P** 足迹外 | 落在该槽 UV 足迹之外（`dump_hair_uv.py` 的栅格） | 任意近邻色，只为压 mip；越接近周围面料越稳 | 无 |
| **V** 可见镂空 | 足迹内 + 材质**未**绑 `Opacity` | 见下方三步 | `hole_fill_audit.py` 偏差 ≤25 |
| **C** 切空洞 | 足迹内 + 材质**已**绑 `Opacity` | 保留 alpha 语义，落色只为防黑边，不得跨越足迹边界 | 偏差 ≤40 |

V 态落色三步，缺一不可：

1. **按共边长度投票，不按最近邻**。同一块面料与洞的接触边界总比别的面料长；最近邻会在两块面料交界处把另一侧的颜色灌进来。
2. **跨色禁单色**。洞的最长邻块与次长邻块亮度差 >60 时，说明这块洞横跨两块面料，整块刷单色必然错一半；改为"逐像素归属最近邻块、块内取该块中位色"。
3. **暗壳上限**。外环中位亮度 <70 时，落色亮度不得超过外环中位 +20。

三条都不成立（洞大、邻接色乱、且旧版是另一种落色）时，**回退到上一版已验收贴图的同像素 RGB**（`git show <上一版>:Textures/<槽>.dds`，尺寸一致时逐像素取）。猜错一次的成本远高于不变动。

**绝不能"保留源图 RGB"**：源 PNG 是**预乘 alpha** 的，镂空区 `RGB=0` 表达的是"无色"而不是"黑"；把它当颜色写进 DDS 等于整片刷纯黑。实测（2026-11-03 今汐 Down）三态重出版的近黑像素占 **14.589%**，回退到 `187fae0` 后只有 **3.552%**（这 3.55% 是黑色布料本身的真实像素）——多出来的 11% 全是兜底写 0 的产物。这些黑块与周边正常色形成硬边界，1 px 的锯齿台阶在细长系数 6.7 的洞上被放大成实机可见的**边缘毛刺**。

上一版贴图取不到时（首次导入、无历史版本），按序退让：① 源图 alpha>0 区域的中位色；② 该槽足迹内面料的主色；③ 中性灰（119）。**不要用 0**。

**反例（2026-11-03 今汐 Down）**：源 alpha<0.05 占 18.2%，其中 11.4% 是岛内洞，缺陷像素有 96% 落在同一个 65,870 px 的洞上。该洞最长邻块是浅色（192,188,191）、次长邻块是黑（39,43,43）——最近邻填充把肤色带进黑布，游戏内表现为"黑色胸罩下缘与内裤布料缺损"。按第 2、3 条应判为跨色洞并禁用单色；第一版处置是"保留源 RGB"，结果把 11% 的像素刷成纯黑、边缘出现毛刺（近黑占比 3.552% → 14.589%），已回退 `187fae0` 的 Down 基色。教训见上面兜底段。

**判据起点**：任何"补色"动作之前先跑 `scripts/probes/hole_fill_audit.py`，它按三态输出每个洞的面积、最长邻块色、当前落色与偏差。补过色的槽用 `--expect filled` 跑（偏差超限退出码 1），保留源值的槽用 `--expect kept`（只报数，不做数值判定）。

## 六、cook 与部署

九类告警全部必须为 0：`missing file`、`wrong extension`、`is not allowed here`、`class`、`Replacing asset`、`error asset`、`fallback`、`I/O error`、`ERRORS`。

`Replacing asset` 非 0 即说明几何或材质被替换成 error asset，不是告警而是失败。

部署判据三条同时成立：`DEPLOY_OK`、`HASH_LOCAL == HASH_DEPLOYED`、`SIZE` 与预期量级一致（守岸人 19,101,696 字节）。

## 七、踩过的坑（本会话内，全部已复现）

| 现象 | 根因 | 处置 |
|------|------|------|
| 游戏内肩胛骨下、双臂背面、右半裙摆白色尖锐穿插 | `push_cloth` 碰撞体漏 `Up02`/`Alpha`，骨名表不认源骨架的扭转骨与飘带骨，三轮无条件累积 | 关掉修整，走纯插件链路 |
| 补面区域 UV 全压到一点，局部整片铺满同色 | `fill_surface_holes` 在 `bm.faces.new()` 之后才取 UV | UV 映射在建面前取样；法线翻转改为删面重建后重新赋 UV |
| 整张脸错位，两眼落在同一侧 | 面骨在网格旋转之后才建 | 顺序固定为 缩放 → 建骨 → 写权重 → 旋转 |
| cook 报 `Entity name ... does not match`，BLP 掉到 1 MB | animset 的 `model.dst` 用了载体名而非 `ast_target` | 生成式 animset，产物名即 `ast_target` |
| 同上，geo 是 `<AssetObjects..GeometryInstance>` 单点写法 | `model.class` 写成 `Character` | 必须是 `Leader` |
| 材质段数比模型多两项，cook 后贴图悬空 | `bs_leaders.json` 的 `materials` 还列着已不生成的 `Bangs_Dark` 与蝴蝶材质 | 材质列表与实际导出的槽逐一核对 |
| 模型看着完好，实机却畸变 | Blender 里打开的是补丁前状态，工程内 fgx 是补丁后 | 每次上机前用 `open_model.py` 反导工程内的 fgx，与源模型做逐材质范围对照 |
