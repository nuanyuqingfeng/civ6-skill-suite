# scripts/archive/ — 一次性诊断脚本归档

本目录存放 2026-10 阶段为单次取证写的诊断脚本：`jx_r3*`…`jx_r16*`、`jx13*`、`jx14*`、`jx_portrait*`、`jx_pmx*`、`jx_voice*`、`jx_wpn*`，共 142 个。这些脚本只在复现旧结论时按需运行，内部工程路径常量多为当时工程的旧值。

保留在 `scripts/` 根目录的是主流程脚本（`jx_build5.py` 及其六个依赖模块、`jx_assemble.py`、`jx_ast_normalize.py`、`jx_cook.sh`、接缝与探针诊断四个脚本）、`scripts/probes/`、`scripts/csharp/` 与 `build_acl_patch.ps1`。

约定：不再新增一次性脚本。新的取证需求先改进 `scripts/probes/` 里的既有工具；临时验证在 `workspace/tmp` 里跑完即弃，需要留存的结论写进 `workspace/gen/reports/`。
