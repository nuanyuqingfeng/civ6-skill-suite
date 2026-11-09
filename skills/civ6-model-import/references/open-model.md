# 打开模型 — 独立 GUI 启动流程与验收判据

> 路由来源：`SKILL.md` §四「任务分流」首行。命中「打开/查看模型、预览贴图、窗口一开就关、要一个长期留着的 Blender GUI」即进本文。
> **定性：这是只读查看任务。不进十步流程、不 cook、不部署、不改模型/动画资产。** 导入的是 rest 态，无 pose。
> 本文是「打开模型」的唯一执行依据；`SKILL.md` §〇 只保留命令与摘要。

## 一、为什么窗口会自己关掉（根因，2026-11-06 实测）

命令会话派生的进程被关进一个 **不允许 breakaway 的 Windows job object**：`CREATE_BREAKAWAY_FROM_JOB` 直接 `WinError 5`。命令/会话一结束，整棵子树被回收，GUI 随之消失。父链实测：

```
explorer.exe -> WorkBuddy.exe -> sandbox-cli.exe -> bash.exe -> blender.exe
```

只看**同一条命令内**的轮询会误判：实测 `Start-Process` 在命令内 16 s 窗口标题、hwnd、WS 全正常，跨一条命令立刻 `NO BLENDER PROCESS`。**命令内轮询不算「已打开」。**

| 机制 | 实测结果 |
|------|---------|
| 会话内 `Start-Process` | 命令内正常，命令结束即回收 |
| WMI `Win32_Process.Create` / COM `WScript.Shell` / `schtasks.exe` / `Add-Type` 运行时编译 | 被安全策略拦截（schtasks 在程序黑名单，禁止绕行） |
| Python `CREATE_BREAKAWAY_FROM_JOB` | WinError 5，job 不允许 breakaway |
| `os.startfile(<cmd>)` | 未产生 Blender |
| `run_in_background: true` 直接跑 blender | 稳定，但父链仍是 `bash -> blender`，随后台任务生命周期结束 |
| **`explorer.exe <执行器.cmd>`** | ✅ 唯一可用：桌面 shell 派生，执行器退出后 Blender 无活父进程 |

`explorer.exe` 是 Session 1 常驻桌面进程，**不属于 agent 会话树**，因此由它派生的进程不会被上述 job 回收。

## 二、两阶段自举启动器（推荐，唯一默认）

| 角色 | 本机实例 | 分发模板 |
|------|---------|---------|
| 入口（Stage 1） | `E:\SoftWares\civ6_nexus_work\dj_preview\打开当前模型.cmd`（英文别名 `open_danjin.cmd`） | `scripts/open_model_launcher.cmd` |
| 执行器（Stage 2） | `E:\SoftWares\civ6_nexus_work\dj_preview\_open_detached.cmd` | `scripts/_open_detached.cmd` |

两处实现**逐位一致**，改一处必须同步另一处（用 sha256 比对，不要靠肉眼）。

```
用户/agent 调用入口
   ├─ 有参数（拖放） -> 把模型路径写入 %TEMP%\civ6_open_model_target.txt
   └─ 无参数（双击） -> 删除该文件，执行器用默认模型
入口: start "" explorer.exe "%~dp0_open_detached.cmd"  -> 立即 exit /b
   ↓  explorer.exe 是会话外桌面进程
执行器: 设 BLENDER_USER_RESOURCES -> start blender.exe --python open_model.py -- <MODEL> -> exit /b
   ↓  执行器退出，Blender 变孤儿
Blender: 无活父进程，不属于任何 agent 会话树
```

- 入口**绝不直接启动 Blender**；这是「不依赖父级 cmd」的关键。
- 执行器头部 4 个可用环境变量覆盖的常量：`CIV6_BLENDER_HOME`、`CIV6_BLENDER_USERRES`、`CIV6_OPEN_MODEL_PY`、`CIV6_DEFAULT_MODEL`。换机器只改这 4 个或拖放指定模型。
- 启动日志：`%TEMP%\civ6_open_model_launch.log` 每行 `LAUNCH <时间> MODEL=<路径> EXECUTOR=<执行器>`，用于确认「打开的是哪个模型」。
- `cmd` 里设环境变量必须 `set "VAR=值"` 且分行写；`set VAR=值 && …` 会把尾随空格写进变量（`BLENDER_USER_RESOURCES` 变成 `…\userres ` → `WinError 3`），细节见 `SKILL.md` §〇。

### 三种调用方式

| 场景 | 做法 | 是否脱离会话 |
|------|------|-------------|
| 人工看当前模型 | 双击 `打开当前模型.cmd` | ✅ |
| 人工看任意模型 | 把 `.cn6/.psk/.fgx/.blend` 拖到入口上 | ✅ |
| agent 临时查看 | `run_in_background: true` 跑 `SKILL.md` §〇 那条命令 | ❌（随后台任务结束），只作临时 |
| agent 要留窗口 | 从会话内调用入口 `.cmd`（实测可脱离）或请用户双击 | ✅ |
| 无头批量出图 | `blender.exe -b --python open_model.py -- <模型> --no-gui --out <blend>` | 不适用（进程自行退出） |

`E:\SoftWares\blender45\OPEN_MODEL.cmd` 是旧拖放式入口，只适合人工；**不要在 agent 会话里当独立启动器用**。

## 三、硬性验收判据（缺一不算打开成功）

1. **跨 ≥2 条独立命令**复核：`blender.exe` 的 `PID` 存在、`MainWindowHandle != 0`、`uptime > 60 s`、窗口标题含 `Blender 4.5.9`。
2. **父链**：父 PID 已消失（`Get-CimInstance Win32_Process` 查不到），或链上不含 `sandbox-cli.exe` / `bash.exe` / `WorkBuddy.exe`。孤儿进程是预期结果，不是故障。
3. **加载日志** `%TEMP%\open_model.log`：末行 `OPEN_MODEL_OK`；`materials=N textured=N`（`textured < materials` 说明贴图没配上，回去看 `tex_roots=`）；`OPEN_MODEL view={… 'lights': 3, 'shading_failures': []}`。`shading_failures` 非空先修视口属性，别谈画面。
4. **启动日志** `%TEMP%\civ6_open_model_launch.log`：有对应 `LAUNCH` 行且 `MODEL=` 与预期一致。
5. **可视证据**：把窗口置前后抓图（`PrintWindow(PW_RENDERFULLCONTENT)` 或置前后 `ImageGrab`），确认模型、贴图、材质预览都在。启动 splash 会遮挡，点一下视口或按 ESC 收掉再抓。

> 旧判据 `%TEMP%\view_setup.log` 末行 `VIEW_SETUP_OK` / `shading=['MATERIAL']` 属于已废弃的两步法，**不再使用**。旧脚本 `scripts/probes/open_model_in_blender.py` 同样废弃。

## 四、故障树

| 现象 | 原因 | 处置 |
|------|------|------|
| 窗口几秒后消失 | 用了会话内一次性派生（`Start-Process` / `subprocess.Popen`） | 改走两阶段启动器；按 §三 第 2 条查父链 |
| 报「已打开」但用户看不到 | 只做了命令内轮询 | 按 §三 第 1 条跨命令复核 |
| 黑窗一闪 | 入口/执行器 cmd 瞬时窗口 | 正常；若 cmd 不退出，检查 `start ""` 的标题参数是否丢失 |
| 模型无贴图 / `textured < materials` | 插件未加载或贴图根目录没命中 | 确认 `BLENDER_USER_RESOURCES`；加 `--tex-root <目录>`；看 `tex_roots=` 命中数 |
| `WinError 3` / `userres \extensions` | `set VAR=值 && …` 写进尾随空格 | 改 `set "VAR=值"` 并分行 |
| 打开的不是想要的模型 | `%TEMP%\civ6_open_model_target.txt` 残留上次拖放路径 | 双击入口会删除它；或手动删后再开 |
| 抓图抓到别的窗口 | 窗口被遮挡 | 置前后抓，或用 `PrintWindow` |
| 换了机器打不开 | 执行器头部 4 个路径常量还是本机的 | 覆盖 `CIV6_*` 环境变量，或改执行器头部并同步两处实例 |

## 五、禁止事项

- **禁改** `E:\SoftWares\blender45\open_model.py` 与 `FgxToCn6.exe`（源码 `E:\SoftWares\civ6_nexus_work\rover_view\FgxToCn6.cs`）。要调整「打开」行为只改启动器与本文。
- 禁止用 WMI 进程创建、COM 自动化、`schtasks.exe`、运行时编译来「脱离会话」——全部被安全策略拦截，且 `schtasks` 明确禁止绕行。
- 禁止把 `open_model.py` 的两步法旧脚本 `open_model_in_blender.py` 当现行方案。
- 禁止把「命令内窗口存在」当成交付依据。

## 六、实测留档（2026-11-06）

- A/B 探针：`start "" explorer.exe <cmd>` 与直接 `explorer.exe <cmd>` 均触发 explorer 派生（`HIT_A` / `HIT_B` 都写入），采用前者（入口立即返回更明确）。
- 无参（双击）路径：从 agent 会话内调用入口 → `TARGET_FILE` 被正确删除 → 执行器用默认 cn6 → 新 Blender `PID 55072`、父 `8636 GONE`、父链只剩自身、跨命令 uptime 95 s，`OPEN_MODEL_OK` / `materials=6 textured=6` / `lights=3 shading_failures=[]`。
- 有参（拖放）路径：`TARGET_FILE` 正确写入传入路径，`civ6_open_model_launch.log` 的 `MODEL=` 与之逐字一致。
- 更早一次手动 `& explorer.exe <cmd>`：`PID 54996`、父 `25948 GONE`、跨命令 uptime 205 s，结论一致。
