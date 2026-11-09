# 类 6 —— Icon 引用规范

> 跨类集合（语料 2,579 条含标记，`HasIcon=1`）。
> 权威图标名表：`reference/civ6-icon-tags.sql`（5,056 个 `[ICON_*]`，社区整理，随 skill 分发）
> **名词↔Icon 映射表**：`reference/icon_noun_map.tsv`（主表）+ `icon_noun_map_versioned.tsv`（版本专属）+ `icon_noun_map.json`（iconify 兼容），由官方语料全量挖掘生成
> 校验器：`civ6-modding/art/iconify_text.py`（`--audit`/`--check`/`--write`）+ `scripts/check_text_refs.py` + `scripts/analyze_icon_nouns.py --check`（名词搭配）

## 1. 图标标记语法

```
[ICON_<Name>]        行内图标（如 [ICON_Science] 科技值）
[ICON_BULLET]        列表符号（bullet）
[ICON_<Name>_LARGE]  大图标变体（如 [ICON_BOMBARD_LARGE]）
```

**★ 静默失败铁律**：图标名写错**不报错、只是不显示**（游戏里留空）。
所以"批量加图标"必须配"名称校验"，否则等于批量制造静默失败。

### 大小写
官方文本里大小写**并存**（`[ICON_Production]` 292 次 vs `[ICON_PRODUCTION]` 75 次；
`[ICON_Bullet]` 100 次 vs `[ICON_BULLET]` 83 次）——两者都能渲染（查找**不区分大小写**）。
- 权威表 `civ6-icon-tags.sql` 用**全大写**登记；
- **写作建议**：与同类官方文本保持一致（产出类官方常用大写，如 `[ICON_CULTURE]`；但 `[ICON_Gold]`/`[ICON_Faith]` 官方驼峰也很常见）——**只要名字在权威表里能查到即可**，不必强求单一大小写。

## 2. 名词↔Icon 映射表（写作取名 + 校验白名单，权威）

文明6 文本名词与图标是**固定映射**：每个名词如有图标，一般只有唯一对应图标；一个图标则
可能对应复数名词（如 `[ICON_Citizen]` ↔ 人口/公民）。本 skill 用官方语料全量挖掘出这张表：

| 文件 | 内容 | 用途 |
|---|---|---|
| `reference/icon_noun_map.tsv` | **主表**：原版+风云变幻**通用**图标 ↔ 名词（图标、类别、首选名词、别名名词、搭配频次、尺寸变体） | 写作时按名词查图标；校验的白名单 |
| `reference/icon_noun_map_versioned.tsv` | **版本专属表**：仅原版 / 仅风云变幻可用的图标，多一列**出处**限制引用 | 引用前必须核对出处 |
| `reference/icon_noun_map.json` | 名词→图标名（`{"名词": "IconName"}`） | 喂给 `iconify_text.py --map` 全量官方映射 |
| `scripts/analyze_icon_nouns.py` | 生成器 + 校验器（`--emit-candidates` / `--check`） | 表格可再生成；名词搭配校验 |

### 写作方向（名词→Icon）

- 给文本补图标时，名词对应的图标**以表内为准**；表里没有的名词 → 该名词官方不配图标，
  不要自创搭配（项目自造图标不纳入本表，另查工程 Icons XML）。
- 每个名词的唯一指向也可直接用 JSON 查；或整表交给补图标工具：

```bash
# 用全量官方映射（覆盖内置 60 词小表）跑补图标预演
python <civ6-modding>\art\iconify_text.py <工程根> --check \
    --map "<本skill>\reference\icon_noun_map.json"
```

### 校验方向（Icon→名词，白名单制）

- 官方图标后面跟的名词**必须是表内已有映射**，不允许给一个官方图标配表外新名词
  （如 `[ICON_Gold] 玉石` ✘——金币图标只配 金币/黄金）。
- 校验按「图标后紧跟的汉字串的最长表内前缀」判定，后缀语（`生产力**加成**`、`贸易路线**容量**`）
  合法；符号类图标（`Bullet`/`CheckFail`/`GOSSIP_*` 等）不配名词，跳过检查；
  表外图标（含项目自造）不校验。

```bash
python scripts/analyze_icon_nouns.py --check <工程文本目录或文件...>
# FAIL 两类：① 图标后接名词不在表内  ② 名词写在图标前（顺序违规，见 §4）
# 退出码：0 通过 / 1 有问题 —— 可接 CI，与 iconify --audit、check_text_refs.py 三件套同跑
```

### 版本专属图标的引用限制

- **仅原版**：风云变幻环境已无对应内容 → 工程**禁止引用**（`--check` 直接 FAIL）。
- **仅风云变幻**（电力、不满、总督点数、世界议会奖励、GOSSIP、黑暗/英雄时代等资料片内容）：
  目标环境为风云变幻时可正常引用；若面向纯原版环境则不可引用。
- 本语料口径下「仅原版」当前为空（风云变幻有效文本保留了原版用到的全部图标）；
  判定脚本按 base+DLC 口径 vs 全量口径重算，规则见脚本头注释。

### 常用图标速查（节选自主表，全量以 `icon_noun_map.tsv` 为准）

| 产出 | 标记 | 类别 | 标记 |
|---|---|---|---|
| 战斗力 | `[ICON_Strength]` | 首都 | `[ICON_Capital]` |
| 金币 | `[ICON_Gold]` | 贸易路线 | `[ICON_TradeRoute]` |
| 生产力 | `[ICON_Production]` | 移动力 | `[ICON_Movement]` |
| 信仰值 | `[ICON_Faith]` | 公民/人口 | `[ICON_Citizen]` |
| 文化值 | `[ICON_Culture]` | 食物/粮食 | `[ICON_Food]` |
| 科技值 | `[ICON_Science]` | 旅游业绩 | `[ICON_Tourism]` |
| 伟人 | `[ICON_GreatPerson]` | 宜居度 | `[ICON_Amenities]` |
| 住房 | `[ICON_Housing]` | 使者 | `[ICON_Envoy]` |
| 列表符号 | `[ICON_Bullet]` | 外交支持 | `[ICON_Favor]` |

## 3. 其它文本标记（与图标同属「不可破坏的原始标记」）

| 标记 | 含义 | 范式 |
|---|---|---|
| `[COLOR_<C>]…[ENDCOLOR]` | 着色区间（红/绿/浮金等） | `[COLOR_RED]-17 [ICON_Bombard][ENDCOLOR] 轰炸攻击力。` |
| `[COLOR_FLOAT_GOLD]…[ENDCOLOR]` | 浮金（数值动效色） | `[COLOR_FLOAT_GOLD]+{1_Num} [ICON_Gold][ENDCOLOR]` |
| `[NEWLINE]` | 强制换行 | 多段能力描述、议程解释 |
| `{LOC_x}` | 内嵌另一条本地化文本 | `{LOC_ERA_TT_HAVE_GOLDEN_AGE_EFFECT}` |
| `{1_Arg}` / `{1_num}` / `{Amount}` | 引擎/Modifier 传参占位 | 见类1/类5 |

**规则**：这些标记在翻译/改写时**必须原样保留**，位置、大小写（对大小写敏感者如 `ENDCOLOR`）都不得改动。

## 4. 常见错误

| 错误 | 后果 | 正确 |
|---|---|---|
| 图标名拼错（`[ICON_Scicence]`） | **静默**不显示 | 对照 `civ6-icon-tags.sql` 校验 |
| 图标配了表外新名词（`[ICON_Gold] 玉石`） | 名词搭配校验 FAIL；映射关系走样 | 对照 `icon_noun_map.tsv` 选名词 |
| 名词写在图标前（`粮食[ICON_Food]`） | 违反官方顺序惯例 | `数值 + 空格 + [ICON_x] + 空格 + 名词` |
| 漏写 `[ENDCOLOR]` | 其后整段被着色 | 成对书写 |
| 把 `[ICON_Culture]` 写成 `[Icon_Culture]` | 前缀错 → 不解析 | 前缀必须 `ICON_` |
| 中文与图标间缺空格 | 官方惯例留空格（`+1 [ICON_Faith] 信仰值`） | 数值/图标左右留空格 |
| 翻译时把 `{1_Arg}` 译掉 | 传参失效 | 占位符不译 |
| 引用了版本专属图标却未核对出处 | 面向环境不符时图标/内容缺失 | 查 `icon_noun_map_versioned.tsv` 出处列 |

## 5. 校验（必跑）

```bash
# 审计文本里所有 [ICON_x] 是否可解析（只读）
python <civ6-modding>\art\iconify_text.py <工程根> --audit
# 预演自动补图标（不写盘）；--map 换用全量官方名词映射
python <civ6-modding>\art\iconify_text.py <工程根> --check \
    --map "<本skill>\reference\icon_noun_map.json"
# 双向引用体检：图标正向 + {LOC_x} 反向 + Config 孤儿 tag
python <civ6-modding>\scripts\check_text_refs.py <工程根>
# 名词搭配白名单校验（Icon→名词）+ 版本专属出处检查
python scripts/analyze_icon_nouns.py --check <工程根>
```

## 6. 校验清单

- [ ] 每个 `[ICON_x]` 都能在 `civ6-icon-tags.sql` 或工程 Icons 里解析到
- [ ] 每个官方图标后接的名词都在 `icon_noun_map.tsv` 白名单内
- [ ] 版本专属图标的出处与工程目标环境相符（仅原版一律禁用）
- [ ] `[COLOR_*]` 与 `[ENDCOLOR]` 成对
- [ ] `{LOC_x}` / `{1_Arg}` 占位符原样保留
- [ ] 图标与前后文留空格
- [ ] `iconify_text.py --audit` + `check_text_refs.py` + `analyze_icon_nouns.py --check` 均 0 问题
