# Na2Tool：na2 导出工具

## 随包 NexusNA2.exe 不可用

NexusNA2.exe 在当前环境无法导出原版动画的帧数据，实测证据：

- 输入：原版模型 `SDK Assets/Civ6/pantry/Geometries/LEAD_EGYP_Cleopatra.fgx` 与原版动画 `SDK Assets/Civ6/pantry/Animations/Cleopatra_ANIM_Happy_Idle.fgx`。
- 回显 `NA2_EXPORT result=3` 后紧跟 `NA2_DONE`，退出码 0。
- 产物 2,584 字节、1,227 行，其中只有 7 行非空（仅表头 FrameSets / FrameCount / FirstFrame / LastFrame / FPS / Bones），没有任何帧矩阵行。
- `result` 的取值是重试次数：`NexusBuddy/FileOps/NB2NA2FileOps.cs:149` 返回 retryCount，`:75` 把 retryCount 初始化为 0，`:109` 每轮失败加一，`:80` 以 retryLimit 为上限。
- 每轮失败的原因被 `NB2NA2FileOps.cs:97` 的 `catch (Exception)` 吞掉，采样调用写在 `:94`（`anim.SampleBone(model, bone.Name, time)`）。
- 全骨采样探针进程的退出码为 139，说明原生 SampleAnimation 抛 AccessViolationException。
- 原版模型共 1220 骨，其中只有 195 骨带动画轨迹（共 202 条 TRACK）；随包工具对这 195 骨同样全部失败。

需要原版动画的 na2 时使用同目录的 Na2Tool.exe。

## Na2Tool.exe 用法

命令行契约与 NexusNA2 一致：

    Na2Tool.exe <模型 fgx> <动画 fgx> <输出 na2> [起始帧] [结束帧]

- 模型 fgx：含骨架与蒙皮的模型文件。
- 动画 fgx：含动画轨迹的动画文件。
- 输出 na2：na2 文本文件（f6 即可），表头为 FrameSets / FrameCount / FirstFrame / LastFrame / FPS / Bones。
- 起始帧默认 0；结束帧默认动画总帧数，超过总帧数时按总帧数计算。采样区间为 [起始帧, 结束帧)。
- na2 的 FrameCount 写入结束帧的取值，因此起始帧大于 0 时，起始帧之前的帧按静止姿态填充。
- 参数个数少于三个时，立即在 stderr 打印一行 usage，并以退出码 2 结束；第一个参数不是任何模式名时按本契约解释为模型路径。

成功回显 `DIRECT_DONE bones=<骨骼数> frames=<帧数> start=<起始帧> end=<结束帧> -> <输出路径>`，退出码 0。

输出的骨骼数量等于该动画里有轨迹的骨骼数量，模型中没有动画轨迹的骨骼不写入 na2。

另有五个分步模式，便于单独核对中间结果：

    Na2Tool.exe rest    <模型 fgx> <输出 rest.tsv>
    Na2Tool.exe anim    <动画 fgx> <rest.tsv> <输出 anim.tsv> [起始帧] [帧数量]
    Na2Tool.exe compose <rest.tsv> <anim.tsv> <输出 na2> [占位] [骨选择] [帧上限]
    Na2Tool.exe ref     <模型 fgx> <动画 fgx> <输出 ref.tsv> <骨上限> <帧数>
    Na2Tool.exe probe   <动画 fgx> <起始帧>

- `anim` 的第 5 个参数是帧数量，结束帧取「起始帧 + 帧数量」与总帧数的较小值。
- `compose` 的第 4 个参数是占位，当前不使用；第 5 个参数为 `tracked` 时只输出动画里有轨迹的骨骼，其它取值输出模型全部骨骼；第 6 个参数限制帧数。
- `ref` 与 `probe` 是评测通道，用于和引擎采样结果对照，正常导出不需要调用。

单命令模式等价于按 `rest`、`anim`、`compose` 三步依次执行，骨选择与 `tracked` 相同。

## 文件格式

- 每行以 CRLF 结束，编码 UTF-8，浮点按 InvariantCulture 以 `f6` 格式输出。
- 骨骼名独占一行，随后每帧一行 16 个浮点（4x4 世界矩阵按行展开），行尾保留一个空格。

## 实现说明

- 单命令通道与 `compose` 采样只用 `IGrannyCurve.Sample`，再按骨骼层级合成世界矩阵，不调用会触发原生 SampleAnimation 的 `SampleBone`。
- 与引擎 `SampleBone` 的 50 个 4x4 矩阵对照，maxdiff=0.001102。
- 运行依赖同目录的 CivNexus6.exe 与 Firaxis.* 托管程序集，.NET 从 Na2Tool.exe 所在目录加载它们。
