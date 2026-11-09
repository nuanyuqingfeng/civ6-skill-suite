# 鸣潮（Wuthering Waves）全量音频解包 — 命名对照与数据口径

> 本文件是鸣潮音频解包任务的命名真源：命名规则、目录树结构、索引 schema、已知限制均以此为准。
> 数据口径来自 2026-10-27 对 Client 3.7.0（Resource 3.7.16，简体中文语音包）的一次完整解包实践
> （100,787 个 wem，与包内总量一致）。新版本解包时版本号、档案数、文件数按当次实测更新。

## 数据源与工具链

| 环节 | 工具 / 路径 |
|------|------------|
| 游戏本体 | `F:\Wuthering Waves`（以当次安装版本为准，解包前先确认 Client / Resource 版本号） |
| 包体挂载 | FModel MCP，`GAME_WutheringWaves` 档案，官方 AES / Oodle 密钥链（3.7 时为 419 个挂载档案） |
| 批量扫描 / 导出 | `scripts/cue4parse_scan/`（C# CueScan，CUE4Parse 直连，密钥走本机 FModel 设置；万级资产时替代 MCP 逐个调用） |
| 音频解码 | `G:\vgmstream-dd\extracted\vgmstream-cli.exe`，Wwise wem → PCM WAV 48kHz；批量转码用 `scripts/wem_transcode.py` |
| 鸣潮专属脚本 | Ragunna_Pack 工程 `workspace/_tools/wuwa_audio/`（归类 / 索引 / 对账全流程与关键口径，见其 README） |
| MCP 配置 | `E:\SoftWares\FModelMcp\config.json`（输入根、密钥由 FModel 本机设置维护） |

## 命名规则

### 事件名 = 文件名

- 普通事件：文件名即官方 Wwise 事件名，如 `music_scene_hundunzhijian_yueguishu.wav`。
- 多媒体事件：一个事件引用多个媒体时追加序号后缀 `__1`、`__2`，如 `amb_emit_fire_home__1.wav`。

### 语音保留官方全名

- ExternalSource 文件名即运行时触发名，解包时原样保留，如 `zh_vo_Character_chun_25_15.wav`。
- `zh_` 前缀 = 简体中文语音；`gl_` 前缀 = 全局无语言差异（呼吸、拟声等）。
- 语言覆盖取决于本机安装的语音包（3.7 时仅 zh + gl）。

### 目录树

```text
BGM\<类别>\                     类别取事件名第二段：scene / battle / dungeon / function /
                                interact / role / rouge / phonograph_albums / common 等；
                                少量以地图事件形式挂接的音乐按官方 DebugName 目录归档
SFX\<二级分类>\                 amb / compose / da_fx / elite / interact / map / mon / play /
                                plot / role / seq / sequence / sfx / ui / vision
Voice\<语言>\vo_<类别>\<主体>\  vo_Character 的主体为角色内部名；其余类别按任务 / 活动归档
Unreferenced\                   无事件引用的孤儿媒体 + PLUG 特殊文件
```

### vo_Character 主体内部名对照

内部名即官方数据使用的角色标识（`index_voice.csv` 的 `subject` 列），目录名照抄。3.7 观察值：

| 内部名 | 角色 | 内部名 | 角色 |
|--------|------|--------|------|
| chun | 椿 | LingYang | 凌阳 |
| Brant | 布兰特 | Rococo | 洛可可 |
| Cantarella | 坎特蕾拉 | YinLin | 吟霖 |
| ChangLi | 长离 | Zani | 赞妮 |
| Encore | 安可 | ZheZhi | 折枝 |
| JiYan | 忌炎 | jinhsi | 今汐 |
| yangyang | 秧秧 | | |

> 官方完整内部名表存于 ConfigDB flatbuffer，解包库不内置中文名映射；
> 上表为 3.7 目录观察值加常见对照。新版本出现新内部名时按其拼音语义对照，不臆造。

### Voice 语言内的 vo_<类别> 清单（3.7 观察值）

zh 侧 41 类：vo_ActivityRoleTrial、vo_BYSTMP、vo_Character、vo_Chengxiaoshan、vo_CommonVoice、
vo_DYHD、vo_Event、vo_Flow、vo_GNNPC、vo_GNNPCXJXY、vo_GondolaRideSharingPlot、vo_Guide、vo_HD、
vo_HHAXST、vo_HRQDGNQST、vo_HRT、vo_Heihaian、vo_Huanglong、vo_HuanglongM1、vo_HuanglongXZ、
vo_LHYSTTH、vo_Main、vo_Motorcycle、vo_NPC、vo_POI、vo_POIJQR、vo_RGZYYYGJZ、vo_ST、vo_STNPC、
vo_Shixifeidu、vo_Side、vo_StJCFYLQ、vo_StYZC、vo_TZZNQ、vo_XJXYST、vo_ZSPYMP、vo_ZYHPYMP、
vo_Zuoyequnxing、vo_func、vo_simple、vo_zhuiyuejie。

gl 侧 9 类：vo_Character、vo_Heihaian、vo_Huanglong、vo_Main、vo_ST、vo_STNPC、vo_Side、vo_TZZNQ、
vo_XJXYST。

这些缩写为任务 / 活动的内部代号，解包时按事件归属原样建目录，不做翻译改写。

## 索引清单 schema（每次解包必须产出）

UTF-8 CSV，Excel 可直接打开：

| 文件 | 内容 | 列 |
|------|------|-----|
| index_events.csv | 全部音频事件（3.7 时 39,444 行） | event、top、sub、file、langs、media_count、debug_name、media_ids、note |
| index_media.csv | 每个被事件引用的媒体一行（3.7 时 53,482 行） | media_ref、primary_event、file、event_count、events、debug_name |
| index_voice.csv | 全部语音文件（3.7 时 47,088 行） | official_name、file、lang、category、subject、bytes |
| index_unreferenced.csv | 孤儿媒体对照表（3.7 时 179 行） | file、wem_ref、bytes |

关键口径：

- `debug_name` 是 Kuro 官方 Wwise 工程的源文件路径，保留完整层级（如
  `plot\2.1\level_b\zh_vo_Character_Brant_13_NOSUB_1.wav` = 2.1 版支线 level_b 剧情语音），
  可直接据此定位任务 / 版本 / 场景，是全部索引里最有价值的对照列。
- 多个事件共用同一媒体：文件只归字母序首个事件，其余事件在 index_media.csv 的 `events` 列
  交叉引用（空格分隔）。
- `note` 列记录缺失标注（事件存在但媒体缺失等）。

## 已知限制

- PLUG 魔数文件是 Kuro 私有插件媒体（非标准 Wwise 编码），vgmstream 无法解码，3.7 时 38 个，
  按 `.wem` 原样存 `Unreferenced\PLUG_wem\`。
- 台词字幕与语音名的映射是运行时动态关联，静态包数据里没有，解包库不含台词文本。
- 角色中文名映射在 ConfigDB flatbuffer 内，解包时不展开，只保留官方内部名。

## 对账与验收

- 解包完成后 wav + 原样 wem 的文件总数必须等于包内 wem 总量。
- 四张索引的行数、`file` 列指向的路径必须与目录树逐行一致。
- 事件名、语音官方全名、`debug_name` 三类命名信息缺一不可。
