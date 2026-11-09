# Verify a workshop item after upload using Steam API
#
# 检查项：
#   1. 默认（english）标题 —— null/空 → exit 1；给了 -ExpectedTitle 则精确比对
#   2. -LocalizedTitle：逐语言抓工坊页检查本地化标题（workshopItemTitle div）
#      —— 空/缺失 → exit 1（2026-10-24 Cube_CityStates 事故：本地化提交漏 title 被 Steam 整体清空，
#         API 只返回默认标题，探不到这种丢失，必须逐语言查页面）
#      —— 给了 -LocalizedTitles 哈希表则再精确比对（语言代码 → 期望标题）
#   3. time_updated / hcontent_file / visibility / result 照旧打印，变化与否由调用方比对基线
#
# 退出码：0 = 全部通过；1 = 任一失败
param(
    [Parameter(Mandatory=$true)][string]$ItemId,
    [string]$ExpectedTitle = "",
    [switch]$LocalizedTitle,
    [hashtable]$LocalizedTitles = @{},
    [string[]]$Languages = @("schinese","tchinese","japanese","koreana","german","spanish","french")
)
$body = "itemcount=1&publishedfileids[0]=$ItemId"
try {
    $r = Invoke-RestMethod -Method Post -Uri "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/" -Body $body -TimeoutSec 30
} catch {
    Write-Error "Steam API request failed: $_"
    exit 1
}
$d = $r.response.publishedfiledetails[0]
[pscustomobject]@{
    publishedfileid = $d.publishedfileid
    title           = $d.title
    visibility      = $d.visibility
    time_updated    = $d.time_updated
    hcontent_file   = $d.hcontent_file
    result          = $d.result
} | Format-List

$fail = $false
if ([string]::IsNullOrEmpty($d.title)) {
    Write-Host "[FAIL] 默认标题为空 —— 标题已被清空！" -ForegroundColor Red
    $fail = $true
} elseif ($ExpectedTitle -and $d.title -ne $ExpectedTitle) {
    Write-Host "[FAIL] 默认标题不符：期望 '$ExpectedTitle'，实际 '$($d.title)'" -ForegroundColor Red
    $fail = $true
} else {
    Write-Host "[OK] 默认标题：$($d.title)" -ForegroundColor Green
}

if ($LocalizedTitle) {
    foreach ($lang in $Languages) {
        $html = $null
        for ($i = 0; $i -lt 4; $i++) {
            try {
                $html = (Invoke-WebRequest -Uri "https://steamcommunity.com/sharedfiles/filedetails/?id=$ItemId&l=$lang" -TimeoutSec 30 -UseBasicParsing).Content
                break
            } catch {
                Start-Sleep -Seconds (20 * ($i + 1))   # steamcommunity 页面限流常见 429，退避重试
            }
        }
        if (-not $html) {
            Write-Host "[WARN] $lang 页面抓取失败（重试后仍限流），人工复核" -ForegroundColor Yellow
            continue
        }
        $t = $null
        if ($html -match '<div class="workshopItemTitle">([^<]*)</div>') { $t = $Matches[1] }
        if ([string]::IsNullOrEmpty($t)) {
            Write-Host "[FAIL] $lang 本地化标题为空/缺失 —— 被清空了！" -ForegroundColor Red
            $fail = $true
        } elseif ($LocalizedTitles.Count -gt 0 -and $LocalizedTitles.ContainsKey($lang) -and $LocalizedTitles[$lang] -ne $t) {
            Write-Host "[FAIL] $lang 本地化标题不符：期望 '$($LocalizedTitles[$lang])'，实际 '$t'" -ForegroundColor Red
            $fail = $true
        } else {
            Write-Host "[OK] $lang 本地化标题：$t" -ForegroundColor Green
        }
        Start-Sleep -Seconds 3   # 页间限流间隔
    }
}
if ($fail) { exit 1 }
