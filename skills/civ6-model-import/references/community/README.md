# community/ — 社区成熟做法参考资料（2026-11-01 采集）

采集目的：civ6-model-import skill 的管线与 CivFanatics 社区工具链（Deliverator 系）同源，但若干环节自造，导致 gotchas.md 60+ 条痛点。本目录存放联网调研取得的社区成熟做法证据，供 skill 优化实验对照。

## 文件索引

| 文件 | 来源 URL | 采集日期 | 状态 |
|------|----------|----------|------|
| `art-assets-guide-extract.md` | https://forums.civfanatics.com/threads/art-assets-in-civilization-6-a-modding-guide.612050 | 2026-11-01 | ✅ 全文要点提取 |
| `civnexus6-tool-extract.md` | https://forums.civfanatics.com/resources/civnexus6.25987/ （源码 resource 26047） | 2026-11-01 | ✅ 全功能提取，v1.3.3，作者 Deliverator |
| `animation-route-notes.md` | 上述两页加 https://github.com/Sukritact/Nexus-Buddy-2-Blender-Scripts 源码综合 | 2026-11-01 | ✅ 综合笔记（含 na2 只读这一关键事实） |
| `Nexus-Buddy-2-Blender-Scripts/` | https://github.com/Sukritact/Nexus-Buddy-2-Blender-Scripts （git clone） | 2026-11-01 | ✅ 完整源码，`Blender-2.8-Addons/io_import_na2.py` 为 na2 只读证据 |
| `civnexus6-fork-diff.md` | 无外部来源：对照包内 `tools/CivNexus6/` 与 E7 实验整理 | 2026-11-01 | ✅ D1–D8 差异清单，E7 依据 |
| `handoff-clarifier.md` | 无外部来源：本地交接澄清稿 | 2026-11-01 | ✅ 三点澄清（替换自造层、机制落点、na2 只读） |
| `skill-optimize-prompt.md` | 无外部来源：本地任务书 | 2026-11-01 | ✅ 四类问题与 E1–E7 任务拆分来源 |

## 未能全文落盘的线索（CivFanatics bot 校验拦截，要点已并入上列文件）

| 来源 URL | 采集日期 | 关键事实（已并入 extract） |
|----------|----------|---------------------------|
| https://forums.civfanatics.com/threads/tutorial-converting-3d-art-from-civ-5-civ-be-to-civ-6.613142 | 2026-11-01 | gr2→fgx/anm 批量转换由 CivNexus6 NexusBatch 承担，需先用 NB2 批量重存 gr2 |
| https://forums.civfanatics.com/threads/extract-gr2-animations-into-blender-and-re-import-to-civ-v-civ-be.564873 | 2026-11-01 | 动画进出 Blender 的历史路径与坑 |
| https://forums.civfanatics.com/resources/blender-scripts-for-civ-v-and-civ-vi.25925/ | 2026-11-01 | 本机 cn6 插件的上游；2.49 与 2.7x 双版本脚本 |
| https://forums.civfanatics.com/resources/nexus-buddy-2-scripts-for-blender-2-49-v12.53037/ | 2026-11-01 | 2.49 端 FBX6.1→NB2 动画链的脚本侧 |
| https://forums.civfanatics.com/threads/nexus-buddy-2-granny-editor-for-civ-5.496855 与 https://forums.civfanatics.com/resources/nexus-buddy-2-1.52997/ | 2026-11-01 | NB2 本体（exe 与源码）唯一分发位，无 GitHub 编译镜像；本机不存在 NB2（`E:\SoftWares` 下 NexusBuddy.dll 是 CivNexus6 fork 的库） |
| https://forums.civfanatics.com/threads/mcs-content-animated-leaders-a-world-wonder.687643/ | 2026-11-01 | 成熟范例帖；抓取被拦截，未取得工作流自述 |
| 「How to adjust the rotation of the unit model?」（CivFanatics，2023-09，未取得固定链接） | 2026-11-01 | 用 NA2 加 Blender 3.4 修导入旋转，证实旋转问题社区同样遇到 |

## 采集方法备注

- CivFanatics 对直接抓取（curl 或 WebFetch）返回 Stile bot 校验页；两次成功的提取发生在校验生效前的服务端缓存。
- 本沙箱 Bash 出网受限（git clone 可用，curl 外网不可用），jina reader 代理超时。后续补充采集建议：浏览器通道（browser-use）或人工开页复制。
