param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistDir = Join-Path $Root "dist\MorningStockAssistantPro"
$ExePath = Join-Path $DistDir "MorningStockAssistantPro.exe"
$ReleaseDir = Join-Path $Root "releases"
$Stamp = Get-Date -Format "yyyyMMdd_HHmm"
$InitPath = Join-Path $Root "src\morning_stock_assistant\__init__.py"
$Version = "0.0.0"

if (Test-Path $InitPath) {
    $VersionMatch = Select-String `
        -Path $InitPath `
        -Pattern '__version__\s*=\s*"([^"]+)"' `
        | Select-Object -First 1

    if ($VersionMatch) {
        $Version = $VersionMatch.Matches[0].Groups[1].Value
    }
}

$PackageName = "MorningStockAssistantPro_v$Version`_$Stamp"
$StageDir = Join-Path $ReleaseDir $PackageName
$ZipPath = Join-Path $ReleaseDir "$PackageName.zip"

Set-Location $Root

if (-not $SkipBuild) {
    python -m py_compile `
        main.py `
        src\morning_stock_assistant\gui\main_window.py `
        src\morning_stock_assistant\shared\alert_engine.py

    python -m PyInstaller --noconfirm MorningStockAssistantPro.spec
}

if (-not (Test-Path $ExePath)) {
    throw "EXE file not found: $ExePath"
}

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

if (Test-Path $StageDir) {
    throw "Release stage already exists: $StageDir"
}

New-Item -ItemType Directory -Path $StageDir | Out-Null
Copy-Item -Path (Join-Path $DistDir "*") -Destination $StageDir -Recurse

$Readme = @"
Morning Stock Assistant Pro
버전: v$Version

실행 방법
1. 이 zip 파일을 원하는 폴더에 압축 해제합니다.
2. MorningStockAssistantPro.exe를 실행합니다.
3. _internal 폴더는 exe와 같은 위치에 있어야 합니다.

업데이트 방법
- 기존 폴더에 압축을 풀어 덮어써도 됩니다.
- 관심종목, 보유정보, 알림 설정은 storage 폴더에 저장됩니다.
- 이 배포 zip에는 storage 폴더를 넣지 않았으므로 기존 데이터는 보존됩니다.
- 그래도 중요한 업데이트 전에는 프로그램의 백업 기능으로 먼저 백업하는 것을 권장합니다.

생성 시각: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@

Set-Content -Path (Join-Path $StageDir "README.txt") -Value $Readme -Encoding UTF8

$ReleaseNotesPath = Join-Path $Root "RELEASE_NOTES.md"

if (Test-Path $ReleaseNotesPath) {
    Copy-Item -Path $ReleaseNotesPath -Destination (Join-Path $StageDir "RELEASE_NOTES.md")
}

$VersionInfo = @{
    app = "Morning Stock Assistant Pro"
    version = $Version
    package = $PackageName
    created_at = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
}

$VersionInfo `
    | ConvertTo-Json -Depth 3 `
    | Set-Content -Path (Join-Path $StageDir "version.json") -Encoding UTF8

if (Test-Path $ZipPath) {
    throw "Release zip already exists: $ZipPath"
}

Compress-Archive -Path (Join-Path $StageDir "*") -DestinationPath $ZipPath

Write-Host "Release package created:"
Write-Host $ZipPath
