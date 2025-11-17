#!/bin/bash

# Download symbols for AL compilation
# Usage: download-symbols.sh <bc-version> <dependencies-json> <linc-registry-url> <linc-token>

set -e

BC_VERSION="$1"
DEPENDENCIES_JSON="$2"
LINC_REGISTRY_URL="$3"
LINC_TOKEN="$4"

echo "📦 Downloading symbols for BC version: $BC_VERSION"

# Create symbols directory
SYMBOLS_DIR="$(pwd)/.symbols"
rm -rf "$SYMBOLS_DIR"
mkdir -p "$SYMBOLS_DIR"

# Get BC major version for symbol downloads
BC_MAJOR=$(echo "$BC_VERSION" | sed 's/bc//' | sed 's/cloud/26/')
if [ -z "$BC_MAJOR" ] || [ "$BC_MAJOR" = "cloud" ]; then
    BC_MAJOR="26"  # Default to latest cloud version
fi

echo "🔍 BC Major version: $BC_MAJOR"

# Download Microsoft symbols from NuGet
download_microsoft_symbols() {
    echo "📥 Downloading Microsoft Business Central symbols..."
    
    local symbols_package=""
    case $BC_MAJOR in
        17) symbols_package="Microsoft.BusinessCentral.17.0" ;;
        18) symbols_package="Microsoft.BusinessCentral.18.0" ;;
        19) symbols_package="Microsoft.BusinessCentral.19.0" ;;
        20) symbols_package="Microsoft.BusinessCentral.20.0" ;;
        21) symbols_package="Microsoft.BusinessCentral.21.0" ;;
        22) symbols_package="Microsoft.BusinessCentral.22.0" ;;
        23) symbols_package="Microsoft.BusinessCentral.23.0" ;;
        24) symbols_package="Microsoft.BusinessCentral.24.0" ;;
        25) symbols_package="Microsoft.BusinessCentral.25.0" ;;
        *) symbols_package="Microsoft.BusinessCentral.Current" ;;
    esac
    
    echo "📦 Downloading package: $symbols_package"
    
    # Create temp directory for package download
    TEMP_SYMBOLS_DIR=$(mktemp -d)
    cd "$TEMP_SYMBOLS_DIR"
    
    # Download the symbols package
    dotnet new console --force
    dotnet add package "$symbols_package" --no-restore || true
    dotnet restore --packages packages || true
    
    # Find and copy symbol files
    find packages -name "*.app" -exec cp {} "$SYMBOLS_DIR/" \; 2>/dev/null || true
    
    # Alternative: try direct download from public feeds
    if [ $(ls "$SYMBOLS_DIR"/*.app 2>/dev/null | wc -l) -eq 0 ]; then
        echo "⚠️ Direct package download failed, trying alternative sources..."
        
        # Try to download from Microsoft's public symbol repository
        SYMBOL_URLS=(
            "https://businesscentralapps.azureedge.net/symbols/dynamics365businesscentral/application-${BC_MAJOR}.0.0.0.app"
            "https://businesscentralapps.azureedge.net/symbols/dynamics365businesscentral/base-${BC_MAJOR}.0.0.0.app"
            "https://businesscentralapps.azureedge.net/symbols/dynamics365businesscentral/system-${BC_MAJOR}.0.0.0.app"
        )
        
        for url in "${SYMBOL_URLS[@]}"; do
            echo "📥 Trying to download: $(basename "$url")"
            curl -L -f "$url" -o "$SYMBOLS_DIR/$(basename "$url")" || echo "⚠️ Failed to download $(basename "$url")"
        done
    fi
    
    # Cleanup temp directory
    cd - > /dev/null
    rm -rf "$TEMP_SYMBOLS_DIR"
}

# Download dependency symbols
download_dependency_symbols() {
    echo "🔗 Processing AL dependencies..."
    
    # Check if we have dependencies
    if [ "$DEPENDENCIES_JSON" = "null" ] || [ "$DEPENDENCIES_JSON" = "[]" ]; then
        echo "ℹ️  No dependencies found"
        return
    fi
    
    # Parse dependencies
    echo "$DEPENDENCIES_JSON" | jq -c '.[]' | while read -r dep; do
        DEP_NAME=$(echo "$dep" | jq -r '.name')
        DEP_PUBLISHER=$(echo "$dep" | jq -r '.publisher // ""')
        DEP_ID=$(echo "$dep" | jq -r '.id // ""')
        DEP_VERSION=$(echo "$dep" | jq -r '.version // ""')
        
        echo "🔍 Processing dependency: $DEP_NAME"
        
        # Check if this is a Linc dependency
        if [[ "$DEP_NAME" =~ ^Linc.* ]] && [ -n "$LINC_REGISTRY_URL" ] && [ -n "$LINC_TOKEN" ]; then
            echo "📥 Downloading Linc dependency from registry..."
            download_linc_dependency "$DEP_NAME" "$DEP_VERSION"
        else
            echo "ℹ️  Skipping dependency $DEP_NAME (not a Linc dependency or no registry configured)"
        fi
    done
}

# Download Linc dependencies from GitHub NuGet registry
download_linc_dependency() {
    local dep_name="$1"
    local dep_version="$2"
    
    echo "📦 Downloading Linc dependency: $dep_name"
    
    # Create temp directory for dependency download
    TEMP_DEP_DIR=$(mktemp -d)
    cd "$TEMP_DEP_DIR"
    
    # Configure NuGet for GitHub registry
    cat > nuget.config << EOF
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <add key="github" value="$LINC_REGISTRY_URL" />
  </packageSources>
  <packageSourceCredentials>
    <github>
      <add key="Username" value="github" />
      <add key="ClearTextPassword" value="$LINC_TOKEN" />
    </github>
  </packageSourceCredentials>
</configuration>
EOF
    
    # Try to download the dependency
    dotnet new console --force
    
    # Convert dependency name to package name format
    PACKAGE_NAME=$(echo "$dep_name" | tr ' ' '.')
    
    if [ -n "$dep_version" ]; then
        dotnet add package "$PACKAGE_NAME" --version "$dep_version" --no-restore || true
    else
        dotnet add package "$PACKAGE_NAME" --no-restore || true
    fi
    
    dotnet restore --packages packages --configfile nuget.config || true
    
    # Find and copy dependency app files
    find packages -name "*.app" -exec cp {} "$SYMBOLS_DIR/" \; 2>/dev/null || echo "⚠️ No .app files found for $dep_name"
    
    # Cleanup
    cd - > /dev/null
    rm -rf "$TEMP_DEP_DIR"
}

# Execute symbol downloads
download_microsoft_symbols
download_dependency_symbols

# Report results
SYMBOL_COUNT=$(ls "$SYMBOLS_DIR"/*.app 2>/dev/null | wc -l)
echo "📊 Downloaded $SYMBOL_COUNT symbol files:"
ls -la "$SYMBOLS_DIR"/*.app 2>/dev/null || echo "⚠️ No symbol files found"

echo "symbols-path=$SYMBOLS_DIR" >> $GITHUB_OUTPUT
echo "symbol-count=$SYMBOL_COUNT" >> $GITHUB_OUTPUT

if [ "$SYMBOL_COUNT" -eq 0 ]; then
    echo "⚠️ Warning: No symbols were downloaded. Compilation may fail."
else
    echo "✅ Symbol download complete"
fi