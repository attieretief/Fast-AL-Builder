#!/bin/bash

# Publish AL extension to AppSource
# Usage: publish-appsource.sh <app-info-json> <app-file-path> <tenant-id> <client-id> <client-secret>

set -e

APP_INFO_JSON="$1"
APP_FILE_PATH="$2"
TENANT_ID="$3"
CLIENT_ID="$4"
CLIENT_SECRET="$5"

echo "🏪 Publishing to Microsoft AppSource..."

# Parse app info
APP_NAME=$(echo "$APP_INFO_JSON" | jq -r '.name')
IS_APPSOURCE_APP=$(echo "$APP_INFO_JSON" | jq -r '.isAppSource')

if [ "$IS_APPSOURCE_APP" != "true" ]; then
    echo "ℹ️ App is not configured for AppSource (no AppSource ID ranges). Skipping AppSource publication."
    exit 0
fi

# Validate inputs
if [ -z "$APP_FILE_PATH" ] || [ ! -f "$APP_FILE_PATH" ]; then
    echo "❌ App file not found: $APP_FILE_PATH"
    exit 1
fi

if [ -z "$TENANT_ID" ] || [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ]; then
    echo "❌ AppSource credentials not provided. Cannot publish to AppSource."
    exit 1
fi

echo "📦 App to publish: $APP_NAME"
echo "📁 App file: $(basename "$APP_FILE_PATH")"
echo "🆔 Client ID: $CLIENT_ID"
echo "🏢 Tenant ID: $TENANT_ID"

# Install required PowerShell modules (using PowerShell Core on Linux)
install_powershell_modules() {
    echo "📥 Installing required PowerShell modules..."
    
    # Check if PowerShell is available
    if ! command -v pwsh &> /dev/null; then
        echo "📥 Installing PowerShell Core..."
        
        # Install PowerShell on Ubuntu
        wget -q https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb
        sudo dpkg -i packages-microsoft-prod.deb
        sudo apt-get update
        sudo apt-get install -y powershell
        
        echo "✅ PowerShell Core installed"
    fi
    
    # Install BcContainerHelper module
    pwsh -Command "
        if (-not (Get-Module -ListAvailable -Name BcContainerHelper)) {
            Install-Module -Name BcContainerHelper -Force -AllowClobber -Scope CurrentUser
            Write-Host '✅ BcContainerHelper module installed'
        } else {
            Write-Host '✅ BcContainerHelper module already available'
        }
    "
}

# Create PowerShell script for AppSource publishing
create_appsource_script() {
    cat > appsource-publish.ps1 << 'EOF'
param(
    [Parameter(Mandatory=$true)]
    [string]$AppFilePath,
    
    [Parameter(Mandatory=$true)]
    [string]$AppName,
    
    [Parameter(Mandatory=$true)]
    [string]$TenantId,
    
    [Parameter(Mandatory=$true)]
    [string]$ClientId,
    
    [Parameter(Mandatory=$true)]
    [string]$ClientSecret
)

# Import required modules
Import-Module BcContainerHelper -Force

try {
    Write-Host "🔐 Creating authentication context..."
    
    # Create authentication context
    $authContext = New-BcAuthContext `
        -clientID $ClientId `
        -clientSecret $ClientSecret `
        -Scopes "https://api.partner.microsoft.com/.default" `
        -TenantID $TenantId
    
    Write-Host "✅ Authentication context created successfully"
    
    # Get existing AppSource products
    Write-Host "🔍 Retrieving AppSource products..."
    $products = Get-AppSourceProduct -authContext $authContext -silent
    
    # Find the product by name (remove "Linc " prefix for matching)
    $productName = $AppName -replace "^Linc\s+", ""
    $product = $products | Where-Object { $_.name -eq $productName }
    
    if (-not $product) {
        Write-Host "❌ Unable to find existing AppSource product: $productName"
        Write-Host "📋 Available products:"
        $products | ForEach-Object { Write-Host "  - $($_.name)" }
        exit 1
    }
    
    Write-Host "✅ Found AppSource product: $($product.name) (ID: $($product.id))"
    
    # Check for library dependencies
    $hasLibraryFile = $false
    $libraryAppFiles = @()
    
    # Parse app.json to check for Linc Extension Access dependency
    if (Test-Path "app.json") {
        $appJson = Get-Content "app.json" | ConvertFrom-Json
        foreach ($dependency in $appJson.dependencies) {
            if ($dependency.name -replace "\s+", "" -eq "LincExtensionAccess") {
                $hasLibraryFile = $true
                Write-Host "🔗 Detected Linc Extension Access dependency"
                
                # Look for library app file in current directory or symbols
                $libAppPattern = "*ExtensionAccess*.app"
                $libAppFile = Get-ChildItem $libAppPattern -ErrorAction SilentlyContinue | Select-Object -First 1
                
                if ($libAppFile) {
                    $libraryAppFiles += $libAppFile.FullName
                    Write-Host "📦 Found library app file: $($libAppFile.Name)"
                } else {
                    Write-Host "⚠️ Library dependency detected but library app file not found"
                }
                break
            }
        }
    }
    
    # Submit to AppSource
    Write-Host "🚀 Submitting to AppSource..."
    
    if ($hasLibraryFile -and $libraryAppFiles.Count -gt 0) {
        Write-Host "📚 Submitting with library files..."
        New-AppSourceSubmission -authContext $authContext -productId $product.id -appFile $AppFilePath -libraryAppFiles $libraryAppFiles -autoPromote -doNotWait
    } else {
        Write-Host "📦 Submitting app only..."
        New-AppSourceSubmission -authContext $authContext -productId $product.id -appFile $AppFilePath -autoPromote -doNotWait
    }
    
    Write-Host "✅ AppSource submission initiated successfully"
    Write-Host "ℹ️ The submission will be processed asynchronously by Microsoft"
    
} catch {
    Write-Host "❌ AppSource submission failed: $($_.Exception.Message)"
    Write-Host "📋 Error details: $($_.Exception.InnerException.Message)"
    exit 1
}
EOF
}

# Execute AppSource publishing
publish_to_appsource() {
    echo "🚀 Executing AppSource publication..."
    
    create_appsource_script
    
    # Run the PowerShell script
    pwsh -File appsource-publish.ps1 \
        -AppFilePath "$APP_FILE_PATH" \
        -AppName "$APP_NAME" \
        -TenantId "$TENANT_ID" \
        -ClientId "$CLIENT_ID" \
        -ClientSecret "$CLIENT_SECRET"
    
    local exit_code=$?
    
    # Clean up the script
    rm -f appsource-publish.ps1
    
    if [ $exit_code -eq 0 ]; then
        echo "✅ AppSource publication completed successfully"
        echo "appsource-published=true" >> $GITHUB_OUTPUT
    else
        echo "❌ AppSource publication failed"
        echo "appsource-published=false" >> $GITHUB_OUTPUT
        exit 1
    fi
}

# Main execution
install_powershell_modules
publish_to_appsource

echo "🎉 AppSource publication process completed!"