# 单位模型案例库（2026-11-01 男漂重建实录）

每条写「现象 → 处置 → 实证程度」。**实证程度为「已复现」的可以直接照做；「可能有关」的只是候选解释，以实际执行结果为准。**

## 一、已复现（有对照读数，可直接照做）

### C01 动作导出后 fgx 只有 4.5 KB、骨骼通道 0 条

- 现象：`NexusBoneCurve.exe <geo> <clip>` 报 `groups=0`，CivModelTool 导出的每条 `.fgx` 都是 4492~4504 字节。
- 原因：FBX 里动作名带 `RoverUnitRig|RoverUnitRig|` 前缀，导出器按骨架名匹配轨道，匹配不到就写空通道。
- 处置：导出前做两步，缺一不可。① `act.name = act.name.split("|")[-1]`；② `for s in act.slots: s.name_display = arm.name`。
- 判据：导出后 `NexusBoneCurve` 的 `groups=60`，`.fgx` 在 35~265 KB 之间。

### C02 动作全部错乱、模型倒置或悬空

- 现象：实机所有动作乱动，模型躺着或浮空。
- 原因（已实测）：`uf.import_ueanim` 依赖每根骨上的 `orig_loc` / `orig_quat` / `post_quat` 三个自定义属性。这三个属性只有 ueformat 自己的骨架创建会写，psk 导入的骨架没有，导入器取默认值后每根骨多叠一次 rest 旋转、多平移一次 rest 偏移。
- 处置：导入动作之前，对**接收动作的那副骨架**（源骨架，不是缩减骨架）逐骨写入：

```python
for b in full.data.bones:
    local = b.matrix_local if b.parent is None else b.parent.matrix_local.inverted() @ b.matrix_local
    loc, quat, _ = local.decompose()
    b["orig_loc"] = loc
    b["orig_quat"] = quat.conjugated()
    b["post_quat"] = quat
```

- 判据：写入后 `REST_PROPS` 等于源骨数（男漂 189）；成品 FBX 中头到髋距离落在 0.35~0.75 米。

### C03 构建脚本超时

- 现象：前台执行 Blender 构建 120 秒超时，日志为空。
- 原因：逐骨调用 `bpy.context.view_layer.update()` 太慢；前台限制 120 秒。
- 处置：改回 `matrix_basis` 反算写法（每帧不逐骨刷新），并把整个构建写进 shell 脚本用后台作业执行。
- 判据：`job_output` 收到 `BUILD_RC=0` 与 `FBX_EXPORTED`。

### C04 日志文件为空

- 现象：后台作业返回退出码 0，但重定向的日志 0 字节。
- 原因：重定向写在作业命令行里，被作业包装吞掉。
- 处置：把 `> log 2>&1` 写进 shell 脚本文件内，作业只调用 `bash <脚本>`。

### C05 插件算子找不到

- 现象：`AttributeError: Calling operator "bpy.ops.uf.import_ueanim" error, could not be found`，但日志里已打印 `BL_BOOTSTRAP_OK`。
- 原因：`bpy.ops.wm.read_factory_settings(use_empty=True)` 在 `import bl_bootstrap` 之后调用，把插件注册清掉了。
- 处置：`read_factory_settings` 必须放在 `import bl_bootstrap` 之前。

### C06 Blender 5.2.3 的 CivModelTool 找不到

- 现象：`Add-on not loaded: "CivModelTool", cause: No module named 'CivModelTool'`，随后 `AttributeError: 'Scene' object has no attribute 'CMT'`。
- 原因：插件装在 `blender-5.2.3-windows-x64/portable/scripts/addons/CivModelTool`，需要设环境变量才被扫描。
- 处置：`export BLENDER_USER_SCRIPTS="C:/Users/Administrator/.agents/skills/civ6-modeltool/tools/blender/blender-5.2.3-windows-x64/portable/scripts"`。

### C07 Blender 4.5.9 不识别 export_animations

- 现象：`TypeError: Converting py args to operator properties:: keyword "export_animations" unrecognized`。
- 原因：`export_animations` / `export_nla_strips` 是 Blender 5.2 的参数。4.5.9 要用 `bake_anim_use_nla_strips=True` 加 `bake_anim_use_all_actions=False`。

### C08 换素材后部署目录残留旧条目

- 现象：cook 与 deploy 都退出码 0，但 `SHARED_DATA` 里同时有新旧两套动画名（小写与大写混在一起）。
- 原因：cook 只写不删，旧 `ANIMATION_*` / `TEXTURE_*` 留在部署目录。
- 处置：cook 之前 `rm -f <BLPs>/SHARED_DATA/ANIMATION_* <BLPs>/SHARED_DATA/TEXTURE_*`。

### C09 AST 时间线时长全为 0

- 现象：CivModelTool 导出的 AST 里 40 条 `<m_fDuration>` 全是 `0.000000`。
- 处置：从对应 `.anm` 读实际时长回填，按 `<m_Animations>` 段内 `<m_AnimationName>` 与 `<m_fDuration>` 的配对改写。
- 判据：时间线条目数与片段数对应，时长不一致 0、零时长 0。

### C10 材质贴图核对时读不到贴图名

- 现象：按 `<m_Name>` 提取贴图名得到 0 条。
- 原因：Civ6 材质实例的贴图写在 `<m_ObjectName text="T_xxx"/>` 节点，`<m_Name>` 是材质自身名字。
- 处置：按 `m_ObjectName` 提取，并且只核对 `<m_ParamName text="BaseColor"/>` 那一条。

### C11 整体朝向差 90 度

- 现象：模型面朝方向与游戏期望不一致。
- 判据（已实测）：源模型踝→趾为 `(0.001, -0.097, -0.100)`（正面朝 `-Y`），目标朝 `+X`。
- 处置：`ROT_Z90 = Matrix.Rotation(math.radians(90.0), 4, 'Z')` 施加到骨架 `edit_bones` 与 `mesh.data`；烘焙时源骨架矩阵同步 `m = ROT_Z90 @ sb.matrix`。
- 判据：踝→趾变 `(0.097, 0.001, -0.100)`；双脚连线由 `(0.265, 0.000)` 变 `(0.000, 0.156)`。

### C12 改了静止姿态后旋转被抹掉

- 现象：加了 `ROT_Z90`，导出后朝向仍不对。
- 原因：先用未旋转的世界矩阵覆盖骨架静止姿态，把刚加的旋转覆盖掉了。
- 处置：覆盖静止姿态用的世界矩阵必须同乘 `ROT_Z90`，即 `stand_world = {n: (ROT_Z90 @ full.pose.bones[n].matrix) for n in KEEP}`，且这一段必须放在 `ROT_Z90` 施加到 reduced 之后。

## 二、可能有关（只是候选解释，以实际执行结果为准）

### P01 几何 Root 四元数与女漂不同

- 现象：男漂几何 Root 为 `(0.5,0.5,0.5,0.5)`，女漂为 `(0,0.7071,0.7071,0)`。
- 已实测：CivModelTool 的 `getTranslationOrientation`（`cmt_exporter/io_export_cn6.py:8`）对两个源骨架（`Root.matrix_local` 都是单位四元数）都算出 `(0.5,0.5,0.5,0.5)`。导出公式 `out = transpose(Z90 @ cn6_perm(M))` 的矩阵奇异，`numpy.linalg.solve` 报 `Singular matrix`；精确反解出的输入行列式为 −1（含镜像），四元数无法表达。
- 净旋转判据（片段 Root 与几何静止 Root 的四元数商）男漂 27 条最大偏差 0.000006 度、女漂 23 条 0.000009 度，两侧同一量级。
- **结论**：该差异是否影响实机表现，尚未实机对照验证。现阶段的处置是「净旋转为零即可」，不要为此去改骨架 Root。
- 两次尝试均失败并已撤回：整体预乘 `Rz(±90)` 导致包围盒宽深互换；只旋转 `Root` 的 `edit_bone` 导致导出 Root 变成 `(0,0,0.7071,0.7071)` 且 `Bip001` 的局部位置与朝向被带歪。

### P02 成品 FBX 中骨长偏差 0.2%~27.7%

- 现象：`REACT_RANGED_D` 的 `Bip001-Bip001Head` 长度相对静止姿态偏差 27.69%，`DEATH_A` 13.43%，多数片段 0.2%~1.3%。
- 已实测：源骨架接受 ueanim 后骨长偏差女漂 `Stand2` 为 99.01%、男漂 `AM_Behit_Push_Start` 为 99.28%，两侧一致，说明这是该导入器的固有表现。
- 未证：女漂成品已无 FBX 留痕，无法用同一方法对照，因此**不能据此判定男漂有问题**。
- **结论**：骨长偏差在当前链路上不是有效判据，不要拿它当闸门。

### P03 NexusPoseDump 的世界坐标出现哨兵值

- 现象：男漂 `Bip001` 的世界位置显示 `-107374900` 或 `-30351100000`，女漂不显示。
- 已实测：按同一四元数公式独立复算两份产物，都得到有限世界坐标（女漂 `(-0.8366, 0, 86.2520)`、男漂 `(0, 1.0164, 85.3512)`）。
- **结论**：可能是转储工具对该骨骼的处理行为，不是产物缺陷。核对世界坐标时优先自己按四元数复算。

### P04 Bip001Head 位移通道是 −2.4e11

- 现象：`NexusCurveDump` 读出的 `Bip001Head` `pos(0)` 为 `-241106700000`。
- 已实测：女漂正常批次同样存在该读数。
- **结论**：可能是导出器对零位移写的哨兵值，不要据此判断片段异常。

### P05 默认站姿与源模型 A 字姿态

- 现象：源 psk 的静止姿态是 A 字（双臂外展约 45 度），不是游戏默认站姿。
- 已实测：解包 `Stand2.ueanim` 首帧的肩到腕为 `(0.077, 0.011, -0.400)` 与 `(-0.041, -0.039, -0.411)`，横向偏移显著小于 A 字的 0.238 米。
- **结论**：改用 `Stand2` 首帧作骨架静止姿态是候选做法，但该改动在 2026-11-01 被用户判定为超出当次授权范围而回退，**未经过实机验收**。要做这条改动时按第八节单独开任务。

## 三、判据速查

| 判据 | 阈值 | 说明 |
|---|---|---|
| `check_clip_anchors.py` | `fail=0`、退出码 0 | 只判 Root 一致性，不判绝对朝向 |
| 净旋转偏差 | < 0.001 度 | 片段 Root 与几何静止 Root 的四元数商 |
| 头到髋距离 | 0.35~0.75 米 | FBX 逐动作逐帧 |
| 髋高 | 0.80~0.90 米 | 静止姿态 |
| 踝→趾 | 指向 +X | 朝向判据 |
| AST 时间线时长 | 与 `.anm` 一致 | 不一致数 0、零时长 0 |
| 材质 BaseColor 贴图 | 缺失 0 | 按 `m_ObjectName` 提取 |
| `SHARED_DATA` 条目 | 与片段数 + 贴图数吻合 | 部署后 |
| `resample_audit.py` | `dupes=0`、步长集合 `[1]` | 输出帧数不得大于源帧区间跨度 |
| `patch_shape_rebuild.py` | 拟合残差 < 0.01 厘米、漂移 < `--tol`、权重继承数 = 新建顶点数 | 贴片按轮廓重建 |
| `shared_data_conflict.py` | 同名异内容为 0 | 两个 mod 同时装载 |
| `alpha_rgb_audit.py` | 退出码 0 | 全透明像素 RGB 全为 0 |

## 四、脚本化后消除的坑

下列各条在 `scripts/unit/` 的九个脚本里已经内建处理，直接调用脚本不必再踩。

| 原坑 | 脚本内建做法 |
|---|---|
| 附属骨靠手写清单，换角色就少骨或多骨 | `unit_build.py` 的 `--extras` 与 `--extra-prefix` 组合补足到 `--target-bones`，数量不符直接报错并给出还差几根 |
| 权重有顶点未归一化 | 逐顶点断言权重和大于 0，为 0 直接退出并点名顶点号 |
| 删骨后父引用悬空 | 保留骨的父级一律向上找到最近的保留骨重建 |
| 动作名带骨架前缀导致 0 通道 | `unit_export.py` 自动按 `|` 切分取末段并改 `slot.name_display` |
| 槽位表写死在脚本里 | `--slot` 由调用方给，AST 里未赋值的槽位会列出来 |
| 贴图按固定后缀找不到 | `find_texture` 依次尝试五种基名候选与五种扩展名，并可被 `--tex` 覆盖 |
| AST 时长全为 0 | `unit_ast_audit.py --fill --write` 按 `.anm` 回填 |
| 自动挑错 AST（挑到 VFX 的） | 按类名与时线条数挑，不看文件名 |
| AST 值读取失败 | Civ6 AST 的取值写在 `text` 属性上，`text_of()` 统一处理 |
| ElementTree 整体重写破坏格式 | 结构判定用 ElementTree，写盘用文本层替换 |
| 净旋转要手算 | `unit_geo_audit.py` 一次跑完 27 条并给出最大值与所在片段 |
| 重采样后逐帧看画面找抖动 | `resample_audit.py` 按源帧区间与输出帧数算出重复帧数与步长集合，不打开 Blender |
| 贴片重建后错位、悬空、脱离骨骼 | `patch_shape_rebuild.py` 内建拟合残差、质心漂移、权重继承数三条断言，任一不满足即退出码非零 |
| 两个 mod 同时装后动作不触发 | `shared_data_conflict.py` 比对部署目录，区分同名同内容与同名异内容 |
| 透明区残留底色导致毛边 | `alpha_rgb_audit.py` 统计全透明像素里带颜色的个数 |
