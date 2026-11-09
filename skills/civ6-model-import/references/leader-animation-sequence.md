# 领袖动画播放语义：一次性入场 → 循环待机

> 回答的问题：**「能不能让一段动画只在初次打开时播一次，之后循环另一段？」**
> 结论：**可行，而且是 Civ6 原生的标准机制**，不需要自己写状态机、不需要改 UI Lua、不需要在片段里加标记。
>
> 归属分工：本文讲**播放顺序与循环语义**（DB 表 + Lua 队列 + AST 槽名）。`.ast` 内四处容器的引用增删/降级读 `references/ast-anim-binding.md`；片段选择与循环接缝读 `SKILL.md` 第五节与 `references/acceptance.md`；表情曲线读 `references/morph-curves.md`。
>
> 证据分级：**A** = 本机游戏明文实测；**B** = 有旁证的推断；**C** = 未验证推断，禁止当交付依据。
> 行号对应 2026-11-07 本机安装的明文文件；路径统一写成 `<Civ6>/Base/Assets/...`。该结论来自引擎明文，与具体角色素材无关。

## 一、先把「只播一次」说清楚

用户说「初次打开」时，至少有三种不同语义，动手前必须先问清是哪一种：

| 语义 | 触发范围 | 原生载体 | 结论 |
|---|---|---|---|
| **每次打开外交界面播一次** | 每次进入该界面 | `NEUTRAL_GREETING` 序列 | 原生支持，A 级 |
| **整个存档首次会面播一次** | 每对领袖一次 | `FIRST_MEET` 序列 + `01_FIRST_MEET` 槽 | 原生支持，A 级 |
| **在单个片段内部标「只播一次」** | —— | 无 | **做不到**：循环与否不是片段属性，B 级 |

第三种是最常见的误判。`.ast` 里只有槽位、时间线、时长、触发器与绑定，**没有 loop / one-shot / repeat 字段**（本机工程 AST 实测 0 命中）；是否循环由 UI 队列与被调用的动画语义决定。把入场动作拼进循环待机片段里，它就会随待机每轮重播。

## 二、证据链（A 级，本机明文）

### 1. 数据表：`<Civ6>/Base/Assets/Gameplay/Data/LeaderAnimations.xml`

表结构只有四列：`Name` / `Leader` / `Initial` / `Sequence`，全表 21 行，`Leader` 全为 `ANY`。`Sequence` 用分号分隔多个动画名，**最后一项通常是循环 IDLE**：

| Sequence 行 | Name | Initial | Sequence |
|---|---|---|---|
| 8 | `NEUTRAL_IDLE` | — | `NEUTRAL_IDLE` |
| 20 | `NEUTRAL_POSITIVE` | `NEUTRAL_IDLE` | `NEUTRAL_POSITIVE;NEUTRAL_IDLE` |
| 39 | `NEUTRAL_TO_HAPPY` | `NEUTRAL_IDLE` | `TO_HAPPY;HAPPY_IDLE` |
| 85 | `NEUTRAL_GREETING` | `NEUTRAL_IDLE` | `NEUTRAL_POSITIVE;NEUTRAL_IDLE` |
| 92 | `ENRAGED` | `$(MOOD)_IDLE` | `ENRAGED` |
| 120 | `FIRST_MEET` | — | `FIRST_MEET` |

`Initial` 是「先把状态机摆到哪个基准姿态」，不是要播的入场动画。`ENRAGED` 的 `$(MOOD)_IDLE` 说明 `Initial` 支持心情占位符替换。`FIRST_MEET` 只有单段、无 `Initial`，正是「一次性动作」的官方形态。

### 2. 队列实现：`<Civ6>/Base/Assets/UI/LeaderSupport.lua`

| 行 | 内容 | 意义 |
|---|---|---|
| 83–93 | `GetLeaderAnimationSequence()`：`SELECT Sequence, Initial from LeaderAnimations WHERE Leader = ? AND Name = ?`，查不到再查 `Leader = 'ANY'` | **支持按具体领袖加特化行**，覆盖官方默认 |
| 51–77 | `$(MOOD)` 替换；`string.gmatch(row.Sequence, "([%w_]+)")` 把序列切成数组 | 分隔符是「非字母数字下划线」；**自定义序列名只能用 `[A-Za-z0-9_]`**，连字符/点号会被切开 |
| 11–29 | `LeaderSupport_UpdateAnimationQueue()`：先播 `Initial`（`BlendTime = 0.0`），紧接着立刻播 `Sequence[1]`，然后 `table.remove(..., 1)` | 源码注释原文：`forced initial animation could be a looping animation, which never completes` —— 官方明确知道循环动画不会完成 |
| 96–118 | `LeaderSupport_QueueAnimationSequence()`：队列空则直接起播；非空则替换队列并让当前动画完成后 kick off | 注释原文：如果上一段是循环，新动画「would never get to our desired animations」 |

### 3. 触发时机：`<Civ6>/Base/Assets/UI/DiplomacyActionView.lua`

| 行 | 内容 |
|---|---|
| 842 | 打开界面时初始语句类型取 `"GREETING"`（自身则 `NO_TARGET`） |
| 625 / 630 | `kParsedStatement.LeaderAnimation` → `LeaderSupport_QueueAnimationSequence()` |
| 2104 / 2105 | `Events.LeaderScreenFinishedLoading` 与 `Events.LeaderAnimationComplete` 注册 |
| 2227–2233 | `OnLeaderAnimationComplete()` → 调 `LeaderSupport_UpdateAnimationQueue()` 推进队列 |

配套语句表：`<Civ6>/Base/Assets/Gameplay/Data/DiplomacyStatements_Greeting.xml:29` 的 `<LeaderAnimation>NEUTRAL_GREETING</LeaderAnimation>`；`DiplomacyStatements_FirstMeet.xml:31/41` 的 `<LeaderAnimation>FIRST_MEET</LeaderAnimation>`。全库 `<LeaderAnimation>` 取值里 `FIRST_MEET` 出现 6 次、`NEUTRAL_GREETING` 3 次。

### 4. 机制归纳

```
打开界面 → 取 GREETING 语句 → 读 LeaderAnimations 表
       → Sequence = [一次性动作, 循环 IDLE]  （分号切分）
       → 播 Initial 摆基准 → 播 Sequence[1]
       → 一次性动画结束触发 LeaderAnimationComplete → 队首移除 → 播 Sequence[2]（循环）
       → 循环动画不触发 Complete → 队列停在它上面
```

**关键约束：队列最后一项必须是循环动画**。把循环片段放在中间，后面的项永远播不到（源码注释已明说）。因此「一次性入场 + 循环待机」就是 `Sequence="<一次性槽名>;<循环槽名>"`。

## 三、结论与边界

1. **可行**，且不用造状态机：改 DB 序列 / 改 AST 槽位绑定即可，引擎已有队列、完成事件与回退逻辑。
2. **循环不是片段属性**：`.ast` / `.anm` 里没有循环标记，别去找、更别去造一个。
3. **槽名必须闭环**：DB `Sequence` 里的每个名字都要能在 `.ast` 的槽位绑定里找到对应动画；否则队列播到那一项会落空（B 级，需实测）。
4. **两种「初次」触发范围不同**：GREETING 每次打开界面，FIRST_MEET 每存档首次会面。选错会出现「每次都播」或「只播一次之后再也不播」。
5. **按 `Leader` 特化行**：`DB.Query` 优先查具体领袖，理论上 mod 可为单个领袖写专属 `NEUTRAL_GREETING`。但「自定义序列名能否被引擎与 AST 状态机接受」「`ms_OtherLeaderName` 传的到底是不是 `LEADER_*` 类型名」属 **C 级**，必须实机验证，不得当方案定论。
6. **常驻道具与入场动作**：单 mesh 领袖通常不做逐段显隐，入场段附带的道具在循环段里仍会可见；若要「只在入场出现」，需要骨曲线把它移出视野或另做显隐机制 —— **C 级推断，未验证**。

## 四、三条落地路线

| 路线 | 做法 | 代价 / 风险 | 级别 |
|---|---|---|---|
| **1（推荐先做）** | 只改 AST：把 GREETING 对应的情绪槽从循环 IDLE 改绑独立的一次性片段，同时把循环片段恢复成纯 Loop；DB 不动 | 零 DB / 零 Lua 改动，回退容易；但同一情绪的其它外交语句也会播这个动作 | A（改法）/ C（作用范围观感） |
| 2 | 在 mod 的 `LeaderAnimations` 表加 `Leader=<具体领袖>` 特化行，用自定义 `Sequence` 名 | 作用范围最精确；但自定义槽名与 AST 的映射需实机验证，且命名受 `[%w_]+` 限制 | C |
| 3 | 直接用现成的 `01_FIRST_MEET` 槽与一次性片段 | 零新增资产、零 DB 改动；只在真·首次会面触发，不是每次打开界面 | A |

路线 1 与 3 不互斥：先拿现成一次性片段做机制验证，通过后再决定要不要为特定入场动作新增一段专用入场动画。

## 五、最小验证实验（单变量、不动模型）

1. 备份当前 `.ast` 与 cook 产物，记录 sha16 与字节数作回退点。
2. **只改一个变量**：一个槽位的绑定，指向现成的一次性片段；循环片段保持不变。
3. 重新装配 → cook，告警计数为 0，对比包体积确认改的是生效的那份 `.ast`（见 `ast-anim-binding.md` 第四节）。
4. **部署须用户明确指令**；离线全绿不作实机结论。
5. 实机只认用户口述：「是否播一次后停在循环 IDLE」。未口述 = **未闭环**，报告中如实写未闭环。
6. 通过后才进入「新增一段专用入场动画 / 道具适配 / DB 特化行」。

纪律沿用项目 P0：只取证后动、单变量 A/B、每版留回退点与指纹、答案异常或中断一律 ABSTAIN（零写操作只出报告）。

## 六、红旗清单

- 在 `.anm` / `.fgx` 里找 loop 标记，或给片段加「只播一次」字段 → 方向错；
- 只改 `.ast` 引用、不改 DB 序列名 → UI 仍回退 `Leader='ANY'`，行为不变；
- 把循环 IDLE 放在 `Sequence` 中间 → 后面的动画永远排不到；
- 自定义序列名含 `-`、`.`、空格 → `string.gmatch("([%w_]+)")` 会把它切成多段；
- 把「每次打开界面」当成「存档首次会面」，或反过来；
- 改了 DB 表但 cook 后包体积/行为不变 → 改的不是生效文件（先对部署指纹，见 `misattribution.md`）；
- 一次性片段本身来自循环素材（内部含拼接的表演段）→ 用户看到的仍是重播，先查片段内容再看队列。

## 七、接线

- 本文：`references/leader-animation-sequence.md`（播放语义 / 队列 / 路线 / 待验项）
- `.ast` 四处容器引用增删、降级与恢复：`references/ast-anim-binding.md`、`scripts/ast_bind.py`
- 片段选择、循环插入接缝与时长回填：`SKILL.md` 第五节、`references/acceptance.md`
- 失败归因与基准指纹纪律：`references/misattribution.md`
- 本项目完整调研报告（含精确行号、工程 AST 现状与状态留档）：`<方案根>/workspace/gen/reports/S14_领袖动画一次性入场与循环待机机制调研_20261107.md`
- 报告与实验产物一律落 `<方案根>/workspace/gen/reports/`；跨会话移交按 `references/handover.md` 六要素。
