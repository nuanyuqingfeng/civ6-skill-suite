# 成功案例：今汐领袖 3D 模型导入（完整参数与实测值）

## 一、案例结果

输入为鸣潮角色 R2T1JinxiMd10011 的 psk 网格与 ueanim 动画，输出为文明6 领袖 JINZ_Jinhsi 的 3D 模型。实机确认项：模型尺寸与站姿、正面朝向相机、待机动画循环、首次见面动画、口型、眨眼、待机插入动作。

## 二、定稿参数

| 项 | 值 | 说明 |
|----|----|------|
| 模型链 | cn6：`bpy.ops.export_shape.cn6` → NexusBatch `ImportCN6` | rest 与 bind 零换算直搬 |
| 动画链 | FBX：`ExportGeometry(input, outputDir, nodeName, fgxName)` | 四参数入口 |
| 朝向 δ | −90.000° | `δ = atan2(D[1][0]−D[0][1], D[0][0]+D[1][1])`，骨架绕 Z 施加 −δ，网格随转 |
| 动画骨架缩放 | `arm_c.scale=(0.01,0.01,0.01)` | 抵消 FBX 导入器写入的 diag(100,100,100)；修前修后顶点跨度差 100.00 倍 |
| 烘焙微旋 | EPS = 0.01° | 每帧叠加，避开 identity 通道被右乘 R_z(180°) |
| 帧率 | 30 fps | 动画与口型包络同一时基 |
| ueanim 平移 | 通道值 ×100 | 米换算厘米 |
| 尺寸定标 | 顶点 Z 跨度 142.920±0.01 cm | 与正样本达妮娅同高 |
| 材质 | Leader_Matte 类，BaseColor 与 Opacity 成对 | 实心部位 Opacity 留空串；切孔布料用保留 alpha 的二值贴图 |

改尺寸时：骨架与网格同缩放，`ANIM_SCALE = 100 × MODEL_SCALE`，动画同批重烘，刘海等二次定标项联动重算。

## 三、采信判据的实测值（前四条；第 5 条「片段根骨朝向对静止姿态」为单位类专属，本案例未跑）

| # | 判据 | 阈值 | 今汐实测 | 正样本（达妮娅）实测 |
|---|------|------|---------|---------------------|
| 1 | 顶点包围盒对骨架包围盒 | 上轴相同、量级同为 10²、中心距 ≤ 身高 20% | 通过 | 上轴 Z、量级 2.16/2.20、中心距 7.787（限 31.572） |
| 2 | InvBind 与 restWorld_rot⁻¹ 夹角 | ≤ 1° | 0.0396° | 0.0396° |
| 3 | 第 0 根 ScaleShear | 最大元素偏差 ≤ 0.05 | 单位阵 | 单位阵 |
| 4 | Root 通道与模型 rest 夹角 | ≤ 1° | 七段最大 0.0280° | 0.0280° |

## 四、Q/p_Q 标定（动画链核心）

- 曲线路径实测映射：`out_p = Q·in_p + p_Q`，`out_q = Q ⊗ in_q`。
- 通道旋转为 identity (1,0,0,0) 时，输出被额外右乘 R_z(180°)，204/204 骨命中。
- Q 是该骨架在动画侧 fgx 的静态基准，与模型 rest 夹角 mean 49.80°；把模型 rest 当 Q 使用是动画挂载后模型散架的成因。
- 反解烘焙：`in_q = Q⁻¹ ⊗ T_q ⊗ EPS`（残差中位 0.0115°），`in_p = Q⁻¹(T_p − p_Q)`。
- 标定表落 `anim_channel_map.tsv`，逐骨记录；换骨架或改导出参数后重标，表只允许追加。

## 五、管线命令序列

1. 清空 staging 的 `fgx/geo/anm/wig` 与 `<转换宿主>` 下全部旧 `.cn6`。
2. Blender 装配与导出：`jx_build5.py` 负责单骨架场景、骨架零变换、ueanim ×100、朝向修正、cn6 与 FBX 双导出。
3. 转换：NexusBatch 走 `ImportCN6`（模型）与 `ExportGeometry`（动画），判定看 `MODEL_DONE`/`ANIM_DONE`/`CONVERT_DONE` 回显。
4. 入工程：`jx_assemble.py` → `jx_ast_normalize.py`，顺序固定；ast 槽位与正样本一致，时长取 `.anm` 实际值。
5. cook：`Civ6AssetCooker_FinalRelease.exe --absolute_paths --no_mt --platform Windows`，五个 `--pantry` 根，`--mode XLP`，目标 `XLPs/leader_jinhsi_qyqxp.xlp`。
6. 部署：BLP 复制到 `<Mods>/<Mod>/Platforms/Windows/BLPs/leaders/`，两侧 sha256 逐位一致。
7. 实机：`gamectl.py kill → launch → wait --want inmenu --timeout 150 → host-game → load`，BLP 不热重载。

## 六、cook 与部署判据

| 项 | 期望 |
|----|------|
| 退出码 | 0 |
| 末行 | `XLP cook completed with success.` |
| 九类告警 | `grep -ic` 逐项 0（missing file / wrong extension / is not allowed here / class / Replacing asset / error asset / fallback / I/O error / ERRORS） |
| BLP 体积 | 领袖包 14–21 十进制 MB |
| 部署一致性 | 部署位与 cook 产物 sha256 逐位相同 |
| 部署指纹 | 每次记录字节数 + sha256 前 16 位 + 九类告警计数 |
| 2026-10-30 指纹 | 18,427,392 字节、sha256 前 16 位 `754cfb959057cb10`、九类告警全 0（`BUILD_EXIT=0`、`ERRORS=0`） |

## 七、表情、口型与待机动作（第四轮验证）

- 语音包络：vgmstream 解码 bank 内 Wwise IMA ADPCM 到 PCM，按 30 fps 逐帧 RMS，与原始 wav 相关 0.99999 以上。
- 六段语音的 SOUND 触发点在 `.ast` 的 `m_fStartTime`，第 16 帧约 0.5 s。
- 口型驱动：`JX_Jaw` 权重沿嘴宽余弦衰减；权重必须写进 `JX_Jaw` 本体，写在唇骨上会被 `JX_Jaw` 的全 1.0 覆盖。
- 四档量化加短语内微张；包络按语音实际时长铺满，禁止固定帧数。
- 语音长于动画时保持结束姿态继续口型。
- 眨眼：上睑整体下移，行程按眼球竖直跨度定（实测 2.06 cm）；闭眼时下睑参与，行程为上睑的 40%。
- 待机插入动作：待机循环 1133 帧（30 fps，37.767 秒），插入 `Stand1_Action01` 第 80…380 帧。进入过渡 56 帧以插入段的进入段为载体、叠加衰减到零的局部修正，落在插入段第 79 帧（下一帧正是第 80 帧）；退出过渡 57 帧用两端切线的三次 Hermite，落在待机第 1 帧；末段待机取第 2…240 帧共 239 帧。接缝 536→537 的逐骨步长：头 1.71→1.67、左手 0.90→0.80、右手 2.02→1.90 度/帧。插入动作与眨眼频率解耦。
- 面部表情：86 个形态键转成面骨通道（18 根面骨，`JX_LipLo` 无蒙皮权重，实际参与拟合 17 根）。满强度预置的逐顶点误差：Smile 均方 0.139／最大 0.882、Anger 0.056／0.599、Sad 0.053／1.221、Focus 0.038／0.856 厘米。面部通道不再顶到 1.2 厘米/帧的单帧限速。
- 待机段不叠加形态键表情层：思考姿势与惊讶由骨驱动参数给出，待机段的面部表现与拼接改动相互独立。

## 八、成功链路的判定顺序

模型链先定（cn6）→ 四条判据第一次闸门 → 朝向归位 → 动画链（FBX + Q/p_Q）→ 四条判据第二次闸门 → 入工程与 ast → cook → 部署与实机。

顺序的理由：模型 rest 与 bind 的误差会污染动画标定；朝向未定时导出的动画 fgx 与模型的空间关系不可复核；ast 与 cook 只接受已经通过离线判据的产物。四类错误在链路后段被发现时，前段全部要重跑。
