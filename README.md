# civ6-skill-suite

文明 6（Civilization VI）mod 开发的 AI skill 合集，11 个 skill 以子目录共存于 `skills/`。

每个 skill 都是独立的技能目录：一份 `SKILL.md` 入口，配套 `references/`、`scripts/`、`assets/` 与离线参考库。

| 目录 | 管什么 |
|---|---|
| `skills/civ6-modding/` | 玩法侧总入口 + 发布：Lua（UI + GP）、ForgeUI XML、`.civ6proj` / `.modinfo`、数据库 XML/SQL、事件系统、API 参考、Steam 创意工坊发布 |
| `skills/civ6-art-reference/` | 引用原版美术素材：ArtDef/XLP 四层引用链 + cook 层（pantry 解析 / 产物归一化 / 警告即静默降级） |
| `skills/civ6-art-unpack/` | 受限素材通道（默认禁用）：唯一入口是 `civ6-art-reference` SKILL.md 的路由句 |
| `skills/civ6-asset-forge/` | 2D 美术素材总入口：总督、忠诚度与宗教压力、单位晋升规格、2D 领袖纸片人、UI 立绘与选人背景、历史时刻插画、FrontEnd 立绘、区域图标、领袖头像、资源图标、单位肖像 |
| `skills/civ6-audio-pipeline/` | 音频全流程：素材整备 → 核验 → 按类别响度均衡 → Wwise 工程直改 → 自动注册 |
| `skills/civ6-html-ui/` | HTML/CSS 设计 → UI 纹理 → 原生 XML/Lua |
| `skills/civ6-landmarks/` | 静态地标组合：SDK 官方几何 → Landmarks.artdef + tilebases.xlp + 建筑差分 → Cooker |
| `skills/civ6-model-import/` | UE 工程的 psk / ueanim 导入文明6：领袖链（FModel 解包 → Blender 重定向 → cn6/FBX 双链 → NexusBatch → cook 部署）、单位链（psk 直导 → CivModelTool 导出 → AST 回填） |
| `skills/civ6-modeltool/` | CivModelTool Blender 插件（`cmt.*` 算子）：`.fgx` 模型与动画、`.ast`、材质贴图、ArtDef 导出，型态键转骨，网格清理；Blender 等二进制工具链另取，见下文 |
| `skills/civ6-text-authoring/` | 文本处理权威规范：风云变幻口径简体中文语料（27,998 tag）+ 六大类写法规范 + 模式文本模块 |
| `skills/civ6-tuner/` | FireTuner 运行时验证（TCP 4318）：在运行中的对局里执行 Lua |

各 skill 的详细内容以各自 `SKILL.md` 为准。

## 安装

把 `skills/` 下的目录整个复制到技能根目录（本机为 `~/.agents/skills/`）即可；目录名就是 skill 名，不需要改名。

## 工具链还原（civ6-modeltool）

`skills/civ6-modeltool/` 进版本库的只有插件源码、`civhash`、体检脚本与文档。Blender 便携包、AssetEditor、DllProxy 体积超过 git 仓库的合理范围，按下面的地址取回，解压到 `skills/civ6-modeltool/tools/` 下对应子目录：

| 目录 | 取回地址 | 版本 |
|---|---|---|
| `tools/blender/blender-5.2.3-windows-x64/` | <https://download.blender.org/release/Blender5.2/> 的 `blender-5.2.3-windows-x64.zip` | 5.2.3 LTS |
| `tools/asseteditor/AssetEditor/` | <https://github.com/Sumcam-L/AssetEditor/releases/tag/1.1> | 1.1 |
| `tools/dllproxy/version.dll` | <https://github.com/Sumcam-L/DllProxy/releases/tag/1.0> | 1.0 |

Blender 解压后把插件源码放进便携目录并启用：

    copy skills\civ6-modeltool\tools\vendor\CivModelTool  skills\civ6-modeltool\tools\blender\blender-5.2.3-windows-x64\portable\scripts\addons\CivModelTool

默认的 Blender 包不带 `portable/`，首次启动会把偏好写到 `%APPDATA%\Blender Foundation`；建一个空的 `portable/` 目录即可让它就近读写。

各条目的路径相对 skill 根目录解析：

    skills\civ6-modeltool\tools\blender\blender-5.2.3-windows-x64\blender.exe

版本、来源与校验值见 `skills/civ6-modeltool/README.md`。

## 同步流程

本地各 skill 是独立 git 仓库，本仓库是它们的合并快照：`skills/<名>/` 是本地同名仓库工作树的文件快照，受控文件与未忽略文件一并导出。本地改动提交后，从本地仓库重新导出对应子目录并提交本仓库。

## 许可

PolyForm Noncommercial 1.0.0，见 [LICENSE](LICENSE)。各 skill 吸收的第三方内容、来源与采用范围见其 `THIRD_PARTY_NOTICES.md` 与 `SOURCES.md`。
