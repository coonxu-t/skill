# xk-invoice-skills 一键安装（Windows PowerShell 5.1+ / PowerShell 7+）
# 用法:
#   .\install.ps1
#   .\install.ps1 -Project C:\code\my-project
#   .\install.ps1 -Dir C:\Temp\skill-test -Force -WithDeps
param(
    [switch]$User,
    [string]$Project,
    [string]$Dir,
    [switch]$Force,
    [switch]$WithDeps
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsSrc = Join-Path $RepoRoot 'skills'
$SkillNames = @(
    'xk-invoice-pipeline',
    'xk-pdf-to-jpg',
    'xk-invoice-ocr-summary',
    'xk-invoice-ledger'
)

if (-not (Test-Path $SkillsSrc -PathType Container)) {
    throw "找不到 skills/ 目录，请在仓库根目录运行本脚本"
}

if ($Dir) {
    $Target = $Dir
} elseif ($Project) {
    $Target = Join-Path $Project '.workbuddy\skills'
} else {
    $Target = Join-Path $env:USERPROFILE '.workbuddy\skills'
}

New-Item -ItemType Directory -Path $Target -Force | Out-Null
Write-Host "安装目标: $Target"
Write-Host ''

$backup = $null
$installed = 0
$skipped = 0

foreach ($name in $SkillNames) {
    $dest = Join-Path $Target $name
    if (Test-Path $dest -PathType Container) {
        if (-not $Force) {
            Write-Host "  跳过  $name（已存在；如需覆盖加 -Force）"
            $skipped++
            continue
        }
        if (-not $backup) {
            $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
            $backup = Join-Path (Split-Path -Parent $Target) "skills_backup_$stamp"
            New-Item -ItemType Directory -Path $backup -Force | Out-Null
        }
        # 用「移动」而不是删除：旧版本可随时找回
        Move-Item -Path $dest -Destination (Join-Path $backup $name) -Force
    }
    Copy-Item -Path (Join-Path $SkillsSrc $name) -Destination $dest -Recurse -Force
    Write-Host "  ✓ 安装  $name"
    $installed++
}

Write-Host ''
Write-Host "完成：新装 $installed 个，跳过 $skipped 个"
if ($backup) { Write-Host "原版本备份: $backup" }

if ($WithDeps) {
    Write-Host ''
    Write-Host '安装 Python 依赖…'
    python -m pip install -r (Join-Path $RepoRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'pip 安装失败，请检查 Python 环境' }
}

Write-Host ''
Write-Host '下一步：'
Write-Host "  1) 环境自检  python `"$RepoRoot\scripts\check_env.py`" --skills-dir `"$Target`""
Write-Host "  2) 未装依赖时手动执行  python -m pip install -r `"$RepoRoot\requirements.txt`""
Write-Host '  3) 重启 WorkBuddy（或重新加载技能），对助手说：处理 <发票目录> 的发票出报销台账'
