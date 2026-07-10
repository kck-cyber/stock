param(
    [switch]$RunBuild,
    [switch]$GenerateAssets,
    [switch]$BumpBuildNumber
)

$ErrorActionPreference = "Stop"

$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $AppDir
$ConfigPath = Join-Path $AppDir "app_config.json"
$OutputDir = Join-Path $ProjectRoot "dist_mobile"
$AssetGenerator = Join-Path $AppDir "tools\generate_assets.py"

if (-not (Test-Path $ConfigPath)) {
    throw "app_config.json not found: $ConfigPath"
}

$Config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

if ($BumpBuildNumber) {
    $CurrentBuildNumber = 0

    if ($Config.build_number) {
        $CurrentBuildNumber = [int]$Config.build_number
    }

    $Config.build_number = [string]($CurrentBuildNumber + 1)
    $Config |
        ConvertTo-Json -Depth 10 |
        Set-Content -Path $ConfigPath -Encoding UTF8

    Write-Host "Build number bumped to $($Config.build_number)"
}

if ($GenerateAssets) {
    if (-not (Test-Path $AssetGenerator)) {
        throw "Asset generator not found: $AssetGenerator"
    }

    python $AssetGenerator
}

$BuildArgs = @(
    "build",
    "apk",
    $AppDir,
    "--output", $OutputDir,
    "--project", $Config.project_name,
    "--artifact", $Config.artifact_name,
    "--description", $Config.description,
    "--product", $Config.app_name,
    "--org", $Config.org_name,
    "--bundle-id", $Config.bundle_id,
    "--company", $Config.company_name,
    "--build-version", $Config.build_version,
    "--build-number", $Config.build_number,
    "--splash-color", $Config.splash_color,
    "--android-adaptive-icon-background", $Config.android_adaptive_icon_background,
    "--yes"
)

$Config.android_permissions | ForEach-Object {
    $BuildArgs += @("--android-permissions", $_)
}

Write-Host "APK build command:"
Write-Host "flet $($BuildArgs -join ' ')"
Write-Host ""
Write-Host "Assets:"
Write-Host "icon: $($Config.icon_path)"
Write-Host "splash: $($Config.splash_path)"

if ($RunBuild) {
    flet @BuildArgs
} else {
    Write-Host ""
    Write-Host "Dry run only. To build APK:"
    Write-Host "powershell -ExecutionPolicy Bypass -File mobile_app\build_apk.ps1 -RunBuild"
    Write-Host ""
    Write-Host "To regenerate assets before build:"
    Write-Host "powershell -ExecutionPolicy Bypass -File mobile_app\build_apk.ps1 -GenerateAssets"
    Write-Host ""
    Write-Host "To build an update APK with a higher build number:"
    Write-Host "powershell -ExecutionPolicy Bypass -File mobile_app\build_apk.ps1 -BumpBuildNumber -RunBuild"
}
