# Windows PowerShell version of the core build functionality
# This can be used as an alternative for Windows runners

param(
    [Parameter(Mandatory=$true)]
    [string]$Mode,
    
    [Parameter(Mandatory=$false)]
    [string]$BuildType = 'auto',
    
    [Parameter(Mandatory=$false)]
    [string]$WorkingDirectory = '.',
    
    [Parameter(Mandatory=$false)]
    [string]$ForceShowMyCodeFalse = 'true'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "🔨 Building AL extension in $Mode mode..." -ForegroundColor Green

# Set working directory
Set-Location $WorkingDirectory

# Check if app.json exists
if (-not (Test-Path "app.json")) {
    Write-Error "❌ app.json not found in current directory"
    exit 1
}

# Parse app.json
$appJson = Get-Content "app.json" | ConvertFrom-Json
$appName = $appJson.name
$appVersion = $appJson.version
$appPlatform = $appJson.platform
$appApplication = $appJson.application
$appRuntime = $appJson.runtime
$appTarget = $appJson.target ?? "Cloud"
$appDependencies = $appJson.dependencies ?? @()
$appIdRanges = $appJson.idRanges ?? @()

Write-Host "📦 Found AL app: $appName" -ForegroundColor Cyan
Write-Host "📊 Version: $appVersion" -ForegroundColor Cyan
Write-Host "🎯 Platform: $appPlatform" -ForegroundColor Cyan
Write-Host "📱 Application: $appApplication" -ForegroundColor Cyan

# Determine BC version
if ($BuildType -eq 'auto') {
    $bcMajorVersion = $appApplication.Split('.')[0]
    switch ($bcMajorVersion) {
        '17' { $bcVersion = 'bc17' }
        '18' { $bcVersion = 'bc18' }
        '19' { $bcVersion = 'bc19' }
        '20' { $bcVersion = 'bc20' }
        '21' { $bcVersion = 'bc21' }
        '22' { $bcVersion = 'bc22' }
        '23' { $bcVersion = 'bc23' }
        '24' { $bcVersion = 'bc24' }
        '25' { $bcVersion = 'bc25' }
        '26' { $bcVersion = 'bc26' }
        default { $bcVersion = 'bccloud' }
    }
} else {
    $bcVersion = $BuildType
}

Write-Host "🏢 Detected BC Version: $bcVersion" -ForegroundColor Cyan

# Handle version-specific app.json files
$versionSpecificAppJson = $null
switch ($bcVersion) {
    'bc17' { $versionSpecificAppJson = 'bc17_app.json' }
    'bc18' { $versionSpecificAppJson = 'bc18_app.json' }
    'bc19' { $versionSpecificAppJson = 'bc19_app.json' }
    'bc22' { $versionSpecificAppJson = 'bc22_app.json' }
    'bccloud' { $versionSpecificAppJson = 'cloud_app.json' }
}

if ($versionSpecificAppJson -and (Test-Path $versionSpecificAppJson)) {
    Write-Host "🔄 Switching to version-specific app.json: $versionSpecificAppJson" -ForegroundColor Yellow
    Copy-Item "app.json" "app.json.backup"
    Copy-Item $versionSpecificAppJson "app.json"
    
    # Re-parse the version-specific app.json
    $appJson = Get-Content "app.json" | ConvertFrom-Json
    $appName = $appJson.name
    $appVersion = $appJson.version
    $appPlatform = $appJson.platform
    $appApplication = $appJson.application
    $appRuntime = $appJson.runtime
    $appTarget = $appJson.target ?? "Cloud"
    $appDependencies = $appJson.dependencies ?? @()
    $appIdRanges = $appJson.idRanges ?? @()
}

# Check if this is an AppSource app
$isAppSourceApp = $false
foreach ($range in $appIdRanges) {
    if ($range.from -ge 100000) {
        $isAppSourceApp = $true
        Write-Host "🏪 Detected AppSource app (ID ranges include 100000+)" -ForegroundColor Green
        break
    }
}

if (-not $isAppSourceApp) {
    Write-Host "🏠 Detected internal/PTE app" -ForegroundColor Cyan
}

# Generate build version
function Get-BuildVersion {
    param($Mode)
    
    $eventName = $env:GITHUB_EVENT_NAME ?? 'push'
    $refName = $env:GITHUB_REF_NAME ?? 'main'
    $commitSha = $env:GITHUB_SHA ?? (git rev-parse HEAD 2>$null) ?? '0000000'
    
    $platformMajor = $appPlatform.Split('.')[0]
    $yearMinor = (Get-Date).ToString('yy')
    $daysBuild = [math]::Floor((Get-Date - (Get-Date '2020-01-01')).TotalDays)
    $minutesRevision = [math]::Floor((Get-Date).TimeOfDay.TotalMinutes)
    
    if ($Mode -eq 'build' -and (($eventName -eq 'push') -and (($refName -eq 'main') -or ($refName -eq 'master') -or ($refName -match '^bc[0-9]+$')))) {
        # Production build
        $buildVersion = "$platformMajor.$yearMinor.$daysBuild.$minutesRevision"
        Write-Host "🏗️ Production build version: $buildVersion" -ForegroundColor Green
    } elseif ($Mode -eq 'build' -and ($eventName -eq 'workflow_dispatch') -and ($refName -eq 'develop')) {
        # Development build
        $buildVersion = "99.$yearMinor.$daysBuild.$minutesRevision"
        Write-Host "🧪 Development build version: $buildVersion" -ForegroundColor Yellow
    } else {
        # Test compilation
        $buildVersion = "0.0.0.0"
        Write-Host "🧪 Test compilation version: $buildVersion" -ForegroundColor Cyan
    }
    
    return $buildVersion
}

$buildVersion = Get-BuildVersion -Mode $Mode

# Backup original app.json if not already backed up
if (-not (Test-Path "app.json.original")) {
    Copy-Item "app.json" "app.json.original"
}

# Update app.json for build
Write-Host "📝 Updating app.json for build..." -ForegroundColor Yellow
$appJson.version = $buildVersion

# Force showMyCode to false for customer repos if requested
if (($ForceShowMyCodeFalse -eq 'true') -and ($env:GITHUB_REPOSITORY -match '[Cc]ustomer')) {
    Write-Host "🔒 Forcing showMyCode to false for customer repository" -ForegroundColor Yellow
    $appJson | Add-Member -MemberType NoteProperty -Name 'showMyCode' -Value $false -Force
}

$appJson | ConvertTo-Json -Depth 10 | Set-Content "app.json"

# Clean up permission files based on runtime version
Write-Host "🧹 Cleaning up permission files based on runtime..." -ForegroundColor Yellow
$runtimeDecimal = [decimal]($appRuntime.Substring(0,3))

if ($runtimeDecimal -ge 8.1) {
    # Runtime 8.1+: Remove old XML permission files
    Get-ChildItem -Path "extensionsPermissionSet.xml" -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host "🗑️ Removed extensionsPermissionSet.xml files" -ForegroundColor Gray
} else {
    # Older runtime: Remove new AL permission files
    Get-ChildItem -Path "PermissionSet*.al" -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host "🗑️ Removed PermissionSet*.al files" -ForegroundColor Gray
}

# Find AL compiler
$alCompiler = $null
$alCompilerPaths = @(
    (Get-Command 'alc.exe' -ErrorAction SilentlyContinue).Source,
    "$env:USERPROFILE\.dotnet\tools\alc.exe",
    "$env:USERPROFILE\.vscode\extensions\ms-dynamics-smb.al-*\bin\win32\alc.exe"
)

foreach ($path in $alCompilerPaths) {
    if ($path -and (Test-Path $path)) {
        $alCompiler = $path
        break
    }
}

# Try to find from VS Code extensions
if (-not $alCompiler) {
    $vsCodeExtensions = Get-ChildItem "$env:USERPROFILE\.vscode\extensions\ms-dynamics-smb.al-*" -ErrorAction SilentlyContinue | Sort-Object Name -Descending
    foreach ($ext in $vsCodeExtensions) {
        $alcPath = Join-Path $ext.FullName "bin\win32\alc.exe"
        if (Test-Path $alcPath) {
            $alCompiler = $alcPath
            break
        }
    }
}

if (-not $alCompiler) {
    Write-Error "❌ AL compiler not found. Please install the AL extension for VS Code or the AL compiler via NuGet."
    exit 1
}

Write-Host "🔧 Using AL compiler: $alCompiler" -ForegroundColor Green

# Set up compilation parameters
$symbolsPath = Join-Path (Get-Location) ".symbols"
$cleanAppName = $appName -replace '[ -]', ''
$commitShort = ($env:GITHUB_SHA ?? '0000000').Substring(0, 7)
$outputFile = "${cleanAppName}_${buildVersion}_${commitShort}.app"
$errorLog = Join-Path (Get-Location) "errorLog.json"
$rulesetFile = Join-Path (Get-Location) "LincRuleSet.json"

# Remove previous error log
if (Test-Path $errorLog) {
    Remove-Item $errorLog -Force
}

# Create symbols directory (simplified for this example)
if (-not (Test-Path $symbolsPath)) {
    New-Item -ItemType Directory -Path $symbolsPath -Force | Out-Null
}

Write-Host "⚠️ Note: Symbol download not implemented in this PowerShell version" -ForegroundColor Yellow
Write-Host "Please ensure symbols are available in $symbolsPath" -ForegroundColor Yellow

# Build compiler arguments
$alcArgs = @(
    "/project:$((Get-Location).Path)"
    "/out:$outputFile"
    "/packagecachepath:$symbolsPath"
    "/target:$appTarget"
    "/loglevel:Normal"
    "/errorlog:$errorLog"
)

# Add ruleset if it exists
if (Test-Path $rulesetFile) {
    $alcArgs += "/ruleset:$rulesetFile"
    Write-Host "📋 Using ruleset: $rulesetFile" -ForegroundColor Cyan
}

# Add assembly probing paths
$alcArgs += "/assemblyprobingpaths:$env:WINDIR\Microsoft.NET\Framework\v4.0.30319"

Write-Host "🚀 Running AL compiler..." -ForegroundColor Green
Write-Host "Arguments: $($alcArgs -join ' ')" -ForegroundColor Gray

# Run compilation
$process = Start-Process -FilePath $alCompiler -ArgumentList $alcArgs -Wait -PassThru -NoNewWindow

if ($process.ExitCode -eq 0) {
    $compilationSuccess = $true
    Write-Host "✅ Compilation successful!" -ForegroundColor Green
    
    if (Test-Path $outputFile) {
        $appFilePath = Join-Path (Get-Location) $outputFile
        Write-Host "📦 App file created: $appFilePath" -ForegroundColor Green
        
        $buildNumber = "${buildVersion}_${commitShort}"
        Write-Host "📊 Build number: $buildNumber" -ForegroundColor Cyan
        
        # Set GitHub outputs (if running in GitHub Actions)
        if ($env:GITHUB_OUTPUT) {
            Add-Content -Path $env:GITHUB_OUTPUT -Value "compilation-success=true"
            Add-Content -Path $env:GITHUB_OUTPUT -Value "app-file-path=$appFilePath"
            Add-Content -Path $env:GITHUB_OUTPUT -Value "build-number=$buildNumber"
        }
    } else {
        Write-Host "⚠️ Compilation reported success but no output file found" -ForegroundColor Yellow
        $compilationSuccess = $false
    }
} else {
    $compilationSuccess = $false
    Write-Host "❌ Compilation failed!" -ForegroundColor Red
    
    if (Test-Path $errorLog) {
        Write-Host "📋 Error log:" -ForegroundColor Red
        Get-Content $errorLog | Write-Host -ForegroundColor Red
    }
    
    if ($env:GITHUB_OUTPUT) {
        Add-Content -Path $env:GITHUB_OUTPUT -Value "compilation-success=false"
    }
}

# Restore original app.json
Write-Host "🔄 Restoring original app.json..." -ForegroundColor Yellow
if (Test-Path "app.json.original") {
    Copy-Item "app.json.original" "app.json" -Force
    Remove-Item "app.json.original" -Force
    Write-Host "✅ Original app.json restored" -ForegroundColor Green
}

if ($compilationSuccess) {
    Write-Host "🎉 AL extension build completed successfully!" -ForegroundColor Green
    if ($appFilePath) {
        Write-Host "📊 Build summary:" -ForegroundColor Cyan
        Write-Host "  📦 App: $appName" -ForegroundColor Cyan
        Write-Host "  📋 Version: $buildVersion" -ForegroundColor Cyan
        Write-Host "  📁 File: $(Split-Path $appFilePath -Leaf)" -ForegroundColor Cyan
        Write-Host "  📏 Size: $([math]::Round((Get-Item $appFilePath).Length / 1MB, 2)) MB" -ForegroundColor Cyan
    }
    exit 0
} else {
    Write-Host "❌ AL extension build failed" -ForegroundColor Red
    exit 1
}