# Validate a Civ6 upload workspace before upload
#
# 在上传器自带 validate 之外，额外 lint workshop.json 的 localizations（2026-10-24 Cube_CityStates
# 事故的预上传门）：Steam 对本地化语言变体提交会把**未显式 Set 的本地化 title/description 清空**，
# 所以每条 localizations 必须 title+description 成对齐全；只改描述不带 title = 丢该语言标题。
#   - localizations 条目缺 title 或 description（空串同缺）→ exit 1
#   - 顶层 title 若存在但为空串 → exit 1（SetItemTitle("") 会清空主标题）
#   - 不写 localizations / 字段齐全 → 放行（顶层漏字段对主条目是安全的，见 release.md Hard Rules ⑬）
#
# 2026-11-04 追加硬闸（release.md Hard Rules ④）：更新流程完全不处理标题与描述，
# 以工坊既有版本为准。workshop.json 出现 title / description / localizations 一律 exit 1；
# 仅「新建条目」或「用户明确要求改文字」时才允许，届时显式加 -AllowMeta 放行。
param(
    [Parameter(Mandatory=$true)][string]$Workspace,
    [string]$Tool = "D:\documents\Civ6WorkshopUploader\tool\Civ6WorkshopUploader.exe",
    [switch]$AllowMeta
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Tool)) { Write-Error "Tool not found: $Tool"; exit 1 }

$wsJson = Join-Path $Workspace "workshop.json"
if (Test-Path $wsJson) {
    $cfg = Get-Content $wsJson -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $AllowMeta) {
        foreach ($field in @("title", "description", "localizations")) {
            if ($null -ne $cfg.$field) {
                Write-Host "[FAIL] workshop.json 含 $field —— 更新流程不碰标题/描述，以线上既有版本为准（release.md Hard Rules ④）；确认要改文字时加 -AllowMeta" -ForegroundColor Red
                exit 1
            }
        }
        Write-Host "[OK] workshop.json 未含 title/description/localizations —— 标题与描述保持线上原样"
    }
    if ($null -ne $cfg.title -and [string]::IsNullOrEmpty($cfg.title)) {
        Write-Host "[FAIL] workshop.json 顶层 title 是空串 —— 会把主标题清空；要么删掉该字段，要么写完整标题" -ForegroundColor Red
        exit 1
    }
    if ($null -ne $cfg.localizations) {
        $i = 0
        foreach ($loc in $cfg.localizations) {
            $i++
            $lang = if ($loc.language) { $loc.language } else { "<第 $i 条无 language>" }
            foreach ($field in @("title", "description")) {
                $v = $loc.$field
                if ($null -eq $v -or [string]::IsNullOrEmpty($v)) {
                    Write-Host "[FAIL] localizations[$lang] 缺 $field —— 该语言提交会把它清空（Hard Rules ⑬）；删掉整条 localizations 或补齐成对字段" -ForegroundColor Red
                    exit 1
                }
            }
        }
        Write-Host "[OK] localizations $($cfg.localizations.Count) 条，title/description 成对齐全"
    }
}

& $Tool validate -w $Workspace
exit $LASTEXITCODE
