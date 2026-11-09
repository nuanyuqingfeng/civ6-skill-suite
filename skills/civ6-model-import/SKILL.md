---
name: civ6-model-import
description: 把鸣潮等 UE 工程的 psk 模型与 ueanim 动画导入文明6的完整管线，分领袖与单位两条链。领袖链：FModel 解包素材接入、Blender 装配重定向、cn6（模型）/FBX（动画）双链转换、NexusBatch 转换宿主、离线判据验收、入工程 cook 部署实机。单位链：psk 直导 Blender 4.5.9、60 骨上限、CivModelTool 一步导出、朝向绕 Z 逆时针 90 度、AST 时长回填，走 references/unit-template.md。附带转换工具链与脚本成品，解压即用。触发词：领袖 3D 模型导入、单位 3D 模型导入、单位动画导入、psk/ueanim 导入、cn6 转换、NexusBatch、CivModelTool、模型判据验收、BLP 部署、模型动画口型/眨眼/朝向、默认站姿、打开模型、Blender 打开模型、一键查看模型、open_model、模型窗口自动关闭、GUI 闪退、Blender 一开就关、独立打开模型、脱离会话打开、动画只播一次、一次性入场动画、循环待机、GREETING、FIRST_MEET、动画序列队列。不适用于：引用原版模型素材（用 civ6-art-reference）、Blender 导出 fgx/ast 的通用面板操作（用 civ6-modeltool）、纯 UI/音频任务。
---

# civ6-model-import — UE 模型导入文明6领袖 3D

本文是执行依据。全部流程与判据来自今汐工程（2026-10）实机验证，成功案例的完整参数在 `references/success-case.md`。**领袖模型从零到实机先读 `references/leader-pipeline.md`**（管线骨架、四步顺序铁律、纯插件判据、表情骨调用、七条已复现的坑）。其余 reference 按需读取：流程细节查 `references/pipeline.md`，判据与验收查 `references/acceptance.md`，**贴图侧（基色来源、掩膜头字段、UV 岛定位、调色曲线、自适应分辨率档位）查 `references/texture-pass.md`**，**半透明/发黑/整片消失先读 `references/translucent-pass.md`**（四层判定：归属 → 几何 → 贴图 alpha → 渲染器；发片被 alpha 裁掉要局部实心见 §四·五），**鸣潮星芒/声痕类贴花（黑底显形、图案发彩色）先读 `references/wuwa-notes.md` §9 并用 `scripts/probes/wuwa_star_decal_audit.py` 过三重门——该特例仅鸣潮触发，非鸣潮贴图严禁把可见区 RGB 置 0**，报错先查 `references/gotchas.md`，**单位类资产与「动画一挂就巨大／悬空／散架」先查 `references/anim-rest-anchor.md`**，跨会话交接查 `references/handover.md`，分发范围与上游查 `references/upstream.md`，二次运动查 `references/secondary-motion.md`，**动画播放语义（一次性入场 → 循环待机、GREETING / FIRST_MEET、动画队列与槽名绑定）查 `references/leader-animation-sequence.md`**。

**领袖模型的表情骨一律用 `scripts/face_rig.py`，不按角色另写。** 19 根面骨（Jaw、LipUp、LipLo、MouthCorner_L/R、LidUp_L/R、LidLo_L/R、Eye_L/R、Brow_L/R、BrowIn_L/R、Cheek_L/R、Nose）的后缀与角色无关，尺寸全部来自测量结果：调用方先跑一次面部测量得到 `parts_<code>.json`（eyeball.L/R 的 center_dome 与 radius_fit、mouth_z、mouth_y、mouth_half_w、browL/browR/lashL/lashR/face_verts 顶点索引），再按顺序调三件事：

```python
import face_rig
face_rig.set_prefix(cfg["code"])          # 骨名 = <code>_<后缀>，code 由 bs_leaders.json 给出
face_rig.configure(parts, MODEL_SCALE)    # parts 为该角色的测量结果，MODEL_SCALE 为整体缩放
face_rig.build_face_rig(arm, body)        # 建 19 根骨，父骨 Bip001Head
face_rig.apply_weights(body)              # 按面部顶点索引写权重
```

脚本零硬编码路径、零角色常量。新增其他 19 根面骨的姿态方法（眨眼、口型、视线、眉动）同在此文件内，按骨名索引即可，不要在工程 `_tools/` 下再复制一份。

**单位模型（`m_ClassName=Unit`）一律先读 `references/unit-template.md`**：走 CivModelTool 链，与领袖的 cn6 / NexusBatch 链不同，含 60 骨清单、朝向 90 度修正、AST 回填与全部判据。踩坑对照查 `references/unit-cases.md`（已复现 12 条 + 可能有关 5 条，后者以实际执行结果为准）。

单位链的步骤全部有参数化脚本，不必现场写一次性脚本：`scripts/unit/unit_build.py`（构建与烘焙）、`unit_export.py`（CivModelTool 导出）、`unit_ast_audit.py`（AST 审计与时长回填）、`unit_geo_audit.py`（净旋转与静止骨长）、`unit_yaw_audit.py`（站立朝向，切动作时模型是否转向）、`patch_shape_rebuild.py`（贴片按蒙版轮廓重建成三角网并继承权重）、`resample_audit.py`（重采样是否产生重复帧）、`shared_data_conflict.py`（两个 mod 部署目录的同名资源比对）、`alpha_rgb_audit.py`（全透明像素是否残留颜色）。参数与已验证读数见 `unit-template.md` 第六节与第九节。脚本不以文件名前后缀、槽位名或贴图命名作假设。

单位上的轮廓类贴片（纹样、刻印、纹路）走 `references/case-unit-surface-patch.md`：单位材质没有 `Opacity` 槽，轮廓只能写进几何，三条判据（拟合残差、质心漂移、权重继承数）都内建在 `patch_shape_rebuild.py` 的断言里。

## 〇、本机 Blender

**一键打开模型（最先看这里）。GUI 单进程：导入 → 挂贴图 → 材质预览 → 取景，一条命令搞定。完整流程、判据与故障树见 `references/open-model.md`。**

```
E:/SoftWares/blender45/blender-4.5.9-windows-x64/blender.exe --python "E:/SoftWares/blender45/open_model.py" -- "<模型完整路径>" [--tex-root <额外贴图目录>]
```

- **首选：双击 `E:\SoftWares\civ6_nexus_work\dj_preview\打开当前模型.cmd`**（或把任意 `.cn6/.psk/.fgx/.blend` 拖到它上面）。这是两阶段自举启动器：入口只把执行器交给 `explorer.exe` 后立刻退出；执行器由桌面 shell 派生、启动 Blender 后退出；Blender 最终**没有活父进程**，不属于任何 agent 会话树，窗口不会因命令/会话结束而消失。分发模板是 `scripts/open_model_launcher.cmd` + `scripts/_open_detached.cmd`，与本机实例逐位一致。
- **agent 会话内直接跑上面那条命令**：必须 `run_in_background: true`，但窗口仍挂在会话树内，只适合临时查看；要长期留窗口就调用启动器（从会话内调用启动器同样能脱离，2026-11-06 实测通过）。
- **实测边界（2026-11-06，替换旧「explorer+cmd 全部实测不可用」结论）**：job object 禁止 breakaway（`CREATE_BREAKAWAY_FROM_JOB` → WinError 5）；一次性 `Start-Process`、WMI 进程创建、COM 实例化、`schtasks.exe`、运行时编译均被回收或拦截；**`explorer.exe <执行器.cmd>` 是唯一验证可用的脱离路径**（父 PID 随即消失，跨命令复核 uptime > 200 s 仍存活）。`E:\SoftWares\blender45\OPEN_MODEL.cmd` 只适合人工拖放，不要在 agent 会话里当独立启动器用。

无头 / 批量（不弹窗，只落一个 blend）——加 `--no-gui --out`，`-b` 自己会退出，不涉及存活问题：

```
set "BLENDER_USER_RESOURCES=E:\SoftWares\blender45\userres"
"E:\SoftWares\blender45\blender-4.5.9-windows-x64\blender.exe" -b --python "E:\SoftWares\blender45\open_model.py" -- "<模型完整路径>" --no-gui --out "%TEMP%\blender_view_<名>.blend"
```

> cmd 里必须分两行、并且用 `set "VAR=值"` 的引号形式。写成 `set VAR=值 && …` 会把 `&&` 前的**尾随空格**写进变量，实测 `BLENDER_USER_RESOURCES` 变成 `…\userres `，Blender 把 extensions 缓存路径解析成 `userres \extensions` 并报 `WinError 3`。bash 下等价写法是先 `export BLENDER_USER_RESOURCES=E:/SoftWares/blender45/userres`，再直接跑第二行。

- 格式：`.cn6` / `.psk` 直接导入；**`.fgx` 自动先经 `E:\SoftWares\civ6_nexus_work\CivNexus6\FgxToCn6.exe`（NexusBuddy cn6Export 的无头复刻，逐位无损，男漂 fgx 对照原始 cn6 验证：位置最大偏差 5e-05 cm、三角面 0 差异）反向转 cn6 再导入**；`.blend` 直接 `open_mainfile` 并且**不重建材质**（交付文件里的节点图原样保留）。
- 贴图匹配（2026-11-02 通用化，不再写死四个工程目录）：优先级 `--tex-root` > 环境变量 `CIV6_TEX_ROOTS`（`;` 分隔）> 模型周围 4 层内的 `Textures`、`*\Textures` > `CIV6_MOD_ROOT`（默认 `D:\documents\Firaxis ModBuddy\Civilization VI`）下每个工程的 `<工程>\<工程>\Textures`。按「规范化名字体」对撞：去 `T_`/`MI_` 前缀、去 `_D`/`_D2`/`_BaseColor`/`_Albedo`/` 134 108` 这类尾巴，支持 `.dds/.png/.tga/.jpg`。同一名字体多命中时的排序是 **根目录优先级 → 精确体 > 前缀体 → 更具体的键（`Up02` 压过 `Up`）→ `.dds` > `.png` > `.tga` → 名字更短（`_D` 压过 `_D2`）→ 文件更大**。
- 视口/灯光/世界（参数照抄已验证配方，数值别改）：材质预览 + `use_scene_lights/use_scene_world`，**关掉 overlays 与 gizmo**（得到干净纯色底，没有网格和坐标轴）；正交 `ORTHO`，`clip_start=1.0`、`clip_end=6000.0`，`view_distance = H × 1.18`，`view_location = (包围盒中心 x/y, zmin + H/2)`；3 盏 **AREA 12000 W / size 180**，位置 `(40,-160,190)`、`(-150,-120,100)`、`(0,170,150)`，绕 X 转 ±90°；世界换成 `StudioWorld`，色 `(0.72,0.75,0.80)`、强度 `0.35`；渲染 `EEVEE Next` + `view_transform='Standard'` + `look='None'` + `exposure=0`。
- 上述灯架与视角会**整体偏航到模型自己的正面**（按包围盒判定：水平两轴里更短的是深度轴，**伸出较少的一侧是正面**，因为头发/薄纱往后拖）。朝向 -Y 的模型偏航 0°，`view_rotation` 就是 `Euler(90°,0,0)`；朝向 +X 的模型偏航 90°，等同 `Euler(90°,0,90°)`。日志里 `front=` / `yaw_deg=` / `view_rot_deg=` 三个值可以核对。
- 用面积光而不是 Sun：小角度 Sun 在这套密集的裙摆/薄纱几何上会出**阴影痤疮**，看上去就是满身小黑色方块；换 AREA 后消失。要看阴影可设 `WB_SHADOWS=0` 关掉视口阴影。
- 透明度：按 alpha 两端占比判定——`full = frac(alpha >= 0.99) >= 0.01` 且 `hole = frac(alpha < 0.10) >= 0.01` 才把 Alpha 经 `GREATER_THAN(0.3333)` 接到 Principled 并设 `surface_render_method='DITHERED'`，否则保持实心。缺任一端即判实心：只有 hole 没有 full 的是明暗蒙版，绑上会让整片材质变淡（秧秧 `Body`：max 0.565、full 0.0000、hole 0.1417，旧判据误绑，皮肤整片半透明）。
- 判据：`%TEMP%\open_model.log` 末行是 `OPEN_MODEL_OK`。GUI 模式下同一日志里还有 `OPEN_MODEL materials=8 textured=8 cutout=2 …`（`textured < materials` = 没配上图，回头看 `tex_roots=` 命中数）、`OPEN_MODEL   probe <图名> size=… full=… hole=…`（逐槽贴图与 alpha 两端占比）以及 `OPEN_MODEL view={… 'front': [1.0,0.0,0.0], 'yaw_deg': 90.0, 'view_rot_deg': [90.0,-0.0,90.0], 'lights': 3, 'shading_failures': []}`。`shading_failures` 非空说明某个视口属性名不对，先修这里再谈画面。
- 自检抓图：`--snap <png>` 会在应用视口后做一次 `render.opengl` 抓图。**注意它是单采样 GL 抓图，抗锯齿/抖动噪点比实际视口和 EEVEE 正式渲染明显得多**，别拿它当画质判据；判断打光和贴图请用 `render.render`（EEVEE）出图。
- 性能（2026-11-02 实测，守岸人 cn6 / 59608 verts）：单进程 **16.5 s**（import 16.3 / scan 0.1 / materials 0.0）；旧的两步法约 26 s 且多写一个 32 MB 中间 blend。每阶段耗时打在 `OPEN_MODEL timings …` 那行。
- 两个脚本的分工：`open_model.py` 负责导入 / 贴图 / 进度日志；`view_setup.py` 负责视口预设，也能单独用来开任意 `.blend`（`blender.exe <x.blend> --python view_setup.py`）。改这两个之前先用上面的命令跑一遍守岸人 cn6 与一个 `.blend`，确认识别数没退化。FgxToCn6.exe 仍禁改，源码在 `E:\SoftWares\civ6_nexus_work\rover_view\FgxToCn6.cs`。
- 本命令只管**打开查看**（导入后 rest 态、无 pose）；导出 cn6 的 Blender 选型见下文「cn6 导出用哪个 Blender」。
- **禁改** `E:\SoftWares\blender45\open_model.py` 与 `FgxToCn6.exe`（源码在 `E:\SoftWares\civ6_nexus_work\rover_view\FgxToCn6.cs`，复刻 NexusBuddy.FileOps.CN6FileOps.cn6Export，绕开 GUI 表单资源缺失与 x64 裸指针 AV 两个坑）；要调整「打开」行为只改启动器与 `references/open-model.md`。

```
E:\SoftWares\blender45\blender-4.5.9-windows-x64\blender.exe
```

本机三份 Blender，用途不可互换（插件列表为实测加载结果）：

| 版本 | 绝对路径 | 已加载插件 |
|------|---------|-----------|
| **4.5.9 LTS** | `E:\SoftWares\blender45\blender-4.5.9-windows-x64\blender.exe` | cn6 导入导出、psk/psa、UEFormat、GR2、mmd_tools。**唯一装齐 psk/psa 与 UEFormat 的版本，管线只用这一份** |
| 5.2.3 LTS | `C:\Users\Administrator\.agents\skills\civ6-modeltool\tools\blender\blender-5.2.3-windows-x64\blender.exe` | 仅 CivModelTool，无 cn6/psk/UEFormat；形态键转骨在 5.2 失效 |
| 2.83.0 | `E:\SoftWares\blender-2.83.0-windows64\blender.exe` | cn6 导入导出、na2、mmd_tools；缺 psk/psa 与 UEFormat，导入不了 psk/ueanim |

资源根：`BLENDER_USER_RESOURCES` 取 `E:\SoftWares\blender45\userres`。

### cn6 导出用哪个 Blender（E5 实测）

cn6 导出固定使用 Blender 2.83.0。

- 两版插件清点：2.83.0 已装 14 个插件，含 `io_export_cn6`、`io_import_cn6`、`io_import_na2`，算子 `export_shape.cn6` 存在；4.5.9 已装 10 个插件、默认没有 `io_export_cn6`，显式启用后算子注册成功，一调用就在 `io_export_cn6.py:294` 抛 `AttributeError: 'Mesh' object has no attribute 'create_normals_split'`，走 `.blend` 直出则在 `io_export_cn6.py:233` 抛 `KeyError`。
- 2.83.0 产物：cn6 11,509,978 字节、顶点 40661、三角 56483、骨骼 222、材质 9；转出的 fgx 1,931,204 字节；同一段动画 JX_IDLE 的 FBX 5,040,300 字节（1133 帧）转成 anm 773 字节。
- 顶点成员（`NexusDumpBind` 摘要）：Position／BoneWeights／BoneIndices／Normal／Tangent／Binormal／TextureCoordinates0 全部存在，stride 76、权重槽 8，binormals 与 tangents 在 cn6 产物里保留。
- 角法线探针（`cn6_corner_normals.py`）：`has_custom_normals` True；反向角法线占比 Bangs 565/1930＝0.293、Hair 1591/9148＝0.174、Face 852/4030＝0.211，其余网格 0。
- 未验项：`jx_dark_seam.py` 需要 ingame12 实机截图目录，本机缺该目录，读数未取得；实机发片两色未验。
- 证据：`workspace/gen/reports/wp16-e5-blender-ab.md`。

## 一、与相邻 skill 的分工

| 任务 | 用谁 |
|------|------|
| 让某单位/建筑/资源用上原版模型素材（克隆引用链） | civ6-art-reference |
| Blender 侧通用 fgx/ast 导出面板、形态键转骨、civhash | civ6-modeltool（Sumcam-L 工具链；其形态键转骨模块在 Blender 5.2 不可用） |
| 素材解包（psk/ueanim/贴图） | 本 skill 第 1 步（首选 dsh-ue-asset 插件 HTTP 通道，次选其 MCP 通道，FModel 兜底；ACL 补丁在 `patches/`） <!-- WUWA --> |
| 领袖 3D 模型从零到实机的全管线 | 本 skill |
| 游戏内实机取证与生命周期控制 | civ6-tuner |

## 二、参数槽位（开局先替换成本机实际值）

| 槽位 | 含义 | 今汐工程实测值 |
|------|------|---------------|
| `<方案根>` | `.civ6sln` 所在目录 | `D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi` |
| `<工程名>` | 项目主体目录名，与 `.civ6proj` 同名 | `Jinzhou_Jinhsi` |
| `<领袖 XLP>` | cook 目标，`<工程名>/XLPs/leader_<代号>_qyqxp.xlp` | `leader_jinhsi_qyqxp.xlp` |
| `<正样本工程>` | 同引擎正常领袖的项目主体目录，判据背书来源 | `D:\desktop\mods-CIV6\others\Denia_Pack\Denia_Pack` |
| `<转换宿主>` | `NexusBatch.exe` 与读数工具目录 | 本包 `tools/CivNexus6`，部署到 `E:\SoftWares\civ6_nexus_work\CivNexus6` |
| `<SDK>` | Civ6 Development Tools 安装目录 | `F:\Steam\steamapps\common\Sid Meier's Civilization VI SDK` |
| `<Mods>` | 游戏 Mods 目录，BLP 部署位 | 由 `civ6-tuner` 的 `gamectl` 探测；本机不在默认 Documents 路径 |
| `<素材目录>` | 解包产物根，`Characters\<角色>` | `G:\Wuwa_3D_Assets\Characters\<角色>` <!-- WUWA --> |
| `<Blender>` | 4.5.9 LTS 可执行文件，见 §〇 | `E:\SoftWares\blender45\blender-4.5.9-windows-x64\blender.exe` |

## 三、开工自检（逐条执行，全部通过才进第 1 步）

```bash
test -f "<转换宿主>/NexusBatch.exe" && echo NEXUSBATCH_OK
test -f "<Blender>" && "<Blender>" -b --version | head -1                                                  # Blender 4.5.9
ls "E:/SoftWares/blender45/userres/scripts/addons/" | grep -c cn6   # 2
ls "<正样本工程>"/*.civ6proj
ls "<方案根>/<工程名>/XLPs/" | grep qyqxp
git -C "<方案根>/<工程名>" status --short | head -5
python -c "import zstandard; print('zstandard', zstandard.__version__)"
# 领袖任务加跑 G0 表情数据链探测（A 路线唯一默认；无曲线 → 询问协议，禁止静默降级）：
python scripts/expr_route_gate.py probe --curves-dir <素材>/curves \
    --morph-keys <形态键清单.json> --fit-table <拟合表bones.json> --char <代号>
```

任一失败即停下补环境，来源与安装方式见 `references/upstream.md`。运行 Blender 前设 `BLENDER_USER_RESOURCES=E:\SoftWares\blender45\userres`。G0 判定与询问协议见 `references/expression-route.md`。

## 三·五、失败归因纪律（硬闸门）

**连续两次修不好，先别动素材——去证明工具在骗你。** 本条优先于下面的所有流程；触发即暂停当前修复。

### 零、表情数据链硬闸门（优先于本节及其余一切流程）

领袖模型的表情层**只有一条默认路径（A 路线）**：官方解包 AnimCurve（`curves/*.uecurves.json`）→ 逐帧权重表 → `curve_blink` 长短闭眼分层 → 合成后限幅 → 面骨蒙皮闸门。全链与决策状态机见 `references/expression-route.md`。四条铁律：

1. `E_Close` 的逐帧权重**绝不进入 `morph_fit.pose()` 拟合层**（走拟合层只有 0.4 倍行程且下睑反向，实测 0.659cm vs 应有 1.549cm），只注入 blink 通道；
2. 「找不到官方曲线」必须先补导（`scripts/unpack_expr_curves.sh`）再复核 `expr_route_gate.py probe`；补导后仍无「曲线名 ∩ 形态键清单 ∩ bones>0」命中才允许询问；
3. 询问给出探测证据 + B1/B2/B3 方案（含影响与回退点），**只有用户明确点名某一方案才算授权**；中断、无答复、答非所问、「你看着办」、多选、工具异常、超时一律 **ABSTAIN = 不做**（零写操作，只写闸门日志与报告）；
4. A2 局部补位（某段无曲线 / 短眨眼交回 blink_plan / MANUAL_GAIN=0.55 互补混合 / f>source 冻结段交回人工）属已验证链路，照常执行但必须在报告记录。

交付报告的固定字段（缺项按未验收处理）：曲线来源（绝对路径/文件数/sha8/补导命令）、路线判定（A/A2/B-授权编号/ABSTAIN）、询问记录（触发原因＋答复原文＋判定）、未执行项清单、`E_Close` 是否误入拟合层（必须为否）、`curve_blink` 分层与限幅、G0–G3 结果与注入自检、偏差栏。禁止把「离线全绿」写成「实机正确」。

### 五个触发器（满足任一即转入工具取证）

| 触发器 | 动作 |
|---|---|
| 同一现象第 2 次修复仍复现 | 冻结改动，列出链上每个工具/脚本，逐个做对照实验 |
| 实测值与应有值偏差 > 2 倍 | 先证明读数可信，再谈原因 |
| 连续多次"验收全绿"但实机不对 | 验收脚本作废，先做反向闸门 |
| 工具报错但换输入就好 | 不是素材问题，是输入形态问题（路径/编码/大小写/权限） |
| 两个工具读同一资产结果不同 | 先查版本与数据源完整性（补丁包/密钥/缓存） |
| 用户指认「不是这一版」「又把旧毛病带回来了」 | 停手做时间锚定（`misattribution.md` §五·5），**不做第二次语义猜测** |

### 四个自检问句（任何结论前）

1. 这个数是从**哪个文件**读的？是产物、中间态，还是缓存？
2. 有没有**第二条独立通道**能读到同一事实？
3. 如果工具是对的，这里应该是什么**量级**？差了几倍？
4. 我做过一次**会失败**的实验吗？

### 三条配套规则

- **反向闸门**：任何验收脚本必须能对注入的已知错误 FAIL；注入后仍 PASS 即作废。工具 `scripts/gate_selftest.py`。
- **证据分级**：A=双通道实测、B=单通道实测、C=推理。**C 级结论不得作为交付依据。**
- **迭代脚本不复用**：视觉迭代（调色、alpha 打通、几何微调、取景）每一轮**新写**脚本，不 import、不复制上一轮。旧脚本里写死的色阶系数、面集、阈值就是被否决的方案本身；复用等于把否决过的口径带回来。脚本名与产物名都带轮次或时间，回退点按轮次留。

### 补丁准入（治标脚本）

**补丁必须能被单独关掉；关不掉的不叫补丁，叫负债。** 提出前四问：病灶定位到哪一行/哪几个顶点、绕过什么、能否单点关闭、什么现象消失后必须删。缺一不许合入。出现"补丁需要补丁"、"同一症状第 2 个补丁"时**停止叠补丁**，回到病灶定位。

细节：`references/misattribution.md`（案例矩阵与取证动作）、`references/patch-lifecycle.md`（四类处置与 A/B 三步）。

## 四、任务分流

| 现状 | 走法 |
|------|------|
| **打开 / 查看模型、预览贴图、模型窗口一开就关、要一个长期留着的 Blender GUI** | **只读查看任务，不进十步流程、不 cook、不部署**。先读 `references/open-model.md`；双击（或把 `.cn6/.psk/.fgx/.blend` 拖到）`E:\SoftWares\civ6_nexus_work\dj_preview\打开当前模型.cmd`，分发模板 `scripts/open_model_launcher.cmd`。**跨 ≥2 条独立命令复核 PID + hwnd + uptime，且父链不含 `sandbox-cli/bash/WorkBuddy` 才算打开成功；命令内轮询不算** |
| **同一现象修两次仍复现、或"全绿但实机不对"** | **停止改素材**，读 `references/misattribution.md`：五个触发器、四个取证动作、证据分级 |
| **实机表情/眨眼完全无变化，但动画侧读数正常** | 先跑 `scripts/face_skin_gate.py`（G1 几何蒙皮 / G2 动画轨迹 / G3 装配一致）。palette 里没有面骨 → `references/face-skin-gate.md`；这是"动画全绿、实机不动"的第一嫌疑 |
| **新领袖表情层接线（建链，非排障）** | **必读** `references/expression-route.md`：G0 探测 → 补导 → 权重表 → `face_expr_runtime.py` → G1/G2/G3，A 路线唯一默认；无曲线 → 询问协议行（下一行） |
| **找不到官方表情曲线 / 曲线白名单全空** | `references/expression-route.md` §三询问协议 + `scripts/expr_route_gate.py`：补导→复核→B1/B2/B3 需用户明确点名；未获点名授权 = ABSTAIN 不做 |
| **表情强度/时序不对，或缺官方微表情** | `references/morph-curves.md`：曲线白名单、帧对齐实测、拼接与冻结段、互补混合、双实现校验；生成器 `scripts/morph_curves.py` |
| **眨眼不闭、只闭一半、下睑外翻、眯眼笑穿模** | `references/blink-and-eyelids.md`：通道选择（`E_Close` 不能走拟合层）、短脉冲/长闭眼分类、合成后限幅、下睑轴向陷阱 |
| **要增删或降级某段动画引用** | `references/ast-anim-binding.md`：四处容器同步改；`scripts/ast_bind.py --drop/--to-idle`（注意 drop 与降级是两种语义） |
| **想让某段动画只播一次、随后停在循环待机；或问「单个片段能不能只播一次」；或要区分「每次打开界面」与「存档首次会面」** | **先读** `references/leader-animation-sequence.md`：引擎原生 `LeaderAnimations` 序列表 + Lua 队列（`Sequence=一次性;循环IDLE`），循环不是片段属性；三种语义、三条落地路线、最小验证实验、红旗清单全在该文档。改 AST 绑定时仍按上一行的四处容器同步改 |
| **要写治标脚本** | `references/patch-lifecycle.md`：准入四问、默认关闭、自报改动量、写退出条件；模板 `scripts/_patch_template.py` |
| 新领袖模型从零导入 | 先读 `references/leader-pipeline.md`；第五节十步流程，每步判据在 `acceptance.md` |
| 同一领袖换素材重出（模型或贴图换源） | `references/leader-pipeline.md` 第一节的四步顺序 + 第四节的纯插件对称性判据；不要复用上一次带网格修整的脚本 |
| 换一个从未做过的角色 | 同「新领袖模型从零导入」；表情骨直接用 `scripts/face_rig.py`，只重跑测量生成 `parts_<code>.json` |
| 已有模型改某一属性（缩放/朝向/材质/动画） | 先查 `gotchas.md` 对应条目；改动只允许落在四项定稿参数之外（cn6 链、朝向 δ、Q/p_Q 换算、`arm_c.scale`）；改完必跑第 5/8 步判据并完整重跑管线（清 staging → NexusBatch → assemble → ast_normalize → cook → 部署 → 重启） |
| 动画一挂上模型就散或拉伸 | 十有八九把模型 rest 当成了动画 Q，读 `acceptance.md` §Q/p_Q |
| 模型巨大、悬空、肢体错乱（去掉动画绑定就正常） | 片段与静止姿态不同源。先跑 `scripts/check_clip_anchors.py`，三条锚点与两个常数见 `references/anim-rest-anchor.md`；先做 `IDLE_A` 过闸再批量 |
| **任何单位模型任务（`m_ClassName=Unit`），无论首次还是重建** | **一律先读 `references/unit-template.md`**：走 CivModelTool 链（Blender 4.5.9 装配 + Blender 5.2.3 导出），60 骨上限、朝向绕 Z 逆时针 90 度、AST 时长回填、净旋转判据全在该文档。踩坑对照 `references/unit-cases.md`；只在模板明确不通时再回落领袖十步流程 |
| 单位模型动作一挂就散、拉伸、通道数为 0 | 先查 `references/unit-cases.md` C01（动作名前缀与 slot 显示名）与 C02（`orig_loc`/`orig_quat`/`post_quat` 三属性） |
| 单位模型朝向差 90 度 | `references/unit-template.md` 第五节：`ROT_Z90 = Matrix.Rotation(math.radians(90.0), 4, 'Z')`，骨架与网格同时施加，烘焙时 `m = ROT_Z90 @ sb.matrix`；判据是踝→趾指向 +X |
| 模型完全不显示但包已加载、cook 无报错 | 先做「去绑定」分离：清空 ast 的 `m_animationBindings`、`m_timelineBindings`、`m_timelines`、`m_Animations` 四个容器的内容（保留容器标签），重 cook 一次。模型正常即动画链问题，仍不显示则查贴图像素格式（DXT5 源配 RGBA8 声明会让 alpha 全零） |
| 发丝、裙摆、飘带没有动画或显得僵硬 | 素材里有 `Rib_*` 片段时先走覆盖层，没有才解算；`references/secondary-motion.md`：RibbonAnim 覆盖层、角度弹簧与质点链两套解算器、标定口径、循环接缝、增骨的做法与失败特征 |
| 模型整体拉倒并放大 100 倍 | FBX 链写入了 `0.01·R_x(+90°)·restWorld⁻¹` 与 `diag(100,100,100)`；模型改走 cn6 链，动画骨架 `arm_c.scale=0.01` |
| 面部表情畸变（薄片拉成尖刺、整脸错位） | 形态键表与合成方式的口径不匹配，读 `acceptance.md` §形态键转面骨；`--face-diag` 的 `MORPH_DIAG` 双口径一跑即知 |
| 待机插入动作在接缝处跳一下 | 重复帧加末端速度归零，读 `acceptance.md` §循环插入接缝；逐骨步长用 `jx_diag_track.py` 量 |
| 跑停或攻击收尾后切待机，模型原地转向一个小角度 | 各片段首帧髋线朝向不一致。修正在烘焙时把站立类片段的首帧统一到停止片段末帧朝向，写入 `Bip001` 的 `rotation_quaternion` 曲线（写 `Root` 会被引擎当成真实转身）。判据用 `scripts/unit/unit_yaw_audit.py`，方法见 `unit-template.md` §六「站立朝向判据」 |
| 待机时某个部位低幅度抖动，画面整体正常 | 输出帧数大于源帧区间跨度，重采样产生重复帧。先跑 `scripts/unit/resample_audit.py --clip NAME:START:END:OUT`，判据是 `dupes=0` 且步长集合为 `[1]`；口径见 `secondary-motion.md` 第十二节 |
| 单位模型身上要贴轮廓类花纹（声痕、刻印、纹路） | 单位材质没有 `Opacity` 槽，轮廓必须写进几何。读 `references/case-unit-surface-patch.md`，用 `scripts/unit/patch_shape_rebuild.py`；三条断言（拟合残差、质心漂移、权重继承数）不满足即退出码非零 |
| 两个 mod 同时装载后其中一个动作不触发 | 资源名在引擎里全局寻址。先跑 `scripts/unit/shared_data_conflict.py --mods A B`，同名异内容才是冲突；处置见 `gotchas.md` 第 85 条 |
| 贴片边缘出现一圈彩色毛边 | 全透明像素的 RGB 引擎照画。跑 `scripts/unit/alpha_rgb_audit.py <图>`，退出码 0 即干净；处置见 `texture-pass.md` 第二节 |
| 贴图出现肤色斑、布料缺损、局部黑斑 | 基色镂空区落色错：`Leader_Matte` 直出 RGB，透明区照样显示。先跑 `scripts/probes/hole_fill_audit.py -- --src <png> --dds <dds>` 按三态判据看偏差，再决定补色或兜底；兜底一律取上一版已验收贴图的同像素 RGB，**绝不保留源图 RGB**（源图预乘 alpha，镂空区 RGB=0 会被写成纯黑）。口径见 `leader-pipeline.md` §5.4、矩阵见 `texture-rules-matrix.md` |
| 贴图边缘毛刺且黑区变大 | 兜底写了预乘 0。对比新旧近黑（亮度<30）占比，差 >2 个百分点即失败；处置同上一行 |
| 星芒/声痕贴花整块显形（黑底），或切形正常但图案是彩色的 | 源图 RGB 是 mask 语义不是颜色：黑底＝alpha 蒙版被压平，彩色＝可见区 RGB 直出 | **先跑三重门** `scripts/probes/wuwa_star_decal_audit.py`（主题 + mask 语义 + 材质双槽）。命中（**仅鸣潮**）→ RGB 全置 0 且保留蒙版；未命中 → 通用贴花行，**可见区 RGB 一个字节都别动**。见 `wuwa-notes.md` §9 |
| 半透明区域发黑、整片消失、边缘毛刺 | 四层顺序：归属（这块面属于哪个槽）→ 几何（该不该透明）→ 贴图 alpha（frac 阈值）→ 渲染器（`surface_render_method` 与背面剔除）。读 `references/translucent-pass.md`，禁止直接调 alpha 系数 |
| **发片/刘海被 alpha 裁掉、要局部实心**（额发偏浅、发丝缝漏光，几何明明存在） | `references/translucent-pass.md` §四·五：就地 alpha 打通。粒度是 texel 不是面；RGB 逐字节保源图、只打通正面+侧向面集的完整 UV 岛、背向面保留源 α。色阶移位与并集平铺都已否决 |
| 两块面卡之间透光、有明显空隙 | 空隙是**没有面**，贴图打通无效。先用射线分层取证确认是「无面」还是「被裁」，再决定补内衬/合并面/收顶点；不要把空隙当透明度问题调参 |
| 贴图异常（黑块、毛刺、穿透、BLP 缩水） | 先怀疑手工 `.tex`：改走 CivNexus6 的 `Process Texture into .dds/.tex` 生成 dds/tex 对，再用 `workspace/gen/tools/wp2/wp2_texpair_check.py` 类判据复核；依据见「与社区工具链对齐」节 |
| 整包贴图换源（素材重出） | 按 `texture-pass.md` 判据一选源并统计四项读数，再逐槽位重出；按判据五自适应出图档位（默认随源图 2048²），DDS 头 / `.tex` 的 W/H/mip 三处一致 |
| 贴图局部调色（某块偏灰、偏暗、颜色族不对） | 按 `texture-pass.md` 判据三先做骨骼分组 UV 岛掩膜，再与颜色判据相交；禁止用颜色阈值或形态学直接定位 |
| 材质绑了 Opacity 但整块几何不显示 | 按 `texture-pass.md` 判据二核对掩膜 DDS 的 `pixelformat.dwFlags`（偏移 80）与 `caps`（偏移 108） |
| 选片段拿不准哪些属于待机、哪些属于战斗 | 先按第五节「选片前的基本口径」判断；族名对照表见 `references/wuwa-notes.md` 第三节 <!-- WUWA --> |
| 动画链要改动（改名、换片段、重编导入器、导出 na2） | 先查「与社区工具链对齐」节的动画路由：现链保留 Blender 4.5 FBX 加 CivNexus6 导入器，na2 导出走 `Na2Tool.exe` |
| 实机画面与预期不符 | 先对部署指纹（BLP 字节数 + sha256 前 16 位），再判断是没生效还是真缺陷；画面判断由人执行并口述 |
| 接手别人半成品 | 按 `handover.md` 六要素核对，第一动作是验证基准指纹仍成立 |
| **用户用时间或截图指认「就要那一版」** | **禁止按语义重建**。走 `references/misattribution.md` §五·5 时间锚定法：会话 jsonl 时间戳 → 产物 mtime → sha16，先出「时间／文件／字节／sha」清单让用户勾选，勾定再动手，并把该文件另存 `_ANCHOR` 副本。连续两次猜错即触发 §三·五 硬闸门 |
| 迭代脚本要不要复用上一轮的 | **不复用**。视觉迭代（调色、alpha、几何微调）每轮新写脚本，不 import 不复制；旧脚本里写死的系数/面集/阈值就是上一轮被否掉的口径本身 |

## 五、十步流程

| 步 | 动作 | 产物或判据 |
|----|------|-----------|
| 1 | 接手或立项：读交接文档；无则建 goal 与六栏留痕；清空 staging 与 `<转换宿主>` 旧产物 | 留痕文件、空 staging |
| 2 | 素材取证：FModel 直读引擎参数（骨骼/材质段/LOD/morph/物理链/贴图），写审查报告并冻结不可迁移项 | 审查报告落 `workspace/gen/reports/` |
| 3 | Blender 装配：单骨架场景、骨架对象零变换、ueanim 平移 ×100（米→厘米） | 场景只含 1 骨架 + 网格 |
| 4 | 模型链 cn6：`bpy.ops.export_shape.cn6` → NexusBatch `ImportCN6` | `MODEL_DONE` 回显 + 产物哈希 |
| 5 | 离线判据（第一次闸门） | 四条判据全绿，新阈值先拿正样本跑 |
| 6 | 朝向归位：数据求 δ，骨架绕垂直轴转 −δ，网格随转 | 重跑四条判据 |
| 7 | 动画链 FBX：标定 Q/p_Q 落 `anim_channel_map.tsv`；反解烘焙每帧叠 EPS=0.01°；`arm_c.scale=(0.01,0.01,0.01)`；fps=30 | 逐骨标定表 |
| 8 | 判据复核（第二次闸门）：四判据重跑 + 与正样本并列出表；动画用 NexusBoneCurve 或 FgxViewer 旁路核对 | 两通道结论一致 |
| 8.5 | 二次运动：素材有 `Rib_*` 片段就整条覆盖旋转通道（1:1，不做增益），没有则短链走角度弹簧、长链走质点链并按族标定；循环片段做接缝检查 | 轨道节点数大于 1 才算真有曲线（`NexusAnimAmp.exe`）；曲线参数与峰值表落 `workspace/gen/reports/`，衔接见 `references/secondary-motion.md` |
| 8.6a | 表情数据链（硬闸门，见 §三·五零）：`expr_route_gate.py probe` 探测官方曲线 → 缺则 `unpack_expr_curves.sh` 补导 → `morph_curves.py build/verify` 逐帧权重表（双实现 MAE=0，E_Close 列保留） | `P1_1_RESULT` 级比对全等或来源指纹 manifest；无曲线未获授权 = ABSTAIN |
| 8.6b | 形态键→面骨拟合：全部面部形态键（今汐 86 个）逐骨加权刚体拟合成面骨通道，再做 LBS 一致性迭代 | `MORPH_DIAG` 均方 ≤0.15 厘米、`MORPH_GAP` 零权重顶点为 0，口径见 `acceptance.md` §形态键转面骨 |
| 8.6c | 表情运行时合成：`scripts/face_expr_runtime.py`——曲线为底互补混合（剔除 E_Close）、`curve_blink` 长短闭眼分层、`takes_over_jaw/brow` 让位、`ensure_lid_close` 下睑保底、`clamp_lids` 合成后限幅 | 闭眼幅度达 `BLINK_DOWN_CM` 量级（御三家实测 1.462–1.520cm 通道）、限幅触发数记录 |
| 8.7 | 循环拼接：插入片段做进入与退出过渡，端点姿态与两端速度都要对上 | 接缝逐骨步长连续、无重复帧，判据见 `acceptance.md` §循环插入接缝 |
| 9 | 入工程：`jx_assemble.py` → `jx_ast_normalize.py`（顺序固定）；ast 槽位与正样本一致，时长取 `.anm` 实际值 | 只写目标 ast |
| 9.5 | 贴图定稿：基色来源、掩膜头字段、局部调色掩膜三处按 `texture-pass.md` 五道闸门过一遍，并先跑一次 `open_model.py` 预览 | 预览末行 `OPEN_MODEL_OK`；四项读数与掩膜预览入留痕 |
| 10 | cook + 部署 + 实机：九类告警全 0、体积合规；BLP 快照回退点；部署位与产物哈希逐位一致；完整重启后由人观察 | 部署指纹入留痕 |

命令与参数在 `references/pipeline.md`，判据阈值在 `references/acceptance.md`，成功案例的完整数值在 `references/success-case.md`，发丝与衣物的二次运动在 `references/secondary-motion.md`。

第 8.6 与 8.7 步的判据是 2026-10-30 补入的：形态键转面骨的坐标系错一层就会把整张脸甩出几十厘米，循环拼接的速度断点只出现在接缝之后一帧，两者都必须先用数值判据验收，画面观察排在其后。

### 选片前的基本口径

片段归哪一类由目录与族名决定，名字里的 `Action`、`Skill` 不表示用途。判断顺序是目录归属 → 族名前缀 → 片段时长与首帧姿态，第 3 步装配与第 8.7 步拼接之前先做完这一步。族名对照表随素材来源而异，工程内没有对照表时按目录归属判断。

<!-- WUWA:BEGIN -->
鸣潮素材的族名对照表、目录分布与 `Stand1_ActionNN` 的归属见 `references/wuwa-notes.md` 第三节，选片段之前先读它。
<!-- WUWA:END -->

## 六、主从协作契约（多会话或子代理时）

- 子代理只做取证与资产改动，不 cook、不部署、不启动游戏；构建由主会话串行执行。
- 同一文件禁止两个子代理并行修改；并行构建会互覆日志。
- 子代理提示词必须含：工作目录、只读与可写边界、中间产物只写 `workspace/tmp`、报告写 `workspace/gen/reports`、结论带数字与文件出处。
- 观感类目标先向用户要口径并换算成数值判据；等回馈期间关游戏、攒批待裁决项。

## 七、部署指纹与事故应急

每次部署记录：BLP 字节数 + sha256 前 16 位 + cook 九类告警计数。cook 前把当前部署 BLP 另存 `workspace/gen/backup/` 作回退点，cook 日志另存防覆盖。伪失败码清单（不作失败判据）见 `acceptance.md` §伪失败码，坏包回退见 `gotchas.md`。

## 八、交接

跨会话移交按 `references/handover.md` 六要素模板写交接文档与可复制提示词；接手方第一动作是核对基准指纹。

头发与刘海出现同片两色、或改材质改贴图后画面不动时，按 `references/hair-shading-case.md` 的排查顺序走，先做材质归属测量再动参数。

## 九、随包内容与上游

包内自带转换工具链、转换脚本与 ACL 补丁，解压即可运行；第三方插件与 SDK 需自行获取。

| 包内路径 | 内容 | 说明 |
|---------|------|------|
| `tools/CivNexus6/` | `NexusBatch.exe`、`CivNexus6.exe`、`Na2Tool.exe`、16 个读数工具与全部依赖程序集，35 MB | 未签名，必须在 `D:\documents` 树外执行；na2 导出用 `Na2Tool.exe`，随包旧 `NexusNA2.exe` 失效，见「与社区工具链对齐」节 |
| `scripts/` | `jx_build5.py`（装配与七段动画）、`jx_r3_face.py`（面部骨架与权重）、`jx_morph_face.py`（形态键转面骨）、`jx_hair_rib.py`（RibbonAnim 叠加）、`jx_secondary.py`（发丝与衣物）、`jx_r5_bangs.py`（刘海定标）、`jx_assemble.py`、`jx_ast_normalize.py`、`jx_cook.sh` 及 `scripts/archive/` 下 142 个一次性诊断采样脚本（`jx_r3*`…`jx_r16*`、`jx13*`、`jx14*`、`jx_portrait*`、`jx_pmx*`、`jx_voice*`、`jx_wpn*`），归档约定见 `scripts/archive/README.md` | 内含工程路径常量，换项目需改；`jx_build5.py` 依赖前六个模块，缺一即导入失败 |
| `scripts/csharp/` | 读数工具与 `NexusBatch` 的 C# 源码 | 重编译用 |
| `scripts/open_model_launcher.cmd` + `scripts/_open_detached.cmd` | 两阶段自举启动器（分发模板）：入口只把执行器交给 `explorer.exe` 后退出，执行器启动 Blender 后退出，Blender 无活父进程。双击 = 默认模型，拖放 = 指定模型 | 换机器改执行器头部 `CIV6_*` 常量；本机实例在 `E:\SoftWares\civ6_nexus_work\dj_preview\`，两边逐位一致；流程与判据见 `references/open-model.md` |
| `scripts/cook_sweep.sh` | 全 XLP cook 扫描：逐条目跑官方 Cooker，把退出码与九类告警计数写进 TSV | 六个必填参数，工程路径与 pantry 根从命令行传入 |
| `scripts/`（面部与归因） | `expr_route_gate.py`（G0 曲线来源探测 + A/B 路线决策状态机，退出码 0/10/11/12）、`face_expr_runtime.py`（曲线层运行时：curve_blink 长短分层/互补混合/让位/下睑保底/限幅）、`unpack_expr_curves.sh` + `curves_json_check.py` + `curves_manifest.py`（官方曲线补导与来源指纹）、`face_skin_gate.py`（几何蒙皮 + 动画轨迹 + 装配一致 三合一闸门，`--code-map`/`--geo-pattern` 参数化定位）、`dump_tracks.py`（逐帧骨头导出与绝对 min–max 摘要）、`morph_curves.py`（官方曲线 → 逐帧权重表 + 双实现校验，`--require-source` 默认开）、`ast_bind.py`（`.ast` 四处容器引用增删/降级）、`gate_selftest.py`（反向闸门自检，默认五注入）、`_patch_template.py`（治标补丁模板） | `face_skin_gate.py` / `dump_tracks.py` 需 `--meshtable`、`--dump` 指向读数 exe；`face_skin_gate.py` 的 `--inject` 供 `gate_selftest.py` 验证区分力；表情链用法见 `references/expression-route.md` |
| `scripts/probes/` | 诊断脚本：`cn6_material_stats.py`（逐材质面数与法线）、`cn6_corner_normals.py`（反向角法线占比）、`dds_tex_verify.py`（DDS 头与 .tex 校验）、`dds_header.py`（打印与改写 `pf_flags`、`caps`）、`mask_roworder_audit.py`（掩膜行序审计：按两种行序各栅格化 UV 三角比岛内覆盖率，退出码 0=正写 / 4=翻转 / 5=判不出，`--selftest` 为反向闸门）、`alpha_bind_verdict.py`（alpha 两端占比 → 该不该绑 Opacity）、`texpair_check.py`（dds/tex 成对与类别表逐项校验）、`texture_compare.py`（源图与工程贴图比对）、`png_to_dds.py`（源 PNG 重建带 mip 的 DDS）、`open_model_in_blender.py`（**已废弃**的两步法 GUI 脚本，勿用；改走 `open_model_launcher.cmd`）、`dump_hair_uv.py`（按主导骨骼导出 UV 三角）、`hair_mask_color.py`（掩膜栅格化与按曲线调色） | `cn6_*`、`texture_compare.py`、`open_model_in_blender.py` 含工程路径常量；`texpair_check.py` 的类别表取 `references/texture-classes.json` |
| `patches/UAnimSequence.cs` | ACL 动画解码补丁 | 覆盖 CUE4Parse 同名文件后重编 `CUE4Parse-Natives.dll` <!-- WUWA --> |

| 需自行获取 | 用途 | 上游地址 |
|-----------|------|---------|
| FModel | UE 包浏览与 psk/ueanim 导出宿主 | https://github.com/4sval/FModel |
| fmodel-mcp | FModel 的 MCP 封装 | https://github.com/plu1337/fmodel-mcp |
| CUE4Parse | UE 解析库，FModel 依赖 | https://github.com/FabianFG/CUE4Parse |
| Blender 4.5 LTS | 装配、重定向、cn6 与 FBX 导出 | https://www.blender.org/download/lts/ |
| psk/psa 插件 | Blender 读写 psk 与 psa | https://github.com/DarklightGames/io_scene_psk_psa |
| UEFormat 插件 | Blender 读写 `.uemodel`/`.ueanim` | https://github.com/h4lfheart/UEFormat |
| cn6 插件 | Blender 导入导出 `.cn6` | https://forums.civfanatics.com/resources/blender-scripts-for-civ-v-and-civ-vi.25925/ |
| GR2 插件 | 读取正样本 `.gr2` | https://github.com/SWTOR-Slicers/Granny2-Plug-In-Blender-2.8x |
| Civ6 Development Tools | Asset Cooker、FgxViewer、ModBuddy、pantry | https://store.steampowered.com/app/404350/ |
| vgmstream | 解码 Wwise IMA ADPCM | https://github.com/vgmstream/vgmstream |
| .NET SDK | 编译 C# 工具与 fmodel-mcp | https://dotnet.microsoft.com/download |
| python-zstandard | UEFormat 插件依赖 | https://pypi.org/project/zstandard/ |

取得方式、部署命令与核验状态见 `references/upstream.md`。

## 十、与社区工具链对齐（E1–E7 实验结论）

动手前先定路由，判据与故障对照查 `references/gotchas.md` 顶部的「根因 → 新路径映射」，与社区工具的差异清单查 `references/community/civnexus6-fork-diff.md`（D1–D8）。实验报告在 `<方案根>/workspace/gen/reports/`。

### 路由一：贴图一律由 CivNexus6 工具生成 dds/tex 对

- 入口：`tools/CivNexus6/CivNexus6.exe` 的 `Process Texture into .dds/.tex` 与 `Process All Textures in Directory`。同一次调用写出 `.dds` 与 `.tex`，全链没有缩放操作。
- 依据（E3）：今汐 236 对贴图全部换成工具产物后，cook 退出码 0、九类告警全 0、BLP 19,474,944 字节，判据脚本由 EXIT=1（HARD 9／SOFT 670）转为 EXIT=0；工具生成的 `.tex` 其 `m_Version` 为 0.0.0.0 且根元素未声明 xmlns，cook 接受。报告 `wp2-e3-textures.md`、`wp13-e3-cook-acceptance.md`。
- 兜底：手工 `.tex` 只用于工具覆盖不到的贴图类别，改完用 `workspace/gen/tools/wp2/wp2_texpair_check.py` 类判据复核（dds/tex 成对、头部字段齐全）。
- 材质：`.ast` 只引用材质名，缺省层可以省。
- **掩膜例外**：材质 `Opacity` 槽引用的贴图不能直接用工具产物覆盖。工具生成的 DDS 头为 `pixelformat.dwFlags=0x20000`、`caps=0x401008`，与工程既有掩膜（`0x40`、`0x401007`）不一致时整块几何在引擎里消失且 cook 不报错。生成后按 `texture-pass.md` 判据二比对，不一致须改回头字段（只改头部，负载逐字节不动）。

### 路由二：动画链保留现链（Blender 4.5 FBX 加 CivNexus6 导入器）

- 依据（E2）：Nexus Buddy 2 的 `FBXImporter.ImportFBXFile` 对 Blender 4.5 FBX 与 2.49 FBX 6.1 共四种输入全部返回 False、零产物；CivNexus6 x64 的同一方法返回 True。今汐超 4 权重顶点占比 0/37013 与 0/54283，长离 280/59418＝0.4712%。报告 `wp6-e2-nb2-chain.md`。
- na2 导出用随包 `tools/CivNexus6/Na2Tool.exe`，单命令 `<模型 fgx> <动画 fgx> <输出 na2> [起始帧] [结束帧]`。随包旧 `NexusNA2.exe` 失效：`NA2_EXPORT result=3`，产物 2,584 字节、仅 7 行非空，根因是 `IGrannyAnimation.SampleBone` 抛 AccessViolationException（全骨探针退出码 139）。`Na2Tool` 与原引擎采样的 50 个 4×4 矩阵 maxdiff＝0.001102，输出 3,619,984 字节且确定性可复现；Blender 2.83 的 `io_import_na2` 只读导入可用（原版 195 骨／121 帧、今汐 223 骨）。报告 `wp1-e1-na2-baseline.md`、`wp10-e1-na2-tool-landing.md`。
- 改名与换片段只改配置：`NexusBatch.exe` 与 `MintBatch.exe` 的动画名表是与 exe 同目录的 `<exe 名>.animset.tsv`（查找点 `NexusBatch.cs:56-58`，走 `Application.ExecutablePath`），改名后 `ANIM_SKIP` 由 1 降到 0；配置写错回显 `ANIMSET_ERROR` 带行号并以退出码 2 终止。编译必须引用 `CivNexus6.exe`，引用 `NexusBuddy.dll` 会在窗体构造抛 MissingManifestResourceException。报告 `wp5-e7-fork-config.md`、`wp9-e7-fork-landing.md`。

### 路由三：ast 一律从原版领袖 ast 复制后只改绑定与时长

- 依据（E4）：`MetadataWriter.WriteGeoAnimFile(fgx,0,"Leader")` 生成 `.geo`（9,481 字节／303 行，与工程产物逐字节相同）并自动写 dummy `.wig`（106 字节）；`.anm` 由同一入口生成（34 行含 WIG 条目，`jx_assemble.py` 剥掉后 30 行）；`WriteGeometrySet` 可生成 `m_GeometrySet` XML。原版领袖 ast 的副本 1,776 行、含 29 条 timelineBinding，4 个迁移槽天然存在。工程现有 ast 缺 7 条槽的时间线两层、`m_Name` 写成 Armature。报告 `wp3-e4-geo-anm-ast.md`。
- 顺序守卫：`jx_assemble.py` → `jx_ast_normalize.py`，不可换序。

<!-- WUWA:BEGIN -->
### ACL 补丁随包携带，按版本号人工装入

- 依据（E6）：UE Viewer build 1590 无法替代（33 次导出 0 文件、ACL 命中 0、27/33 日志含 `Serializing behind stopper`）。`scripts/build_acl_patch.ps1` 只做四步：校验 `-SourceRoot` → 覆盖 `patches/UAnimSequence.cs` → `dotnet build` → 回显产物路径、字节数、sha256、FileVersion、ProductVersion；装入由人工按 ProductVersion 提交哈希比对后执行。报告 `wp4-e6-umodel.md`、`wp8-e6-acl-patch-package.md`。
<!-- WUWA:END -->

### success-case.md 里 sha256 部署指纹的适用范围

`references/success-case.md` 的 BLP 字节数与 sha256 属于产物指纹，只对同一次产物成立。同一工程连跑两次 leader 包，sha256 不同（实测差异 28 字节），所以跨次比对只认 BLP 字节数、九类告警计数与四判据结果；同一次产物内部的逐位校验（部署位与产物哈希比对）仍然成立。

全量回归证据：今汐七步重跑，四判据 7 段全 PASS，cook 两次退出码 0，九类告警除既有 `fallback=7` 外全 0，部署 BLP 19,474,944 字节、sha256 `0c4cad2dc667bb38765354af7776876d0b5d77a826fab5e329cf2dffe393b7fa`。报告 `wp14-full-regression.md`。

## 十一、贴图侧五道闸门

细节与实测读数在 `references/texture-pass.md`，这里只列执行顺序与停止条件。

| 闸门 | 内容 | 不过即停的情形 |
| --- | --- | --- |
| 一 | 基色只取 `_D`／`_D2`／`_D3` 漫反射；`_N`、`_LD`、`_M`、`_HM`、`_VC`、`_ID` 不得充当 BaseColor | 生成后读数不在“最小 80～90、均值 160～190、暗像素 5%～15%”区间 |
| 二 | 掩膜 DDS 头字段与工程既有掩膜一致（`dwFlags` 偏移 80 为 `0x40`、`caps` 偏移 108 为 `0x401007`） | 两字段任一不符，或 `dds_tex_verify.py` 未跑 |
| 三 | 局部调色先按主导骨骼导出 UV 三角、栅格化成掩膜，再与颜色判据相交；掩膜预览里不得出现图集空白区、发尾条带、缎带条带 | 预览不合格，或没有预览 |
| 四 | 色块与层次二选一：纯灰块走阈值替换加羽化，保留层次走平滑曲线压缩（`L' = 均值 + k × (L − 均值)`） | 曲线或阈值未写进报告 |
| 五 | 出图尺寸随源图自适应（默认 2048²），`TARGET_SIZE` / DDS 头 / `.tex` 三处一致；`Leader_BaseColor` 上限 4096²、2048² 为合法默认档位；贴图改完先跑 `open_model.py` 预览，末行 `OPEN_MODEL_OK` 才 cook | 三处不一致，或预览未过 |

今汐定稿的实测值（作为读数参照；1024² 是当时的出图档位，非规格，现按判据五自适应）：头发基色 `Hair_D` 1024²，漫反射读数最小 83／均值 167.8／暗像素 8.70%；定稿后最小 84／均值 186.5／暗像素 4.65%；十二段骨骼栅格化共 7,726 个三角，垂发侧掩膜覆盖 27.35%；曲线系数 `0.22`。

<!-- WUWA:BEGIN -->
## 十二、鸣潮专用补充

解包链路、骨架与骨名、片段语义、二次运动层、贴图后缀、单位侧口径、解包完整性边界全部归在 `references/wuwa-notes.md`。本机全部案例来自鸣潮素材，分享版删除该文件与本节的标记块，其余章节自洽。

新增鸣潮相关内容一律写进 `references/wuwa-notes.md`。确需写在主文件的，必须带 `<!-- WUWA -->` 行尾标记或 `<!-- WUWA:BEGIN -->` 块标记；`scripts/pack_share.py` 的泄露扫描会对未标记的残留以退出码 2 终止。

生成分享版：

```bash
python scripts/pack_share.py --src . --out ../civ6-model-import-share
```
<!-- WUWA:END -->
