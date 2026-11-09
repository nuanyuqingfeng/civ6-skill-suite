# 管线细节与命令（civ6-model-import）

全部命令在今汐工程实机验证。路径按本机现状写死，迁移时只改盘符。

## 1. 素材解包（素材侧）

解包一律按下面的顺序尝试，前一条能用就不走后面。第 1 条与第 2 条是同一套能力（dsh-ue-asset 插件）的两种通道，第 3 条是 FModel。

### 1.1 首选：dsh-ue-asset 插件（HTTP 通道）

插件把解析进程与一套 HTTP 接口挂在 DSH Web 进程上。DSH 在跑，接口就在；本机任何 agent 用 curl 直接调，不需要凭证。

**先确认服务在监听**：

```bash
curl -s --max-time 20 'http://127.0.0.1:3080/ue-asset/api/sessions'
```

返回 `{"ok":true,"result":[...]}` 即可用。连接被拒说明 DSH Web 没启动，按 1.4 启动后重试。

**调用协议**：所有接口前缀 `http://127.0.0.1:3080/ue-asset/api`，请求体与响应体都是 JSON。响应统一包成 `{"ok":true,"result":...}` 或 `{"ok":false,"error":{"code":...,"message":...}}`。业务失败（资产不存在、参数缺失、解析报错）仍然返回 HTTP 200，成败看 `ok` 字段；只有用错方法才回 405。查询类用 GET，其余用 POST（`content-type: application/json`）。

下表是解包会用到的接口，插件另外还注册了 `/config/*`、`/tag/*`、`/asset-types`、`/index`、`/oodle/download` 等配置类接口，需要改 profile 或建检索索引时再查 `D:/documents/Deepseek_WorkPlace/dsh-ue-asset/index.js` 里 `registerRoutes` 的完整清单。

| 接口 | 方法 | 请求体字段（★ 必填） | 用途 |
|------|------|---------------------|------|
| `/sessions` | GET | 无 | 列出已挂载会话，含 mounted、fileCount、paks |
| `/open` | POST | `profile` 或 `directory`；可选 `game`、`paks`、`tags` | 挂载包体，返回 `sessionId` |
| `/close` | POST | ★ `sessionId` | 关闭会话 |
| `/tree` | POST | ★ `sessionId`；`path`、`limit`（默认 200）、`offset` | 列一层目录 |
| `/find` | POST | ★ `sessionId`；`query`、`prefix`、`ext`、`kind`、`nameOnly`、`limit`（默认 100）、`offset`、`includeNonAssets` | 按路径片段检索 |
| `/inspect` | POST | ★ `sessionId`、★ `path` | 读导出表与全部属性（骨骼、材质、NumFrame、SequenceLength） |
| `/asset` | POST | ★ `sessionId`、★ `path`；`raw` | 按资产类别出定义卡（材质参数、蓝图函数、数据表行） |
| `/preview` | POST | ★ `sessionId`、★ `path`；`maxSize`（默认 1024）、`animationPath` | 贴图转 base64 PNG；网格返回 GLB 的 `meta.modelUrl` |
| `/export` | POST | ★ `sessionId`、★ `paths`（数组） | 提交导出任务，返回 `jobId` |
| `/jobs` | GET | `?sessionId=` 可选 | 列任务 |
| `/job` | POST | ★ `jobId`；`action` 取 `status`（默认）或 `cancel`；`sessionId` 可选 | 查任务状态与产出路径 |
| `/animations` | POST | ★ `sessionId`、★ `mesh`；`prefix`、`query`、`limit` | 按网格找动画候选 |
| `/search-assets` | POST | ★ `sessionId`、★ `query`；`kind`、`limit` | 按人名或代号模糊搜（含中文别名） |
| `/paks` | POST | ★ `profile` | 列 pak 与标签 |
| `/pak-key` | POST | ★ `profile`、★ `pak`、★ `key` | 给单个 pak 绑定密钥 |
| `/pak-keys`、`/pak-key/clear` | POST | ★ `profile`（清除时另需 `pak`） | 查已绑密钥、清绑 |
| `/config` | GET | 无 | 读全局配置与全部 profile |
| `/config/games` | GET | 无 | 可选引擎版本枚举 |

静态产物走另一条前缀：`/export` 返回的 `modelUrl`（形如 `/ue-asset/cache/<hash>/.../x.glb`）拼到 `http://127.0.0.1:3080` 后面即可直接下载，响应为 `model/gltf-binary`。贴图预览返回的是 base64，要落盘请用 `/export`。

**一次完整解包**（模型 + 贴图 + 动画）：

```bash
API=http://127.0.0.1:3080/ue-asset/api

# 1) 挂载，记下 sessionId
curl -s -X POST "$API/open" -H 'content-type: application/json' -d '{"profile":"<profile>"}'

# 2) 定位资产（query 换成要找的角色代号或文件名片段）
curl -s -X POST "$API/find" -H 'content-type: application/json' \
  -d '{"sessionId":"<id>","query":"<代号>","limit":20}'

# 3) 读引擎参数写取证报告（path 用上一步返回的 path）
curl -s -X POST "$API/inspect" -H 'content-type: application/json' \
  -d '{"sessionId":"<id>","path":"<资产虚拟路径>"}'

# 4) 导出，拿到 jobId
curl -s -X POST "$API/export" -H 'content-type: application/json' \
  -d '{"sessionId":"<id>","paths":["<资产虚拟路径>"]}'

# 5) 轮询到 completed，读 result.results[].files 的落盘路径
curl -s -X POST "$API/job" -H 'content-type: application/json' \
  -d '{"action":"status","jobId":"<jobId>"}'
```

**产物格式由配置决定**，不是每次请求传参：`C:\Users\Administrator\AppData\Local\dsh-ue-asset\config.json` 的 `defaultMeshFormat` 取 `actorx` 出 `.psk`（ActorX），取 `ueformat` 出 `.uemodel`/`.ueanim`，取 `gltf` 出 `.glb`。要 psk 就先改这个键。改完直接生效，不需要重启 DSH。

`outputRoot` 是导出落盘根目录，本机为 `D:/documents/Deepseek_WorkPlace/dsh-ue-asset/out`。

<!-- WUWA:BEGIN -->
本机已配好的 profile 是 `wuwa`：105 个 pak（Content/Paks 的 55 个 + UHD 的 50 个），主密钥与 512 条动态密钥都在配置里，`/open` 返回 `mounted: 105, missing: 0`，2,305,358 个文件。密钥不出配置文件，调用方不需要也不应该传。
<!-- WUWA:END -->

<!-- WUWA:BEGIN -->
**已知缺口**：走这条通道导出的 ueanim 是空壳。`Attack01` 出 171 字节、`AM_Attack01` 出 189 字节，内容只有 `UEFORMAT`/`UEANIM` 头与空 `TRACKS`；对照 `G:\Wuwa_3D_Assets` 下已验证样本为 165,522 字节。根因是 `dist/ueasset.exe` 链接的 NuGet 原版 CUE4Parse 1.2.2.202610 不含鸣潮 ACL 回退分支，而该分支只在 `D:\ZcodeWorkPlace\fmodel-mcp\CUE4Parse\CUE4Parse\UE4\Assets\Exports\Animation\UAnimSequence.cs:326` 起的源码里。psk 与贴图不受影响。动画需要真正导出时，按 1.3 走 FModel。
<!-- WUWA:END -->


### 1.2 次选：dsh-ue-asset 插件（MCP 通道）

同一套能力走 MCP stdio。DSH 的 HTTP 通道不可用（例如只想拿独立进程、或 DSH 版本冲突导致插件没挂上）时用它。工具名与 1.1 的接口一一对应，参数名相同。

```bash
claude mcp add ue-asset -- node D:/documents/Deepseek_WorkPlace/dsh-ue-asset/mcp-server.js
codex  mcp add ue-asset -- node D:/documents/Deepseek_WorkPlace/dsh-ue-asset/mcp-server.js
```

本机当前状态：`claude mcp list` 与 `codex mcp list` 都没有这条记录，`D:/documents/Deepseek_WorkPlace/dsh-ue-asset/mcp-server.js` 尚未建立。走这一条之前先确认它存在，不存在就回 1.1。

### 1.3 兜底：FModel

前两条都不可用（DSH 装不上、或包体非 UE、或需要 FModel 独有的界面操作）时才走这里。FModel 的取得与部署见 `upstream.md`。

### 1.4 启动 DSH Web（仅本机）

1.1 的连接被拒时起一次服务：

```bash
cd /d/documents/Deepseek_WorkPlace && cmd //c Start-DSH-Web.cmd
```

它内部执行 `node C:\Users\Administrator\.dsh\profiles\node_modules\@deepseek-ai\dsh\lib\bin.js --profile web --no-open`，监听 `http://127.0.0.1:3080`。要换端口把端口作为第一个参数传进去（`Start-DSH-Web.cmd 8080`），API 前缀里的端口跟着换。

服务会常驻并占住终端。agent 调用时让它转后台：

```bash
cd /d/documents/Deepseek_WorkPlace && cmd //c Start-DSH-Web.cmd > /dev/null 2>&1 &
```

不带脚本、直接从命令行起：

```bash
node 'C:/Users/Administrator/.dsh/profiles/node_modules/@deepseek-ai/dsh/lib/bin.js' --profile web --no-open
```

服务只监听回环地址，本机 agent 可直连，跨机器不通。DSH 关闭后 HTTP 接口与解析进程一起消失，已挂载的 sessionId 全部失效，需要重新 `/open`。

**判断插件是否装进当前 profile**：`dsh-ue-asset` 必须同时出现在 profile 的两处配置里——
- `C:\Users\Administrator\.dsh\profiles\web\package.json` 的 `dependencies` 有 `"dsh-ue-asset": "link:D:/documents/Deepseek_WorkPlace/dsh-ue-asset"`
- 同文件 `dsh.profile.bundles` 数组含 `"dsh-ue-asset"`

缺任一处，服务起来也没有 `/ue-asset/api` 前缀，`/sessions` 返回 404。补装：

```bash
node 'C:/Users/Administrator/.dsh/profiles/node_modules/@deepseek-ai/dsh/lib/bin.js' \
  plugin --profile web add 'link:D:/documents/Deepseek_WorkPlace/dsh-ue-asset'
```

然后在 `package.json` 的 `dsh.profile.bundles` 里手工追加 `"dsh-ue-asset"`，重启 DSH。

### 1.5 产物组织

模型、动画、贴图按角色分目录存放，接入第 2 节的装配流程。

<!-- WUWA:BEGIN -->
本机历史产物在 `G:\Wuwa_3D_Assets\Characters\<角色>\`，新的导出可以继续放这里。
<!-- WUWA:END -->

解包的补充做法见 `wuwa-notes.md` 第一节 <!-- WUWA -->

## 2. Blender 装配（jx_build5.py 核心约定）

- 导入 psk 后场景清点：只允许 1 骨架 + 网格；多骨架（如武器 blend 附带骨架）在 join 前删除。
- 骨架对象 `scale=(1,1,1), location=(0,0,0), rotation_euler=(0,0,0)`（施加朝向修正前）。
- ueanim 通道值是 pose basis：导入 target = 通道值 ×100（米→厘米）。
- 骨架命名：nodeName、TrackGroup 名、骨架实名的 `.001` 后缀三处必须与 FBX 内实际名一致；Blender 导出剥 `.001`，缺失即静默不建轨道组（动画 groups=0 的成因）。
- 朝向修正：`δ = atan2(D[1][0]−D[0][1], D[0][0]+D[1][1])`，`D = R_目标⁻¹·R_正样本`；骨架绕 Z 施加 −δ，网格用 matrix_parent_inverse 保持世界矩阵单位阵（今汐 δ=−90.000°）。
- 模型缩放 MODEL_SCALE（改尺寸时）：骨架与网格同缩放；动画同批重烘，`ANIM_SCALE = 100 × MODEL_SCALE`；刘海等二次定标项联动重算。

## 3. 转换宿主 NexusBatch（E 盘）

- 模型：`ImportCN6`（cn6 链，rest/bind 零换算直搬）。
- 动画：FBX 入口 `ExportGeometry(input, outputDir, nodeName, fgxName)` 四参数；动画骨架 `arm_c.scale=(0.01,0.01,0.01)` 后世界骨 ScaleShear 回到单位阵。
- 开跑前清 staging 旧 `fgx/geo/anm/wig` 与 E 盘全部旧 `.cn6`（残留让 BLP 缩水且几何不更新）。
- 判定完成看 `MODEL_DONE`/`ANIM_DONE`/`CONVERT_DONE` 回显与产物哈希，退出码不作判据（3221226525、127 皆为伪失败）。
- `NexusBatch.cs:181` 回显与 E 盘执行体可能不同版本，依赖参数回显时以执行体为准。

## 4. 读数与校验工具

| 工具 | 用途 | 关键约定 |
|------|------|---------|
| NexusDumpBind.cs | 直读 InverseBind、palette、顶点权重索引，输出四判据 | ScaleShear 在 +44（不是 +28）；scaleMode 固定带 3×3 缩放 |
| NexusNames.exe | 骨骼名清单 | fgx 骨骼名哈希存储，文本检索无效，用此工具 |
| NexusBoneCurve.exe | 从动画 fgx 读骨骼曲线 | 逐帧幅度统计、标定基准 |
| RestVsBind.exe | rest 与 bind 一致性 | nonidentity_bones 应为 0/205 |
| jx_pose_check.py | 逐骨 rest 与 t=0 曲线判定 | 退出码 0=PASS / 1=FAIL / 2=用法 |
| FgxViewer（SDK 自带） | 引擎侧旁路渲染 | 游戏内领袖场景黑屏时用它验证几何/材质/动画 |

granny 内存布局：bone Position@+16 / Orientation@+28 / ScaleShear@+44 / InverseWorldTransform@+80；顶点 40 字节步长（Position 0 / BoneWeights 12 / BoneIndices 16 / Normal 20 / UV0 32）。

## 5. 入工程与 ast

- 顺序固定：`jx_assemble.py`（入工程+ast 补丁）→ `jx_ast_normalize.py`（时间线与绑定重建）；颠倒会重复追加（两脚本补丁锚缩进不同）。
- ast 槽位结构与正样本一致（心情槽+迁移时间线补齐；一次性槽位的时间线本身放 idle 片段）；时长取 .anm 实际值，禁止硬编码。
- 管线脚本禁止写任何非目标 ast（曾发生纸片模型 ast 被覆写）。
- 材质：Leader_Matte 类；BaseColor 与 Opacity 成对；实心部位 Opacity 留空串（达妮娅口径），切孔布料用保留 alpha 的二值贴图；贴图 alpha 不能一律当可见性（先看透明占比）。
- 新增贴图：`.dds` 必配同名 `.tex`（复制现有 .tex 改字段），否则 cook 出坏包。

## 6. cook 与部署

```
cd <SDK>\Civ6AssetModTools\Cooker   # SDK: F:\Steam\steamapps\common\Sid Meier's Civilization VI SDK
Civ6AssetCooker_FinalRelease.exe --absolute_paths --no_mt --platform Windows
  --pantry <工程>\<工程名> --pantry <SDK>\Civ6\pantry
  --pantry <SDK>\Civ6\DLC\Shared\pantry --pantry <SDK>\Civ6\DLC\Expansion1\pantry
  --pantry <SDK>\Civ6\DLC\Expansion2\pantry
  --config Civ6.cfg --mode XLP --stewpot <out> <工程>\XLPs\<leader>_qyqxp.xlp
```

- pantry 路径用 Windows 反斜杠（POSIX 分隔符退出码 2）。
- 成功判据：退出码 0、末行 `XLP cook completed with success.`、九类告警逐项 `grep -ic` 全 0（missing file / wrong extension / is not allowed here / class / Replacing asset / error asset / fallback / I/O error / ERRORS）、BLP 体积在正常带（领袖包约 14–21 十进制 MB）。
- cook 前另存日志（复跑覆盖失败日志）与当前部署 BLP 快照（`workspace/gen/backup/`）。
- 部署：复制 BLP 到 `<Mods 目录>\<Mod>\Platforms\Windows\BLPs\leaders\`，两侧 sha256 逐位一致。
- 实机：`gamectl.py kill → launch → wait --want inmenu --timeout 150 → host-game → load`；BLP 不热重载；画面由人观察并口述。

## 7. 口型与微表情扩展（实测做法）

- 语音包络：vgmstream 解码 bank 内 Wwise IMA ADPCM → PCM → 逐帧 RMS（30fps），与原始 wav 相关 0.99999+；六段语音 SOUND 触发在 .ast m_fStartTime（第 16 帧≈0.5s）。
- 口型驱动：JX_Jaw 权重沿嘴宽余弦衰减（行业做法：张口由下颌关节驱动、影响沿嘴宽衰减；权重必须写进 JX_Jaw 本体，写在唇骨上会被 JX_Jaw 全 1.0 覆盖）；四档量化+短语内微张；包络按语音实际时长铺满（禁止固定帧数）。
- 语音长于动画：保持结束姿态继续口型。
- 眨眼：上睑整体下移（行程按眼球竖直跨度定，跨度实测 2.06cm）；闭眼下睑参与（下睑顶点组归属+上睑行程 40%）。
- 待机插入动作：待机循环扩帧；进入过渡以插入片段自身的进入段为载体、叠加衰减到零的局部修正，退出过渡用两端切线的三次 Hermite；插入动作与眨眼频率解耦。端点与速度判据见 `acceptance.md` §循环插入接缝。

## 8. 表情层与接缝诊断

面部形态键转面骨、以及待机拼接的接缝检查，都用 `jx_build5.py` 的两个开关跑，不必全量重烘。

| 开关 | 行为 | 耗时 |
|------|------|------|
| `-- --face-diag` | 导入 psk、建面骨、拟合全部形态键后退出，打印形态键相关诊断 | 约 5 分钟 |
| `-- --idle-only` | 只烘待机段、导出 `JX_IDLE.fbx` 后退出 | 约 7 分钟 |
| 无开关 | `bash workspace/_tools/jx_r4_build.sh` 全量：构建 → 转换 → 装配 → 规范化 → cook → 部署 | 约 18 分钟 |

| 输出 | 含义 | 判据 |
|------|------|------|
| `MORPH_DIAG <预置> direct/conj` | 两种表口径下的逐顶点误差、拉伸比与最差点 | 误差小者的均值与 `MORPH_FIT` 的 rms 同量级 |
| `MORPH_REFINE <键> 前 → 后` | LBS 一致性迭代前后均方 | 后值不大于前值 |
| `MORPH_GAP <预置>` | 无面骨权重而真实位移 >0.1 厘米的面部顶点数 | 期望 0 |
| `MORPH_STRETCH <键>` | 相邻顶点被不同骨拉开的绝对距离 | 薄片区 ≤0.6 厘米 |
| `IDLE_SEAM HEAD/TAIL` | 接缝段逐帧全骨最大转角 | 统计范围盖住接缝之后 12 帧 |
| `ANIM_JERK` / `ANIM_JERK_LOC` | 每骨最大单帧转角／位移及帧号 | 面骨不出现 1.20 厘米 |
| `ANIM_COMPOSE_IDLE` | 总帧数、插入段、过渡帧数、接缝帧号 | 按帧号写死的常量以此为准 |

逐骨步长与整体速度用两个随包脚本（都在 `scripts/`）。下面的 `<Blender>` 为 SKILL.md §〇 的 4.5.9 绝对路径：

```bash
"<Blender>" -b --factory-startup --python scripts/jx_diag_track.py -- --range 530,542 --bones Bip001Head,Bip001LHand,Bip001RHand
"<Blender>" -b --factory-startup --python scripts/jx_diag_idle_velocity.py -- --range 476,492
```

第一个按帧打印指定骨的角度步长（度/帧），第二个打印头、手、盆骨的世界步长、二阶差分与全片加速度前 12 名。FBX 导入后帧号整体加 1，两个脚本默认用 `--off 1` 吸收该偏移。
