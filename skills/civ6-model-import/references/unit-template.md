# 单位模型导入模板（鸣潮解包素材 → 文明6 Unit 资产）

本模板是 2026-11-01 男漂（UnitRover）重建的完整实录，走 CivModelTool 链（与领袖的 cn6 / NexusBatch 链不同）。所有单位模型任务默认路由到这里；只在模板明确不通时再回落到领袖十步流程。

来源工程：`D:/documents/Firaxis ModBuddy/Civilization VI/UnitRover/UnitRover`
对照工程（实机验收通过）：`D:/documents/Firaxis ModBuddy/Civilization VI/UnitRoverFemale/UnitRoverFemale`

## 一、与领袖链的差异

| 项 | 领袖（Jinzhou_Jinhsi） | 单位（UnitRover） |
|---|---|---|
| 模型转换 | cn6，Blender 2.83 导出 + NexusBatch `ImportCN6` | 无 cn6，直接 psk 导入 Blender 4.5.9 |
| 动画转换 | FBX + NexusBatch `ExportGeometry` + 手工标定 Q/p_Q | FBX + CivModelTool（Blender 5.2.3）一步导出 |
| 导出器 | NexusBatch | CivModelTool 的 `cmt.exporter_ot_export` |
| 包内容 | 模型 + 贴图同包 | 包只装 AST 与几何，曲线落 `SHARED_DATA` |
| 骨骼上限 | 无硬限（实测 222） | 60（`potential_any_graph` 与 Unit 类） |

## 二、十步流程

| 步 | 动作 | 判据 |
|---|---|---|
| 1 | 素材取证：pskx/psk 的骨数、顶点数、面数、材质段 | 读数与源文件一致 |
| 2 | psk 导入 Blender 4.5.9（`bpy.ops.import_scene.psk`） | 1 骨架 + 1 网格 |
| 3 | `Matrix.Scale(0.01, 4)` 施加到骨架数据与网格数据 | 包围盒高度 1.5~1.7 米 |
| 4 | 权重重定向：每根骨映射到最近保留骨，按顶点归一化 | 每顶点权重和 = 1，零权顶点 0 |
| 5 | Decimate COLLAPSE，ratio 0.28，`use_collapse_triangulate=True` | 面数约为原始 28% |
| 6 | 复制骨架、删到 60 根、重建父子链（跨过的中间骨跳过） | `REDUCED_BONES 60` |
| 7 | 整体绕 Z 轴逆时针 90 度（见第五节） | 踝→趾由 −Y 转为 +X |
| 8 | 写 `orig_loc`/`orig_quat`/`post_quat` 到源骨架全部骨骼，30fps | `REST_PROPS` = 源骨数 |
| 9 | 逐动作 `uf.import_ueanim` → 逐帧烘焙 `matrix_basis` → 27 条 NLA 轨道 | `NLA_TRACKS 27` |
| 10 | 导出前清空 active action 并复位 pose → FBX → CivModelTool → AST 回填 → cook → 部署 | 见第六节 |

## 三、工具链固定值

| 用途 | 路径 |
|---|---|
| Blender 4.5.9（装配、烘焙、FBX） | `E:/SoftWares/blender45/blender-4.5.9-windows-x64/blender.exe` |
| 4.5.9 资源根 | `BLENDER_USER_RESOURCES=E:/SoftWares/blender45/userres` |
| Blender 5.2.3（CivModelTool 导出） | `C:/Users/Administrator/.agents/skills/civ6-modeltool/tools/blender/blender-5.2.3-windows-x64/blender.exe` |
| 5.2.3 插件根 | `BLENDER_USER_SCRIPTS=<同目录>/portable/scripts` |
| ueformat / psk_psa | `D:/documents/Firaxis ModBuddy/Civilization VI/Jinzhou_Jinhsi/workspace/_tools/blscripts/addons` |
| 引导脚本 | 同上的上一级 `bl_bootstrap.py` |

引导顺序（顺序错了插件算子不存在）：

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)   # 必须在 bootstrap 之前
sys.path.insert(0, r"D:\\documents\\Firaxis ModBuddy\\Civilization VI\\Jinzhou_Jinhsi\\workspace\\_tools")
import bl_bootstrap                                 # 打印 BL_BOOTSTRAP_OK
```

## 四、60 根骨骼清单

42 根核心骨：

```
Root Bip001 Bip001Pelvis Bip001Spine Bip001Spine1 Bip001Spine2 Bip001Neck Bip001Head
Bip001LClavicle Bip001LUpperArm Bip001LForearm Bip001LHand
Bip001RClavicle Bip001RUpperArm Bip001RForearm Bip001RHand
Bip001LThigh Bip001LCalf Bip001LFoot Bip001LToe0
Bip001RThigh Bip001RCalf Bip001RFoot Bip001RToe0
Bip001LForeTwist Bip001LForeTwist1 Bip001RForeTwist Bip001RForeTwist1
Bip001LUpArmTwist Bip001LUpArmTwist1 Bip001LUpArmTwist2
Bip001RUpArmTwist Bip001RUpArmTwist1 Bip001RUpArmTwist2
Bip001LThighTwist Bip001LThighTwist1 Bip001RThighTwist Bip001RThighTwist1
Bip001_L_Calf Bip001_L_CalfTwist Bip001_R_Calf Bip001_R_CalfTwist
```

18 根附属骨（按角色替换，占满 60）：男漂为 12 根头发 `Bone_Hair*` 加 6 根飘带 `Piao_*`；女漂为 `skirt_*`、`skrit_*`、`Piao_F01/F02`、`R_ChestBone01`、`L_ChestBone01`、`Hair_*`。

删骨时父子链必须重建：原父骨若不在保留集内，向上找到最近的保留骨作为新父。否则 Blender 会保留已删除的父引用，导出时骨骼错位。

## 五、朝向修正（关键参数）

源模型正面朝 `-Y`，游戏期望 `+X`，因此整体绕 Z 轴逆时针旋转 90 度：

```python
ROT_Z90 = Matrix.Rotation(math.radians(90.0), 4, 'Z')
for eb_ in reduced.data.edit_bones:
    eb_.matrix = ROT_Z90 @ eb_.matrix
mesh.data.transform(ROT_Z90)
```

烘焙必须同步补偿，否则动作会把旋转抵消：

```python
m = ROT_Z90 @ sb.matrix      # sb 是源骨架的 pose bone
```

判据：踝→趾由 `(0.001, -0.097, -0.100)` 变为 `(0.097, 0.001, -0.100)`；双脚连线由 `(0.265, 0.000)` 变为 `(0.000, 0.156)`。

## 六、判据与命令

### 闸门

```bash
python C:/Users/Administrator/.agents/skills/civ6-model-import/scripts/check_clip_anchors.py "UnitRover" --tmp workspace/tmp/anchors
```

要求 `clips=27 fail=0`、退出码 0。该闸门只比对同工程内片段与几何的 Root 一致性，不能判断绝对朝向，绝对朝向必须靠第五节的踝→趾判据。

### 净旋转判据

片段 Root 与几何静止 Root 的四元数商应为单位四元数。男漂 27 条最大偏差 0.000006 度、女漂 23 条最大偏差 0.000009 度。脚本样例见 `workspace/tmp/malebuild/net_rot.py`。

### 站立朝向判据（切动作时模型转向）

现象：跑停后切待机、攻击收尾后切待机，模型原地转向一个小角度。根因是各片段首帧的髋线朝向不同，引擎按片段播放，衔接瞬间把朝向差暴露出来。

髋线朝向定义为左右大腿骨世界位置连线的法向角：

```python
yaw = math.degrees(math.atan2(-(rh.x - lh.x), rh.y - lh.y))
```

修正必须在烘焙阶段写入 `Bip001` 的 `rotation_quaternion` 曲线，`Root` 曲线保持单位四元数：

```python
rest_bip = reduced.data.bones["Bip001"].matrix_local.to_quaternion()
rot = Matrix.Rotation(math.radians(delta), 4, 'Z')
conj = (rest_bip.to_matrix().to_4x4().inverted() @ rot @ rest_bip.to_matrix().to_4x4()).to_quaternion()
# 逐帧读四通道 keyframe 值组成四元数，左乘 conj 后写回
```

把偏转写在 `Root` 上会被引擎当成真实转身，衔接时反而偏得更厉害（女漂第一版 +37.441° 就是这样失败的）。

基准取停止片段末帧而不是跑步首帧：切回待机发生在跑停播完之后。要一起转的是全部站立类片段的首帧 —— `IDLE_A`、`IDLE_B`、`IDLE_C`、`IDLE_D`、`IDLE_COMBAT_A`、`IDLE_COMBAT_C`，以及收尾回到站立姿态的 `ATTACK_A`（按末帧算）。男漂实测：`IDLE_A` 与 `ATTACK_A` 需要 306.92°、两条战斗待机需要 10.331°、`IDLE_B` 到 `IDLE_D` 本来就是基准值。

`TURN_L` / `TURN_R` 不参与：源素材的 `Root` 自带正负 90 度旋转，末帧髋线分别是 −108.950° 与 71.049°，这是转身动作的正常收尾。

校验用 `scripts/unit/unit_yaw_audit.py`，在导出的 FBX 上跑：

```bash
BLENDER_USER_RESOURCES=E:/SoftWares/blender45/userres \
  E:/SoftWares/blender45/blender-4.5.9-windows-x64/blender.exe -b --factory-startup \
  --python C:/Users/Administrator/.agents/skills/civ6-model-import/scripts/unit/unit_yaw_audit.py \
  -- --fbx <RoverUnit.fbx> --json workspace/tmp/unit_yaw.json
```

它对每条片段逐帧读髋线角度并解缠成累计路径，输出 `first` / `path` / `last`；判定是全部 `IDLE*` 首帧与 `RUN_STOP` 末帧的夹角不超过 `--tolerance`（默认 1 度），末行 `UNIT_YAW_AUDIT_OK fail=0` 且退出码 0。男漂定稿读数：六条待机首帧 161.049 到 161.051，与 `RUN_STOP` 末帧 161.051 差 0.000 到 0.002 度；`TURN_L` 路径累计 +90.000、`TURN_R` −90.001。

`check_clip_anchors.py` 判不了这一项：它只比对同工程内片段与几何的 `Root` 一致性，而朝向修正写在 `Bip001`，`Root` 前后都是单位四元数。改完必须在 FBX 上另跑本判据。

### AST 审计

- `m_dsgName` = `potential_any_graph`
- `animationBindings` 与 `m_timelines` 条数相同（男漂 40 / 40）
- `m_Animations` 条数 = 实际片段数（男漂 27）
- 每条时间线的 `<m_fDuration>` 必须与对应 `.anm` 的实际时长一致，零时长 0
- `<m_AnimationName>` 引用必须都有对应 `.fgx`

CivModelTool 导出的 AST 时间线时长默认为 0，必须回填。

### 材质审计

材质贴图记录在 `<m_ObjectName text="T_xxx"/>` 节点（不是 `<m_Name>`），且只绑 `BaseColor` 一个槽。核对时按 `m_ObjectName` 提取。

### cook 与部署

```bash
python C:/Users/Administrator/.agents/skills/civ6-modding/tools/cook_assets.py "<工程根>" --quiet
python C:/Users/Administrator/.agents/skills/civ6-modding/tools/modinfo_build.py --deploy --no-cook "<工程根>/<工程名>.civ6proj"
```

部署后核对：`SHARED_DATA` 条目数、`ANIMATION_<前缀>*` 条数、贴图条数与命名前缀、`units/<包名>.blp` 字节数与 sha256。

cook 之前先清空部署目录 `BLPs/SHARED_DATA` 下的旧 `ANIMATION_*` 与 `TEXTURE_*`，否则换素材后旧条目会残留。

## 七、CivModelTool 导出要点

```python
data = bpy.context.scene.CMT.ExporterSettings
data.ProjectPath = PROJECT
data.UVCount = 1
data.IsExportModel = True
data.IsExportAnimation = True
data.IsGenerateRef = True
data.IsExportAst = True
data.IsExportMaterial = True
data.IsExportArtdef = False
data.OverwriteTextures = True
geo = data.GeoList.add();  geo.FileName = "RoverUnit"; geo.Class = "Unit"
ast = data.AstList.add();  ast.FileName = "RoverUnit"; ast.Class = "Unit"; ast.DSG = "potential_any_graph"
bpy.ops.cmt.exporter_ot_automatchtextures()
bpy.ops.cmt.exporter_ot_export()
```

动作改名两条都是必需的，少一条就导出 0 通道：

1. 去掉 `RoverUnitRig|RoverUnitRig|` 前缀
2. 把 `act.slots` 的 `name_display` 改成骨架对象名

## 八、长流程执行方式

Blender 构建与导出都会超过前台 120 秒限制，必须写成 shell 脚本用后台作业跑，再用 `job_output` 收结果：

```bash
# run_build.sh
export BLENDER_USER_RESOURCES='E:/SoftWares/blender45/userres'
E:/SoftWares/blender45/blender-4.5.9-windows-x64/blender.exe -b --factory-startup \
  --python workspace/tmp/build/build_male.py > workspace/tmp/build/build.log 2>&1
echo "BUILD_RC=$?"
grep -aE "REDUCED_BONES|ROT_Z90_DONE|NLA_TRACKS|FBX_EXPORTED" workspace/tmp/build/build.log | tail -5
```

日志重定向在后台作业里必须写在脚本内，直接写在作业命令行里会得到空文件。

## 九、随包脚本（参数化，通用）

四个脚本在 `scripts/unit/`，全部走命令行参数，不假设文件名前缀、不假设固定槽位名、不假设贴图命名。

### unit_build.py — 构建与烘焙

```bash
E:/SoftWares/blender45/blender-4.5.9-windows-x64/blender.exe -b --factory-startup \
  --python <skill>/scripts/unit/unit_build.py -- \
  --psk "<源模型.psk|.pskx>" --out "<输出目录>" \
  --rig-name UnitRig --mesh-name UnitBody \
  --scale 0.01 --decimate 0.28 --target-bones 60 --rot-z 90 --fps 30 \
  --extras "<骨名>,<骨名>,..." \
  --extra-prefix "Piao_" --extra-prefix "Hair_" \
  --anim IDLE_A="<Stand2.ueanim>" --anim ATTACK_A="<AM_Attack01.ueanim>"
```

| 参数 | 说明 |
|---|---|
| `--psk` `--out` | 必填 |
| `--target-bones` | 保留骨上限，默认 60 |
| `--rot-z` | 整体绕 Z 轴旋转角度，默认 90；给 0 即不旋转 |
| `--extras` | 显式附属骨清单，逗号分隔 |
| `--extra-prefix` | 按前缀自动补足到 `--target-bones`，可多次；与 `--extras` 配合 |
| `--rest-action` | 用某段动画首帧作骨架静止姿态（可选，未实机验收） |
| `--anim` | `槽位名=动画文件路径`，可多次；槽位名即 AST 槽位名 |

核心骨 42 根内置，缺任何一根直接报错退出，不静默降级。附属骨数量不足或超限都报错，并指出还差几根。

### unit_export.py — CivModelTool 导出

```bash
export BLENDER_USER_SCRIPTS="<blender-5.2.3>/portable/scripts"
<blender-5.2.3>/blender.exe -b --factory-startup \
  --python <skill>/scripts/unit/unit_export.py -- \
  --fbx "<构建产物.fbx>" --project "<工程根>" \
  --asset Unit --rig-name UnitRig --mesh-name UnitBody \
  --tex-dir "<贴图目录>" --tex "材质名=贴图路径" \
  --slot IDLE_A=IDLE_A --slot ATTACK_A=ATTACK_A
```

贴图查找顺序（不需要改脚本）：先查 `--tex` 显式映射；未命中时在 `--tex-dir` 下依次尝试 `<基名>_D`、`T_<基名>_D`、`<材质名>_D`、`<基名>`、`T_<基名>`，扩展名依次 `.png .dds .tga .tif .jpg`。基名由材质名剥掉 `MI_`/`M_`/`MAT_` 前缀与 `_Mat`/`_Inst`/`_MAT` 后缀得到。

槽位名由 `--slot` 给出，脚本不内置任何槽位表；AST 里未赋值的槽位会列出来，便于核对是否漏配。

### unit_ast_audit.py — AST 审计与时长回填

```bash
python <skill>/scripts/unit/unit_ast_audit.py "<工程根>" --fill --write
```

不给 `--ast` 时按内容自动挑选：优先类名为 `Unit` 且时间线条数最多的 .ast，不看文件名、大小写与前后缀。需要显式指定时用 `--ast`。

判定项：DSG、animationBindings 条数与空绑定数、timelines 条数、引用不存在的片段、时长不一致、零时长。全部通过退出码 0。

`--fill --write` 把时间线时长按 `.anm` 实际值回填。回填用文本层替换，不用 ElementTree 整体重写（后者会把 XML 声明改成单引号并让文件膨胀）；结构判定用 ElementTree 读。

### unit_geo_audit.py — 几何与片段一致性

```bash
python <skill>/scripts/unit/unit_geo_audit.py "<工程根>" --pairs "A-B,A-B"
```

判据：片段 Root 与几何静止 Root 的四元数商应该是单位四元数，阈值 0.001 度；同时打印静止骨长表便于对照。默认 8 对核心骨链，`--pairs` 可追加。

### unit_yaw_audit.py — 站立朝向

```bash
BLENDER_USER_RESOURCES=E:/SoftWares/blender45/userres \
  <blender-4.5.9>/blender.exe -b --factory-startup \
  --python <skill>/scripts/unit/unit_yaw_audit.py -- \
  --fbx "<构建产物.fbx>" --json workspace/tmp/unit_yaw.json
```

对每条片段逐帧读髋线角度并解缠成累计路径，输出 `first` / `path` / `last`。判定是全部 `IDLE*` 首帧与停止片段末帧的夹角不超过 `--tolerance`（默认 1 度）；`--stance` 与 `--stop` 可改匹配串。末行 `UNIT_YAW_AUDIT_OK fail=0`、退出码 0 才算过。

该方法只在 FBX 上成立。用 `NexusCurveDump.exe` 走 fgx 静态反推会错：曲线里缺 key 的骨（例如某条待机的 `Bip001` 全零）会被误当成单位四元数，算出的朝向与真实播放差十几度。

### 已验证读数（男漂实测，作为参照）

| 项 | 值 |
|---|---|
| `unit_build.py` | `IMPORT bones=189 verts=39288` → `KEEP_BONES 60` → `DECIMATE verts=14230 polys=16505` → `ROT_Z_DONE deg=90.0` → `NLA_TRACKS` → `UNIT_BUILD_OK` |
| `unit_export.py` | `SLOTS_ASSIGNED` 与 `--slot` 数量一致、`EXPORT_DONE`、`UNIT_EXPORT_OK` |
| `unit_ast_audit.py` | `DSG potential_any_graph`、`BINDINGS 40`、`TIMELINES 40`、三项异常全 0、`AST_AUDIT_OK` |
| `unit_geo_audit.py` | `NET_ROT_MAX 0.000006 deg`、`UNIT_GEO_AUDIT_OK` |
| `unit_yaw_audit.py` | 六条待机首帧 161.049 到 161.051、`RUN_STOP` 末帧 161.051、`TURN_L` 路径 +90.000、`TURN_R` −90.001、`UNIT_YAW_AUDIT_OK fail=0` |
