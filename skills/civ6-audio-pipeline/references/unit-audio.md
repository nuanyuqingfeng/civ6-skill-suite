# 单位音效（.ast 触发点 → Wwise 事件）

本文件是 `SKILL.md` §8「单位音效」的正文。做**单位模型音效替换 / 给新单位配语音**时按本文走。
标注口径（全文一致）：

- **【实测】** = 用户在实机（游戏内）听过并回报的现象，最高证据等级；
- **【核验】** = 在文件 / 产物 / 日志里直接看到的证据（可复现，但不等于引擎运行时行为）；
- **【推测】** = 没有验证过，只是根据相邻证据的推断，**不要当成结论引用**。

---

## 1. 链路模型

```
.bhv / .ast（行为资产，槽位表 + 时间线）
  └ m_timelineBindings：槽位名 → 时间线名
      └ m_timelines：时间线 → m_Triggers（时间点 + m_FXName）
          └ m_FXName = Wwise 事件名 → SoundBank 里的 Event
              └ Event → Action(Play) → 容器 / Sound → 媒体
```

**【核验】** 触发点写在 `.ast`（`AssetObjects..AssetInstance`）还是写在独立 `.bhv`（`AssetObjects..BehaviorInstance`），两种组织方式**产物等价**：都会 cook 进单位资产 `Platforms/Windows/BLPs/units/<单位>.blp`。区别只是 `.ast` 用自带 `m_behaviorDataSets` 还是用 `m_behaviorInstances` 指向 `.bhv`（参考模组 SkyCastle 走后者，本工程走前者）。

**【核验】** 引擎请求哪个「状态」（进而播放哪条时间线）由**引擎侧状态机**决定；DSG 决定状态图结构，`.bhv` 只描述「状态 → 动画 / 时间线」。

---

## 2. 槽位真实性（最重要的一张表）

**结论：同一条单位，常态攻击里真正会被请求的槽位可能只有一条。**

| 槽位 | 本工程实测 | 证据 / 说明 |
|---|---|---|
| `ATTACK_A` | ✅ 唯一有效的攻击槽 | **【实测】** 四槽各挂一条时长差异明显的探针（0.18 / 0.66 / 1.90 / 3.33 s），连打多次只听得到 `ATTACK_A` 那条 |
| `ATTACK_1 / ATTACK_2 / ATTACK_3` | ❌ 死槽（本工程） | **【实测】** 同上，一次都没响；**【核验】** `.ast` 里绑定与触发点都正确、BLP 里哈希命中，说明不是链路问题，是引擎不请求 |
| `VICTORY` | ❌ 死槽 | **【核验】** 原版 5065 个 `.ast` 里只有 `Modern Armor.ast` 一条 VICTORY 时间线；**【实测】** 挂探测音从未响过 |
| `HERO_A / HERO_1` | ⚠ 偶发（≈突进终结技） | **【实测】** 多次击杀里偶发响一次；**【核验】** 原版 `Units.artdef` 的 `HeroAttack` 是战斗风格（Range 10.76、带 KillType），由 `CombatAttack` 选择——不是伟人/技能槽。**【实测】** 只给它挂**单条固定**语音时，会出现「偶尔冒一句固定台词 + 角色做一个固定动作」——因为槽活、语音单条、时间线又绑着胜利动画 |
| `ACTION_1` | ❌ 死槽 | **【核验】** `UnitActivities.artdef`：`ACTIVITY_BUILD / CREATE_DISTRICT / CREATE_WONDER → EXPEND=ACTION_1`，只有建造者类单位会请求 |
| `RUN_A / RUN_COMBAT / RUN_START / RUN_STOP` | ✅ | **【实测】** 脚步在实机可闻 |
| `DEFEND_A / DEFEND_1 / DODGE_A / REACT_*` | ✅ | **【实测】** 受击/格挡类语音正常 |
| `DEATH_A` | ✅ | **【实测】** 死亡语音正常 |

**推论**：想「常态攻击出语音」，只挂 `ATTACK_A`；想「技能/大招语音低频出现」，**不能靠多分几条槽**（没有第二条槽可给），只能在同一个事件内部做概率。

**HERO 槽的正确用法**：它是「活槽」，所以要么**不挂**（保持静音），要么挂**一个随机池**（和 `ATTACK_A` 共用，或独立——见 §4.6）。绝不要只挂一条固定语音——那正是「偶发固定台词 + 固定抬手挥出」的成因。同时把 `HERO_A / HERO_1 / VICTORY / ACTION_1` 的时间线动画从 `*_VICTORY` 改回 `*_ATTACK_A`（见 §2.1），否则即使不播音，动作仍是胜利动画。**时间线的 `m_fDuration` 必须等于该剪辑 `.anm` 自身的时长，绝不能为了「让语音播完」去拉长它**（见 §2.2）。

### 2.1 槽位动画由时间线决定，不由 `m_animationBindings` 决定

**【实测】** 这是本项目最贵的一个坑：`.ast` 里有两处「槽 → 动画」的写法，长得几乎一样，但只有一处决定实际播放。

| 位置 | 结构 | 是否决定播放 |
|---|---|---|
| `m_behaviorDataSets` → `m_animationBindings` | `<m_SlotName text="HERO_A"/><m_AnimationName text="roverunitf_ATTACK_A"/>` | ❌ 只是编辑器映射表，改它**播放不变** |
| `m_timelines` → `m_Timelines` → `Element` | `<m_Name text="HERO_A"/><m_Description/><m_AnimationName text="…VICTORY"/><m_fDuration>5.8</m_fDuration>` | ✅ **真正决定播放哪段动画与时长** |

误改前者的症状：`unit_ast_triggers.py --list` 里 `HERO_A` 仍显示 `roverunitf_VICTORY` / 5.8 s——它读的是时间线。
判据就是 `--list` 的输出；改完必须再看一遍，两处都相等才算改对（`m_fDuration` 要同步改成目标动画的时长，否则时间轴与动画对不齐）。

### 2.2 时长铁律：时间线 `m_fDuration` == 剪辑 `.anm` 的 `m_fDuration`

**【实测】** 2026-11-05 踩过的坑：为了让 2.74 s 的大招台词不被截尾，把 `HERO_A / HERO_1` 的时间线从 2.2 拉到 2.9，随后观测到战斗节奏异常；回滚到 2.2 后恢复。`roverunit_ATTACK_A` 这段剪辑被 **8 条时间线共享**，其中 2 条变成 2.9 后，引擎对同名剪辑的时长认知被污染，普攻（2.2）也会受影响。

> **口径更正（同日复测）**：当时把症状记成「战斗只做一次动作就回待机」，用户复测后改为「两次攻击之间插入一次固定且不协调的待机姿势」，并发现**回滚时长后该姿势仍在**。所以时长铁律本身依然成立（原版口径 + 共享剪辑必须同值，回滚无副作用），但**它不是这个姿势的根因**——真正原因见 §2.3。别再把「姿态怪」直接归到时长上。

规则：

1. 时间线时长以**剪辑**为准，用 `Animations/<剪辑>.anm` 里的 `<m_fDuration>` 覆盖式核对；
2. **共享同一剪辑的所有时间线必须同值**（本工程 `ACTION_1 / ATTACK_1/2/3 / ATTACK_A / HERO_A / HERO_1 / VICTORY` 都是 2.200，女 2.666667）；浮点精度也要一致，`2.667` 和 `2.666667` 算两种值；
3. **要长语音不被截尾，只能压素材，不能拉时间线**：见 §2.2a；
4. 验收口径：`--list` 里同一动画的所有行时长必须完全相同，且等于 `.anm` 的 `<m_fDuration>`。

#### 2.2a 大招语音收紧：去空白 + 轻微加速，绝不砍尾

**【核验 + 实测】** 2026-11-05 16:00。解包素材里的 `UL_*` 常带大段**数字静音**（不是混响）：
男 `UL_16` 2.744 s 中 `0.6~1.7 s` 是 −77~−112 dBFS 的全零空白；还有 1.34 s 的尾空白。
直接截尾会把后半句台词砍掉；只做 3% 加速又压不进 2.2 s。

正确顺序（`scripts/unit_ult_tighten.py`，幂等、改 `Originals/SFX/*.wav`）：

1. 砍首尾空白，保留 30 ms 起音 / 120 ms 尾音余量；
2. 把内部 ≥150 ms 的死寂段压到 150 ms（**保留停顿感，不删成 0**，切点做 3 ms 淡变）；
3. 仍超长才对**整条**音频 `atempo`（保音调），留 1.5% 帧对齐余量，最多两轮补偿；
   所有条目统一给 1.03 的轻微加速，实际最大只到 1.08。

男目标 2.15 s / 女 2.58 s（时间线 2.200 / 2.666667 减余量）。结果：男 6 条超长
（2.341~2.744 s）全部降到 ≤2.116 s，女最长 2.615 s → 1.914 s，**零截断**。
改完必须删 `.cache/Windows/SFX/*_UL_*.wem` 强制 Wwise 重转码，再 `--generate`；时长验收口径见 §2.2 规则 4。

### 2.3 BREATHING 槽劫持：两次攻击之间的「固定怪姿势」

**【核验 + 实测】** 2026-11-05 定位。症状：两次攻击动画之间插入一个固定待机姿势（托右肘、右手抬到头部高度），躯干与下半身对不上、观感不协调；用户觉得「以前似乎没有」。根因**不在音频、也不在时长**，而是 `.ast` 自定义了原版没有的槽。

**原版 DSG `potential_any_graph.dsgxml`（SDK pantry）是双层结构**：

| 状态 | `Normal` 基础层 | `Additive` 叠加层 |
|---|---|---|
| `IDLE` | `BREATHING_A` | `IDLE_A/B/C/D` |
| `IDLE_COMBAT` | `BREATHING_COMBAT_A` | `IDLE_COMBAT_A/B/C/D` |
| `IDLE_FORTIFY` / `REACT_RANGED` | `BREATHING_A` | 对应姿势层 |

基础层要的是**全局通用细微呼吸动画**，叠加层才是单位自己的待机 / 战斗待机姿势。

**【核验】** 扫 SDK pantry 全部 `.ast`：出现的只有 `IDLE_COMBAT_A~D`（58 个单位）、`RUN_COMBAT*`，**没有任何 `BREATHING_A` / `BREATHING_COMBAT_A` 槽**。原版单位不提供这两个槽 → 基础层回落全局呼吸动画 → 只叠一份姿势。

本工程却补了它们，并指向自己的**完整**待机动画：

| | `BREATHING_A` | `BREATHING_COMBAT_A` |
|---|---|---|
| 男 | → `roverunit_IDLE_A`（4.03 s 完整默认待机） | **不存在**（所以男漂战斗态本来就没这问题，天然对照组） |
| 女 | → `roverunitf_IDLE_A` | → `roverunitf_IDLE_COMBAT_A`（2.53 s 完整战斗待机姿势） |

`IDLE_COMBAT` 状态下基础层播一整段战斗待机姿势、叠加层再叠一整段 `IDLE_COMBAT_A/C` → **同一套姿势算两遍**，躯干旋转/位移加倍，正是「躯干姿势不对」。「每次固定」是因为基础层是 Weighted 选择器里唯一的 Sequence，恒定命中。

**「之前似乎没有」的解释**：`BREATHING_*` 槽从建项（11-02）就在，10:15 起所有备份逐字节相同，动画资产也从未改动；本轮动的是触发点与 HERO 动画，只是让战斗态切换更显眼了。**不是清理误伤**。

**修法（按原版口径）**：移除这两个槽的全部定义：

```bash
S=<skill>/scripts
python $S/unit_ast_anim.py <单位>.ast --drop BREATHING_A BREATHING_COMBAT_A --dry
python $S/unit_ast_anim.py <单位>.ast --drop BREATHING_A BREATHING_COMBAT_A
python $S/unit_ast_anim.py <单位>.ast --list --animdir <工程>/Animations
```

`--drop` 删三处：`m_timelines` 的 Element（内含嵌套 `m_Tracks`，脚本按标签配平删除）、`m_animationBindings`、`m_timelineBindings`；删完做 XML 解析校验，并确认触发点列表逐条不变。

> ⚠ **别用「把 `IDLE_COMBAT_*` 改成 `IDLE_A`」来消掉这个姿势**：原版 `IDLE_COMBAT_A~D` 本来就该指向专门的战斗待机姿势（`AT_Crew_AttackPoseA~D`、`Artillery_CombatA~D`）。错的是多出来的基础层，不是战斗待机姿势本身。本项目第一版修复就走错过这个方向，幸好 `--set` 未落盘。

**验收（2026-11-05 15:01）**：时间线 40/41 → 39/39，BREATHING 残留 0，全部时长仍与 `.anm` 一致，23 条触发点逐条不变；cook 后 `units/*.blp` 触发点命中数不变（VoicePool 1 / Ult 2 / Step 8 / Death 1 / Hit 8）。

---

## 3. DSG 改槽位：已否决

**【核验】** 完整单变量实验（产物字节级）：

| 改动 | 男 `units/rover.blp` md5 |
|---|---|
| 基线（`potential_any_graph` + 四槽探针） | `1f06f9fe…`（前 8 位） |
| 换自建 `RoverProbeDSG`（把 ATTACK 状态的动画图节点从 `ATTACK_A` 改成 `ATTACK_1`） | **同 md5，零字节变化** |
| 换成不存在的 `ZZZ_NoSuchDSG` | `5883c431…`，且 cooker.log 报 `IO-ERROR … <工程>/DSGs/ZZZ_NoSuchDSG.dsg` + `Error/Unit_UnitError` |
| 只改 `.ast` 一个触发点 | `e94e3bb4…`（证明 cook 确实读 `.ast`、无缓存） |

结论：`m_dsgName` 字段**会被读**（写错名字立刻报错并出 Error 资产），但**DSG 图内容不进产物**——改 DSG 图不会改变引擎请求哪个状态，救不回死槽。

> ⚠ 与 §2.3 不矛盾：这里否决的是「**改工程里的 DSG 图**来救死槽」；`m_dsgName` 指向的原版内置 DSG 在运行时**照常生效**，其双层结构照样会请求 `BREATHING_*`。改不动它，只能改 `.ast` 槽位去配合它。

顺带查明的两条事实：

- **【核验】** DSG 源文件的查找路径是 **`<工程根>/DSGs/<名字>.dsg`**，不是 SDK pantry；
- **【核验】** `.dsg` 只是清单（Name + 动画槽/时间线槽 + 指向 `.dsgxml` 的路径），带分支语义的是 `.dsgxml`，而后者被 cook 丢弃。

> 参考模组 SkyCastle（工坊 3811836710）的 `DSGs/` 是**空目录**，全包 0 个 `.dsg`，`m_dsgName` 全部是原版现成的——它没有用 DSG，不能当反例。

---

## 4. 加权语音池（本工程在用的方案）

### 4.1 原理

**【核验】** Wwise 2015.1 的 `RandomSequenceContainer` 只有均匀随机，子项没有权重字段。要「语气词占大部分、技能/大招占小部分」，**用槽位数量当权重**：

```
父容器（随机，MaxSoundPerInstance=1）
  ├─ 语气词组 × 16   → 16/20 = 80%
  ├─ 技能组   ×  3   →  3/20 = 15%
  └─ 大招组   ×  1   →  1/20 =  5%
```

总槽数取 20 这类「能被常见百分比整除」的数，比 30 更好调：80/15/5 一步到位，
要改比例时只动分子，不用重新算小数。

单条命中率 = 组占比 ÷ 组内条数。想更稀有就减少该组槽数（例如 1/60 ≈ 1.7%）。
组内条目用**轮转分块**（第 k 条进第 k mod n 块），避免同一块里全是同一批素材。

### 4.2 已交付参数（2026-11-05 16:00 定稿版）

| 项 | 男漂 | 女漂 |
|---|---|---|
| 事件 | `Play_RoverMale_VoicePool` | `Play_RoverFemale_VoicePool` |
| 父容器 | `RoverMale_VoicePool` | `RoverFemale_VoicePool` |
| 语气词（`CH_*`） | 120 条（四形态全量，静音已剔） | 114 条 |
| 技能（`SK_*`） | 43 条 | 43 条 |
| 大招（`UL_*`） | 18 条 | 18 条 |
| 槽位 / 概率 | 16 / 3 / 1 → **80% / 15% / 5%** | 同左 |
| HERO 事件 | `Play_RoverMale_Ult` → `..._UL_G01` | `Play_RoverFemale_Ult` → 同构 |
| 脚步事件 | `Play_RoverStep_01` | **`Play_RoverFemale_Step_01`**（§5.2 唯一化） |
| 选中事件 | `Unit_Selected_ROVER_QYQXP` | 不定义（由男 bank 提供） |
| bank 媒体总数 | 185 | 178 |
| bank 体积 | 2,996,299 B | 2,545,238 B |

命名：`Play_<性别>_CH_01…`（女漂为三位 `CH_001…`）/ `_SK_01…` / `_UL_01…`。

**四形态是"有意保留"，不是漏筛**：`dark / thunder / wind` 是同一角色的属性形态（见 §4.5），
听感上是同一个人的不同演法，混装能被接受；真正要防的是**混进其他角色**。
本项目先按"只留本尊"做过一版（27/21 条），试听后判定语气词数量太少、重复感强，遂改回全量。
结论：**形态要不要留属于听感取舍，由用户定；先把数量、重复率、单条概率算给用户看。**

> 历史版本（同日 13:20）为 27/21 条 + 3 条大招、96%/4%，已废弃，仅作对照。


### 4.3 两个必须知道的坑

1. **评估版 Wwise 每 bank ≤200 媒体项**（`SKILL.md` 铁律 4）。
   本项目踩到过：`Fatal Error … Maximum number of media items exceeded (209 out of the 200 permitted)`。
   209 = 新池 181 + **整工作单元引用**带进来的 28 个旧对象。解决办法不是砍素材，见下一条。

2. **`SoundBank` 里不要出现「整个工作单元」的 `ObjectRef`**。
   例：`<ObjectRef Name="RoverUnitAudio_Speech" WorkUnitID="{048AE7AB-…}"/>` 这一条会把该 WU 下
   **所有**Sound/容器一起拉进 bank（含已废弃的旧池、探针、胜利音），既超媒体上限又白白涨体积。
   只保留**事件级** `ObjectRef`，事件可达的对象自然会被带入。删掉这条后：209 → 186，一次生成通过。

   判据：`bank 媒体数 == 事件可达媒体数`；多出来的就是被 WU 引用带进来的。

3. **`--force` 重建事件后，bank 的 `ObjectRef` GUID 会失配**（本项目 13:20 踩到）。
   `ObjectRef` 里同时写着 `Name` 和 `ID`（事件的 GUID）。重建事件会生成新 GUID，而 `ObjectRef` 仍指向旧 GUID
   → **Wwise 打包时静默丢弃该事件**：bank 正常生成、`media N` 也正常，但事件清单里就是没有它。
   症状：`unit_bank_chain.py` 输出里找不到 `Play_X_VoicePool` 行，`.ast` 挂的触发点自然永远不响。
   `unit_voice_mixer.py` 现在会自动比对并把 `ObjectRef` 的 GUID 改成事件的实际 GUID（输出 `修正 ObjectRef GUID N 个`）。
   **验收必须看事件清单，不能只看 `media N`。**

### 4.5 素材来源陷阱：同一角色的「属性形态」音色完全不同

**【实测】** 鸣潮的解包目录按**属性形态分轨**，同一角色的不同形态是不同录音演法：

```
zh_vo_<形态>_<角色>_atkXX_0N.wav
   ├─ 无前缀    ← 本尊常规形态（数量最少）
   ├─ dark_     ← 暗主形态：低沉、带混响感
   ├─ thunder_  ← 雷形态：高亢、带气声（_tone 后缀多为纯气息，不成句）
   └─ wind_     ← 风形态：清亮
```

本项目 `01_普攻 / 02_重击 / 04_技能` 三个目录里，**本尊只占 3~30%，其余全是形态变体**（女漂 123 条里本尊仅 24 条；`04_技能` 61 条里本尊只有 3 条）。

**先分清两件事，别一看到数量多就砍：**

| 症状 | 判定 | 处理 |
|---|---|---|
| 听到**别的角色**的声音 | 素材混入（换角色目录、切人语音） | 必剔 |
| 同一角色换演法，音色/气息/混响跳变 | 形态变体 | **听感取舍**，问用户 |
| 出现 −91 dB 全零、长度异常 | 占位/坏素材 | 必剔（mixer 自动） |

本项目实测走过一遍弯路：13:05 版全量混装（女 123 条），用户反馈"像换了个角色、质量参差"→ 13:20 砍到只留本尊（21 条）→ 试听后**又嫌语气词太少、重复感强** → 14:12 全量加回（114 条）。
根因不是素材错，而是**单条概率**：21 条 × 100% 时单条 4.8%，同几句反复出现；114 条 × 80% 时单条 0.7%，重复感立刻消失。

处理原则：

1. **必剔**：`character_switch_*`（切人系统语音，语义不是战斗）、静音占位、明显是其他角色的分轨；
2. **可留**：同角色属性形态（`dark / thunder / wind`），但要接受音色在四种演法间跳变；
3. `_tone` 后缀多为纯气息/拟声，混在技能层没问题，混在语气词层会听不出内容差异——本项目保留（占技能层 22/43）；
4. **决定权交给用户**：把「条数 / 单条概率 / 形态分布」摆出来，不要替用户砍。

`unit_voice_mixer.py` 没有内置形态过滤（命名规则因游戏而异），**建 spec 时就按前缀筛好**；静音素材它会在渲染时自动剔除（本项目两工程各剔 9 条：`01_普攻` 3 条、`03_弹反` 3 条、`07_其他` 3 条）。

### 4.6 HERO / 终结技槽：专用事件复用组容器（零媒体增量）

**【实测】** `HERO_A / HERO_1` 不是死槽（见 §2），会偶发被请求。想要「这槽一响就必是大招台词」，
做法不是再建一批 Sound，而是**让新事件直接指向常态池里的大招组容器**：

```
Play_X_VoicePool ─→ RoverX_VoicePool ─┬─ CH_G01..G16
                                       ├─ SK_G01..G03
                                       └─ UL_G01  ←── Play_X_Ult（HERO 事件也指这里）
```

- 同一容器被两个事件引用，Wwise 里只有**一份对象、一份媒体**（本项目 Ult 事件 `sounds 18 / media 18`，
  bank 媒体总数没变，仍 185/179）。
- 事件只是 Play Action + ObjectRef，指向任意容器都合法；不必是顶层。
- spec 写法：`"hero": {"event": "Play_X_Ult", "group": "UL"}`，mixer 自动找 `..._UL_G01` 建事件并登记 bank。
- **该组必须 `slots: 1`**（组内只一个容器）才能直接指向；多容器需另建包装容器，脚本会报错提示。
- `--force` 重建时 mixer 会一并 purge 同名 HERO 事件，避免留下指向已删容器的旧事件。

配合要求：**HERO 时间线时长必须与剪辑一致，不能为了放下长语音去拉长**（见 §2.2，2026-11-05 已用回滚实测证伪了「拉长只是状态停留」的说法）。大招台词最长 2.74 s，而 `ATTACK_A` 男 2.200 / 女 2.667，尾巴会截掉 0.1~0.5 s——接受截尾，或把超长条目压到剪辑长度以内。


### 4.4 生成与验收

```bash
S=<skill>/scripts
# 建池（渲染媒体 + 建 Sound/容器/事件 + bank 登记）
#   首次用 --unregister 摘旧事件；重建同名池直接 --force（会删同名容器/事件再建）
python $S/unit_voice_mixer.py spec.json --force --unregister Play_X_Atk_01,Play_X_Probe_A
# 可选：彻底清掉旧对象（孤儿 Sound/事件不删会白白占媒体名额）
python $S/unit_wwise_purge.py "<工程>/Actor-Mixer Hierarchy/X.wwu" --match "^Play_X_(Atk|Ult)_\d+$" --match "^RoverX_Victory_Random$"
# 触发点：先改时长再改条目（时长改动会挪字符偏移，脚本已内置这个顺序）
python $S/unit_ast_triggers.py <单位>.ast --dur dur.json --set map.json
# 生成 bank
python $S/wwise_wire.py <工程目录> --generate <Bank名>
# 链路验收（事件 → 容器 → 媒体）⚠ 必须确认目标事件在清单里
python $S/unit_bank_chain.py <Bank名>.bnk --xml <Bank名>.xml
# 触发点验收（⚠ 只认 units/*.blp）
python $S/unit_blp_check.py <mod>/Platforms/Windows/BLPs/units/<单位>.blp --names Play_X_VoicePool,Play_X_Ult
```

`unit_bank_chain.py` 对**嵌套**随机容器的 `sounds/media` 列会显示 0（它只展开一层），
此时以 bank 头的 `media N` 与 `unit_blp_check` 为准，别误判成空容器。

---

## 5. 验收：认哪个文件

**【核验】** `.ast` 的触发点烤进的是**单位资产 BLP**：

```
<mod>/Platforms/Windows/BLPs/units/<单位>.blp        ← 触发点在这里（FNV1a-32 小端）
<mod>/Platforms/Windows/BLPs/SHARED_DATA/ANIMATION_* ← 裸动画剪辑，不含任何触发点
```

踩过的坑：拿 `SHARED_DATA/ANIMATION_*` 去查哈希，命中数恒为 0，误判成「cook 没吃到新 ast」。
反证方法：把 `.ast` 换成无触发点版本重新 cook，`SHARED_DATA` 产物**逐字节相同**（0 差异），
而 `units/*.blp` 会变。`unit_blp_check.py` 的 docstring 已写明这条。

**cook 命令**：`python <skills>/civ6-modding/tools/cook_assets.py <工程根> --quiet`，
跑完看 `units/*.blp` 的 mtime 与哈希命中数。

### 5.1 部署铁律：bank 必须同时落三处，且验收只看 Mods 副本

**【实测】** 2026-11-05 15:30，游戏高频战斗闪退，根因是**女漂 Mods 副本里的 `.bnk` 还是 10:12 的旧版**
（229,819 B，事件表只有 `Atk_01/02 / Probe_A~D / Victory / Step / Selected`），
而当前 `.blp` 里请求的是 `Play_RoverFemale_VoicePool` / `Play_RoverFemale_Ult` —— 这两个事件在旧 bank 里
**根本不存在**。每次女漂攻击都 Post 一个不存在的事件，是这次 CTD 最直接的触发点。
当时 `workspace/tmp/bank_female2/GeneratedSoundBanks/Windows/` 里已是 14:10 的新版（2,698,333 B），
但没进 Mods 副本 → **只验工作目录会得到假阳性**。

`wwise_wire.py --generate` 只写到 `workspace/tmp/bank_*/GeneratedSoundBanks/Windows/`，
**不会自动部署**；`cook_assets.py` 只同步 ArtDefs，也**不会**把新 bank 带过去。
而 ModBuddy / 发布流程可能反过来用**源工程**的 `Platforms/Windows/Audio/` 覆盖 Mods 副本
（本工程 15:25 就发生过一次，女 BLP mtime 15:25:14 而男的停在 15:01:59）。

所以生成后必须把 `.bnk / .txt / .xml` 三件套**双写**到两处，共三处保持 md5 一致：

```
workspace/tmp/bank_*/GeneratedSoundBanks/Windows/   ← 生成源（唯一真源）
<工程根>/Platforms/Windows/Audio/                    ← 源工程（防后续构建覆盖）
<My Games>/Mods/<Mod>/Platforms/Windows/Audio/      ← 游戏实际读取 ★ 验收只认这里
```

验收命令（`unit_bank_chain.py` 和 `unit_blp_check.py` 都必须指向 Mods 副本）：

```bash
for ext in bnk txt xml; do
  cp -f "$GEN/$BANK.$ext" "$SRC_AUDIO/$BANK.$ext"
  cp -f "$GEN/$BANK.$ext" "$MOD_AUDIO/$BANK.$ext"
done
md5sum "$GEN/$BANK.bnk" "$SRC_AUDIO/$BANK.bnk" "$MOD_AUDIO/$BANK.bnk"   # 三个必须相同
python $S/unit_bank_chain.py "$MOD_AUDIO/$BANK.bnk" --xml "$MOD_AUDIO/$BANK.xml"  # 事件清单含 VoicePool/Ult
```

**改完 bank 必须重启游戏**（SoundBank 已加载进内存，热替换磁盘文件对当前进程无效）。

三处 md5 一致只是前提；多个 mod 变体共存还要过 §5.2 的 ShortID 唯一化。

### 5.2 多 mod 同时加载：ShortID 必须全域唯一（本次 CTD 主因）

**【核验 + 实测】** 2026-11-05 16:00。Wwise 的 32 位 ID 是**全局表**：两个都挂 `[InGame]` 的 bank
若从同一模板复制，ID 成套相同但内容不同 → 后加载者覆盖前者索引，卸载时可能连带释放 → 悬空引用
→ 高频战斗 / 后台待机 CTD。「只启用男漂稳定」＝那时只加载了一个 bank。

| 撞号类型 | 修复前 | 修复后 |
|---|---|---|
| HIRC 对象 ID | 113 个相同（Sound / 容器 / Action / ActorMixer） | 3 个（仅模板锚点） |
| 媒体 ID（`DIDX`） | 88 个 | 0 |
| Event ID | 2 个（`Play_RoverStep_01`、`Unit_Selected_ROVER_QYQXP`） | 0 |

**两类 ID，规则不同**（`mechanism.md` §9 / §10）：

| 类别 | 编号来源 | 唯一化手段 |
|---|---|---|
| `.ast` 触发点 `m_FXName`；引擎约定名 `Unit_Selected_<UnitType>`；ArtDef `Audio/XrefName` 派生名 | **Event ID = FNV-1(小写事件名)**，引擎按名字重算，写死无效 | 只能改事件名 / 只留一份。`.ast` 名任意改（改完重新 cook）；引擎约定名与 XrefName **不能改** |
| Sound / AudioFileSource / 容器 / Action / ActorMixer | 显式 `ShortID` 或 GUID 推导 | 按 `<mod 目录名>/<资产名>` **命名派生**（§10），`unit_bank_resign.py --project`，可 `--check` 复算 |

⚠ **别给 Event 的哈希加工程名盐**：引擎只按事件名哈希，加盐就 Post 不到。事件侧的正确做法是
把 mod 名写进**事件名本身**（`Play_RoverFemale_Step_01`），让引擎侧的哈希天然错开。

**本工程定稿**：男漂是单位提供者，保留 `Play_RoverStep_01` 与 `Unit_Selected_ROVER_QYQXP`；
女漂脚步改名、删掉重复的选中事件（两个 mod 都是 `UNIT_ROVER_QYQXP`，引擎只 Post 一次）。
女工程按 `--project UnitRoverFemale` 命名派生重签 441 个对象，兜底避让男 bank + 原版 18 个 bank 的
26,275 个 ID。验收：两 bank 交集只剩 3 个模板锚点（`Stop_Leader_Speech` 寻址目标，同模板 mod 共享，
见 `mechanism.md` §10.3），事件 ID 交集 0，与 Mods 里其它 27 个 bank 零冲突。

```bash
S=<skill>/scripts
python $S/unit_bank_resign.py <女工程> --project UnitRoverFemale \
  --exclude-bank <男 bank.bnk> \
  --exclude-glob "<游戏>/Base/Platforms/Windows/audio/*.bnk" \
  --rename-event "Play_RoverStep_01:Play_RoverFemale_Step_01" \
  --drop-event "Unit_Selected_ROVER_QYQXP"
# 同样参数加 --check 可复算校验；再 --generate，按 §5.1 部署三处，重启游戏
```
`.ast` 里 11 处脚步事件同步改名并重新 cook，否则 BLP 里的哈希不会变。

**【核验】原版参照**：`DLC/ScoutCat/` 零音频文件（modinfo 也无 `UpdateAudio`），猫叫事件
`ScoutCat_Dodge` / `ScoutCat_RunBell` 与 22 条媒体都在原版 `Unit_Bank_3D.bnk`，靠 `Units.artdef` 的
`Audio/XrefName="ScoutCat"` 路由，DLC 的 `units.blp` 里仍有这两个名字的 FNV1a 哈希。
官方做法是「事件并入共享 bank，不新增 bank」，从根上避开撞号；本工程两 mod 的 XrefName 均为空，
只能自己保证全局唯一。

---

## 6. 响度

| 用途 | 目标 | 依据 |
|---|---|---|
| 语气词 / 技能 / 大招 | **-21 LUFS**（单声道 48 kHz） | **【实测】** 与既有语音一致，实机不炸不糊 |
| 脚步 | **-34 LUFS**（RMS ≈ -31.9 dBFS） | **【实测】** 原版 `Footstep_Basic_3D` 媒体 RMS −22.9 dBFS 时「比原版响很多」，重渲染到 -34 LUFS 后通过 |

`.ast` 里脚步的触发点用 **0.217 s / 0.55 s** 两个（对应 `RUN_A` 0.767 s 内的两次落地）；
起步/停步类（`RUN_START` / `RUN_COMBAT_START` / `RUN_STOP` / `RUN_STOP_B~D` / `RUN_COMBAT_STOP`）
各给**一个**（起步 0.15 s、停步 0.30 s），否则起步与刹步会「滑步无声」。

---

## 7. 脚本清单（本节相关）

| 脚本 | 职责 |
|---|---|
| `unit_ast_triggers.py` | 读/清/写 `.ast` 触发点与时间线时长：`--list` / `--clear-all [--keep RUN_A,…]` / `--set map.json` / `--add` / `--dur dur.json` |
| `unit_ast_anim.py` | `.ast` 槽位动画映射：`--list [--animdir]` 逐条比对时间线时长与 `.anm`；`--set map.json` 改槽位指向的动画并同步绑定表；**`--drop SLOT…` 整槽移除**（三处定义 + XML 校验）。排「两次攻击间固定怪姿势」用 `--drop BREATHING_*`（§2.3） |
| `unit_voice_pool.py` | 批量渲染媒体 + 建**单声**Sound/Event + bank 登记（spec 驱动，幂等） |
| `unit_voice_mixer.py` | **一个事件、多档加权池**（嵌套随机容器法），含静音剔除、`--force` 重建、`ObjectRef` GUID 校正、`hero` 专用事件（复用组容器，零媒体） |
| `unit_wwise_purge.py` | 按名字正则从 `.wwu` 删整块对象（Sound/容器/Event），清旧池残留用 |
| `unit_bank_chain.py` | 解析 bank HIRC：事件 → 目标 → 媒体，`in_bank` 判定 |
| `unit_bank_resign.py` | **多 mod 共存**：按 `<mod目录名>/<资产名>` 命名派生全对象 `ShortID`（复用 `voice_shortid.compute`），`--check` 复算、`--exclude-bank/-glob` 兜底避让；`--rename-event` / `--drop-event` 处理同名事件（§5.2） |
| `unit_ult_tighten.py` | **大招语音收紧**：去首尾空白 + 压缩内部死寂 + 轻微 `atempo`，保证不截尾地塞进时间线（§2.2a） |
| `unit_blp_check.py` | 在 `units/*.blp` 里数 FNV1a 命中数 = 触发点是否真的烤进去了 |

---

## 8. 未解决 / 下一步

- **击杀语音**：**【推测】** 最稳的是 Lua `Events.UnitKilledInCombat` → `UI.PlaySound`（2D，不依赖槽位）。同引擎活证据：参考模组 SkyCastle 的**选中音**就是纯 Lua `UI.PlaySound` + `Banks.ini [Global]` + `UI.LoadSoundBankGroup(0)`，实机可闻。
- **VICTORY 的门控条件**：**【推测】** 可能与「是否击杀 / 是否首次 / 镜头是否在附近」有关，文件里查不到，只能实机二分。
- **`.bhv` 路线**：**【推测】** 把绑定搬进独立 `.bhv` 并用 `m_behaviorInstances` 引用，理论上与 `.ast` 等价；**未做过对照实验**，不保证能点亮死槽。

---

## 9. 复现清单（给新单位配语音）

1. 确认单位资产：`<mod>/Platforms/Windows/BLPs/units/<单位>.blp` 存在且由 cook 产出；
2. 跑一次**探针实验**（4 条时长差异明显的音挂候选槽），实机确认哪条槽真的活——**不要假设**；
3. 只给活槽挂事件；`HERO_A/HERO_1` 属于活槽，挂**同一个随机池**，不要挂单条固定语音；`VICTORY/ACTION_1` 不挂；
4. 把 `HERO_A/HERO_1/VICTORY/ACTION_1` 的时间线动画与 `m_fDuration` 一并对齐到 `*_ATTACK_A`（§2.1），`--list` 复核；**确认 `.ast` 里没有 `BREATHING_A` / `BREATHING_COMBAT_A` 槽**，有就 `--drop` 掉，否则战斗待机会双份叠加出固定怪姿势（§2.3）；
5. **筛素材**：只留本尊形态（无 `dark_/thunder_/wind_/character_switch`），`_tone` 优先弃；宁缺毋滥（§4.5）；
6. 语音池用 `unit_voice_mixer.py` 建，权重按「槽数比」定；
7. **若同一个单位有多个 mod 变体**：先按 §5.2 做 ID 唯一化（触发点事件改名 + `--project <mod目录名>` 命名派生重签并 `--check` + 约定名只留一份），否则两个 `[InGame]` bank 会撞号闪退；
8. `wwise_wire.py --generate` 生成，`unit_bank_chain.py` 验链路（**确认目标事件在清单里**）；按 §5.1 把三件套部署三处，验收只认 Mods 副本；
9. `cook_assets.py` 烘焙，`unit_blp_check.py` 验触发点（`VoicePool` 命中数应 = 挂了它的槽数）；
10. 实机听：先确认**每类都出声**，再确认**比例符合设计**（打 30 下数一数大招出现几次），最后确认**没有偶发的固定台词/固定动作**、大招不截尾。
