[CmdletBinding()]
param(
    [string]$SourceRoot,
    [string]$Configuration = 'Release'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($SourceRoot))
{
    Write-Host '错误：缺少参数 -SourceRoot（CUE4Parse 仓库根目录）'
    exit 2
}
if (-not (Test-Path -LiteralPath $SourceRoot -PathType Container))
{
    Write-Host "错误：缺失路径 $SourceRoot"
    exit 2
}

$packageRoot = Split-Path -Parent $PSScriptRoot
$patchFile   = Join-Path $packageRoot 'patches/UAnimSequence.cs'
$projectFile = Join-Path $SourceRoot 'CUE4Parse/CUE4Parse.csproj'
$targetFile  = Join-Path $SourceRoot 'CUE4Parse/UE4/Assets/Exports/Animation/UAnimSequence.cs'

foreach ($required in @($patchFile, $projectFile, $targetFile))
{
    if (-not (Test-Path -LiteralPath $required -PathType Leaf))
    {
        Write-Host "错误：缺失路径 $required"
        exit 2
    }
}

$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if ($null -eq $dotnet)
{
    Write-Host '错误：未找到 dotnet 命令，需先安装 .NET SDK'
    exit 2
}
Write-Host "dotnet：$($dotnet.Source)"

Write-Host "补丁文件：$patchFile"
Write-Host "覆盖目标：$targetFile"
Copy-Item -LiteralPath $patchFile -Destination $targetFile -Force
Write-Host "覆盖完成 sha256：$((Get-FileHash -LiteralPath $targetFile -Algorithm SHA256).Hash)"

& $dotnet.Source build $projectFile -c $Configuration --no-incremental
$buildExit = $LASTEXITCODE
if ($buildExit -ne 0)
{
    Write-Host "错误：dotnet build 退出码 $buildExit"
    exit $buildExit
}

$binRoot = Join-Path $SourceRoot "CUE4Parse/bin/$Configuration"
if (-not (Test-Path -LiteralPath $binRoot -PathType Container))
{
    Write-Host "错误：缺失构建输出目录 $binRoot"
    exit 2
}
$artifacts = @(Get-ChildItem -LiteralPath $binRoot -Filter 'CUE4Parse.dll' -File -Recurse -Depth 1)
if ($artifacts.Count -eq 0)
{
    Write-Host "错误：构建输出中没有 CUE4Parse.dll，目录 $binRoot"
    exit 2
}
if ($artifacts.Count -gt 1)
{
    Write-Host '错误：构建输出中存在多个 CUE4Parse.dll'
    $artifacts | ForEach-Object { Write-Host $_.FullName }
    exit 2
}

$dll = $artifacts[0]
$marker = 'ACL codec DDC handle mismatch'
# 托管字符串堆不保证偶数对齐，两种起始偏移各解码一次
$dllBytes = [System.IO.File]::ReadAllBytes($dll.FullName)
$textAtEven = [System.Text.Encoding]::Unicode.GetString($dllBytes)
$textAtOdd = [System.Text.Encoding]::Unicode.GetString($dllBytes, 1, $dllBytes.Length - 1)
if (-not ($textAtEven.Contains($marker) -or $textAtOdd.Contains($marker)))
{
    Write-Host "错误：构建产物中未找到补丁标记 $marker，产物 $($dll.FullName)"
    exit 4
}

$version = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($dll.FullName)
Write-Host "产物：$($dll.FullName)"
Write-Host "产物字节数：$($dll.Length)"
Write-Host "产物 sha256：$((Get-FileHash -LiteralPath $dll.FullName -Algorithm SHA256).Hash)"
Write-Host "产物 FileVersion：$($version.FileVersion)"
Write-Host "产物 ProductVersion：$($version.ProductVersion)"
Write-Host "补丁标记命中：$marker"

exit 0
