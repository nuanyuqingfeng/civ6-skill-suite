# 提取：CivNexus6 资源页（CivFanatics resource 25987，v1.3.3，作者 Deliverator）

> 来源：https://forums.civfanatics.com/resources/civnexus6.25987/ （源码：resource 26047）
> 采集日期：2026-11-01（WebFetch 服务端缓存，全功能提取）
> 用途：civ6-model-import skill 优化对照——下列能力中多项被 skill 现管线绕开而自造。

## 定位

Civ6 `.fgx` 导入/导出工具，"Nexus Buddy 2 updated to work with Civilization 6"。注意：官方资源页没有独立 "NexusBatch" 条目——批量功能是 CivNexus6 自身的一部分（skill 包内 NexusBatch.exe 为私有 fork）。

## 安装要求

1. 建 "Dummy" 目录，内含 `Assets`（复数）与 `Resource`（单数）两个子目录。
2. 注册表 `HKEY_CURRENT_USER\Software\Firaxis\Tools` 建 `ToolAssetPath` 指向 Dummy 目录。
3. 贴图转换功能需 VC++ Redistributable 2017；可能还需 .NET Framework 4。

## 导出（Civ6 → Blender）

- 模型 `.cn6/.nb2`、动画 `.na2`（**配对脚本导入 Blender**）。
- .cn6 相对 .br2 的增强：
  - 每网格最多 3 层 UV（建筑 Emissive/夜景用）
  - **每顶点最多 8 组骨索引/权重**（Civ5 为 4）
  - 材质导入/导出（仅名字）
  - 每网格多三角组、各自绑材质
  - **自定义顶点法线正确导入（原版法线经哑顶点组 `VERTEX_KEYS` 保留；删掉该组即强制 Blender 重算法线/副法线/切线）**
- 旧 .nb2/.br2 格式仍可用单选钮选择。

## 导入（Blender → Civ6）：BR2/CN6 Import 与 Overwrite

先从 Blender 导出已绑骨模型。**推荐用 Blender 2.7x 导出**（即便在 2.49 里干活），因为 2.7x 导出 binormals 与 tangents，网格更平滑。两个入口：

1. **"Open"**：从 .br2/.cn6 载入骨架+网格。
2. **Overwrite**：打开原版 .fgx 底模的副本，只替换网格、骨架原样保留（复用原版资产的推荐做法）。

**稳定性提示**：两种入口之后都应立即 "Save" 保存 .fgx "for stability reasons"。

### 网格顶点格式（三种）

1. 带骨绑定 + 1 UV —— 单位、**领袖**、一切蒙皮物
2. 无骨绑定 + 2 UV —— 静态物（武器/盾）
3. 无骨绑定 + 3 UV —— 带 Emissive 的改良设施

## 材质支持

增/删/改材质名与网格绑定。**只有材质名重要——其余由 Asset Cooker 经工程内 .ast/.mtl 处理**。Edit Mesh Material Bindings 标签页切换指派/改网格名；Edit Materials 标签页增删改材质。

## XML 元数据生成

- **"Create GeometrySet .xml for .ast"**：自动生成 `<m_GeometrySet>` 条目，接上材质名即可。
- **"Create Geometry/Animation (.geo/.anm) File"**：模型出 .geo，动画出 .anm。
- class 用 "Class" 下拉选（Unit、LandmarkModel 等）。**Class = "Leader" 时 .geo 生成会附带 dummy .wig 文件**（1.2.5 加入）。

## Civ5 / CivBE .gr2 迁移

- 打开 Civ5 .gr2 立即重存为 .fgx。警告：这些文件在 Civ6 可用前必须从 .br2/.cn6 Overwrite 网格。
- **"Convert all .gr2 Files in Directory to .fgx/.anm"**：批量转 Civ5 动画（先用 Nexus Buddy 2 批量重存 .gr2）。
- 相关教程：Civ5/CivBE 单位转 Civ6；modded .fgx 入游戏指南。

## 贴图功能（更新日志）

- 1.3.2：Further Actions 标签页新增 **Texture Import** —— 导入贴图为 Civ6 dds/tex。
- 1.3.3：**"Process All Textures in Directory" 支持 PNG、TGA、JPG 以及 DDS**。

## 其他版本要点

- 1.2.4：可插入 Adjustment Bone 修改 Position（以及 Scale/Rotation）。
- 1.2.6：Create GeometrySet xml 支持每网格多 Tri-Group/材质。
- 1.0.1：**"Open FBX should now work for turning .fbx -> .fgx"**（需指定 Mesh 名）。
