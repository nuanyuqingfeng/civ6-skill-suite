# 分发范围与上游出处

包内分两类：随包分发的自建件（本机产出，无公开上游）与需自行获取的第三方插件与 SDK。

## 一、随包分发（解压即用，无需联网）

| 目录 | 内容 | 用途 | 备注 |
|------|------|------|------|
| `tools/CivNexus6/` | 35 MB，62 个文件：`NexusBatch.exe`、`CivNexus6.exe`、16 个读数工具 exe、16 个 Firaxis/Granny/FBX 程序集 | 模型与动画转换、四条判据读数 | 未签名，必须在 `D:\documents` 树外执行 |
| `scripts/` | 242 个文件，1.7 MB：根目录 76 个主流程与诊断脚本（`jx_build5.py` 及其依赖模块 `jx_r3_face.py`、`jx_morph_face.py`、`jx_hair_rib.py`、`jx_secondary.py`、`jx_r5_bangs.py`，`jx_assemble.py`、`jx_ast_normalize.py`、`jx_cook.sh`，接缝诊断四个脚本），`probes/` 6 个贴图与法线读数脚本，`csharp/` 17 个文件，`archive/` 143 个一次性诊断采样脚本 | 装配、面部表情层、入工程、ast 重建、cook 封装、接缝与表情诊断 | 内含工程路径常量，换项目需改；`jx_build5.py` 缺任一依赖模块即导入失败 |
| `scripts/csharp/` | 16 个 `.cs`：`NexusBatch`、`NexusDumpBind`、`NexusNames`、`NexusBoneCurve` 等源码 | 重新编译读数工具 | 依赖 `tools/CivNexus6` 内程序集 |
| `patches/UAnimSequence.cs` | ACL 动画解码补丁后的文件 | 由 `scripts/build_acl_patch.ps1` 覆盖到 CUE4Parse 源码树并重编译托管程序集 `CUE4Parse.dll` | 原文件路径 `<CUE4Parse 仓库根>/CUE4Parse/UE4/Assets/Exports/Animation/UAnimSequence.cs` <!-- WUWA --> |

读数工具与转换工具在同一个目录，运行时依赖同目录的 `NexusBuddy`、`Firaxis.*`、`FbxImporter`、`Firaxis.Granny.*` 程序集，禁止单独拷贝某个 exe 到别处运行。

## 二、需自行获取（第三方插件与 SDK）

| 工具 | 用途 | 上游地址 | 取得方式 | 核验状态 |
|------|------|---------|---------|---------|
| dsh-ue-asset | 本机首选解包通道：解析进程挂在 DSH Web 上，暴露 HTTP 接口与 MCP 通道 | https://github.com/Sumcam-L/dsh-ue-asset | Release 页下载 `dsh-ue-asset.tgz` 解包，或 `dsh plugin --profile web add 'link:<目录>'` | 本机已装 0.1.8 于 `D:/documents/Deepseek_WorkPlace/dsh-ue-asset`，`/ue-asset/api/sessions` 实测可用 |
| FModel | UE 包浏览与 psk/ueanim 导出宿主，dsh-ue-asset 不可用时的兜底 | https://github.com/4sval/FModel | Release 页下载压缩包 | 页面标题经搜索核对 |
| fmodel-mcp | FModel 的 MCP 封装，会话内直接调用解包 | https://github.com/plu1337/fmodel-mcp | `git clone` 后 `dotnet build` | 本机仓库 `git remote -v` 实测 |
| CUE4Parse | UE 解析库，ACL 补丁的宿主 | https://github.com/FabianFG/CUE4Parse | 随 fmodel-mcp 引用 | 页面标题经搜索核对 |
| Blender 4.5 LTS | 装配、重定向、cn6 与 FBX 导出 | https://www.blender.org/download/lts/ | 便携版 zip 解压 | 本机已装 4.5.9，路径见 SKILL.md §〇 |
| psk/psa 插件 | Blender 读写 ActorX psk 与 psa | https://github.com/DarklightGames/io_scene_psk_psa | Release 页下载 zip | 页面标题经搜索核对 |
| UEFormat 插件 | Blender 读写 `.uemodel`/`.ueanim`/`.uepose` | https://github.com/h4lfheart/UEFormat | Release 页下载 zip | 页面标题经搜索核对 |
| cn6 插件 | Blender 导入导出 `.cn6` | https://forums.civfanatics.com/resources/blender-scripts-for-civ-v-and-civ-vi.25925/ | CivFanatics 资源页下载 | 直连打开成功 |
| GR2 插件 | 读取正样本 `.gr2` 骨架与网格 | https://github.com/SWTOR-Slicers/Granny2-Plug-In-Blender-2.8x | Release 页下载 zip | 页面标题经搜索核对 |
| Civ6 Development Tools | Asset Cooker、FgxViewer、ModBuddy、pantry | https://store.steampowered.com/app/404350/ | Steam 免费工具 | 直连打开成功 |
| vgmstream | 解码 Wwise IMA ADPCM 供口型包络 | https://github.com/vgmstream/vgmstream | Release 页下载二进制 | 页面标题经搜索核对 |
| .NET SDK | 编译 C# 读数工具与 fmodel-mcp | https://dotnet.microsoft.com/download | 官方安装包 | 直连打开成功 |
| python-zstandard | UEFormat 插件依赖的 zstd 绑定 | https://pypi.org/project/zstandard/ | `pip install zstandard` | PyPI 页面直连打开成功 |

CivNexus6 的上游为 https://github.com/deliverator23/CivNexus6（论坛发布页 https://forums.civfanatics.com/resources/civnexus6.25987/），本包已带其构建产物，源码留作重编译参考。

## 三、部署到本机

```bash
cp -r tools/CivNexus6 "/e/SoftWares/civ6_nexus_work/CivNexus6"
cp -r scripts/* "/d/documents/.../<方案根>/workspace/_tools/"
```

<!-- WUWA:BEGIN -->
ACL 解码补丁由 `scripts/build_acl_patch.ps1` 完成覆盖与编译；装入 FModelMcp 版本目录由人工执行，复制前核对版本提交一致。

前置条件：

1. .NET SDK 10 或更高版本（`dotnet --version` 输出以 10 开头）。本机实测使用 SDK 10.0.403；系统自带的 9.0.102 不满足 `net10.0` 目标。
2. CUE4Parse 源码树，用 `git clone --depth 1 https://github.com/FabianFG/CUE4Parse` 取得，并切到与现役 FModel 对应的提交。本机实测提交 `85495b5e126203d68ae3bf84e37fe31abd56a0e5`，版本 1.2.2。浅克隆缺少 `CUE4Parse-Natives/ACL/external/acl` 与 `CUE4Parse-Natives/Oodle/external/oodle2` 的子模块内容，该缺失只影响 native 库，托管程序集照常构建。

用法：

```powershell
pwsh -File scripts/build_acl_patch.ps1 -SourceRoot <CUE4Parse 仓库根>
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `-SourceRoot` | 是 | CUE4Parse 仓库根，其下需存在 `CUE4Parse/CUE4Parse.csproj` 与 `CUE4Parse/UE4/Assets/Exports/Animation/UAnimSequence.cs` |
| `-Configuration` | 否 | 构建配置，默认 `Release` |

脚本动作：校验路径、覆盖 `UAnimSequence.cs`、执行 `dotnet build --no-incremental`、核对产物内含补丁标记串 `ACL codec DDC handle mismatch`、回显产物绝对路径与字节数与 sha256 与 FileVersion 与 ProductVersion。参数或路径缺失以退出码 2 终止，`dotnet build` 失败以它自己的退出码终止，产物缺补丁标记以退出码 4 终止。脚本不复制任何文件。

安装（人工执行）：先比对产物的 ProductVersion 与现役 `CUE4Parse.dll` 的 ProductVersion，两者的提交哈希一致才复制。

```powershell
Get-Item "E:\SoftWares\FModelMcp\versions\1.1.1-d34a1cf64367\CUE4Parse.dll" | ForEach-Object { $_.VersionInfo.ProductVersion }
Get-Item "<CUE4Parse 仓库根>\CUE4Parse\bin\Release\net10.0\CUE4Parse.dll" | ForEach-Object { $_.VersionInfo.ProductVersion }
```

两个串不一致时，改用与现役 FModel 版本对应的提交重新克隆源码树并构建，哈希一致后再复制。

验证方式：核对产物 sha256 与 ProductVersion。本机实测产物 4398592 字节、sha256 `e1dca7be19364d78d2355c31d921f5a4259159175128a40de23f618d2736d3a4`、FileVersion 1.2.2.0、ProductVersion `1.2.2+85495b5e126203d68ae3bf84e37fe31abd56a0e5`；现役版本目录内的 `CUE4Parse.dll` 为 4046336 字节、sha256 `cba41b5a26fdc921d9bfab4a23b18007994fe16d2ede665b3cbe765d3bcedf90`、FileVersion 1.2.2.0、ProductVersion `1.2.2+226780e9b2e69ebf3e0fbcd4009d40d309e4cd80`。两个 ProductVersion 的提交哈希不同，直接把产物复制进去会得到一个与现役 FModel 不同提交的程序集。

`CUE4Parse-Natives.dll` 不复制。补丁改的是 C# 源码，载体是托管程序集 `CUE4Parse.dll`；FModelMcp 版本目录内现役 native 库 45568 字节、sha256 `367c9896ab2755d8d5313d2ef5cdcf030e42986a1d39751506f711a9b43a0564`，含 ACL 相关字符串；浅克隆重建出的 native 库不含 ACL 与 Oodle 内容，三次重建得到三个互不相同的哈希（均为 103936 字节：`69b494516a85e6a29d9e88204ca3b16358b31519a9c2b15b9fd62983ae7dc98d`、`52ffcc78d61b81379add64c89aa21b77dc622a42fcd90c9048988a7ef21fa077`、`9c61b99f944ef78479621c8144d11b59890cf9275a0683ea72b53fe628b8682f`），覆盖安装会丢掉 ACL 解码能力。

未验证项：按版本哈希一致装入版本目录的 `CUE4Parse.dll` 未启动 FModel 实测导出；native 库在上述浅克隆条件下无法重建出 ACL 能力。
<!-- WUWA:END -->

## 四、核验方式说明

「直连打开成功」指用网页抓取工具直接取到页面正文（HTTP 200）。

「页面标题经搜索核对」指本机在 2026-10-27 直连 `github.com` 超时（`curl` 28 秒超时），改为从搜索引擎返回的 GitHub 页面标题核对仓库路径与项目描述；仓库路径与本机已有仓库的 `git remote -v` 一致。

「本机仓库 `git remote -v` 实测」指该仓库已在本机存在，远程地址由 git 自己报告。
