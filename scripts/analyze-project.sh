#!/bin/bash

# Analyze AL project and determine build configuration
# Usage: analyze-project.sh <build-type>

set -e

BUILD_TYPE="${1:-auto}"

echo "📋 Analyzing AL project configuration..."

# Check if app.json exists
if [ ! -f "app.json" ]; then
    echo "❌ app.json not found in current directory"
    exit 1
fi

# Parse app.json
APP_NAME=$(jq -r '.name' app.json)
APP_VERSION=$(jq -r '.version' app.json)
APP_PLATFORM=$(jq -r '.platform' app.json)
APP_APPLICATION=$(jq -r '.application' app.json)
APP_RUNTIME=$(jq -r '.runtime' app.json)
APP_TARGET=$(jq -r '.target // "Cloud"' app.json)
APP_DEPENDENCIES=$(jq -c '.dependencies // []' app.json)
APP_ID_RANGES=$(jq -c '.idRanges // []' app.json)

echo "📦 Found AL app: $APP_NAME"
echo "📊 Version: $APP_VERSION"
echo "🎯 Platform: $APP_PLATFORM" 
echo "📱 Application: $APP_APPLICATION"
echo "⚙️  Runtime: $APP_RUNTIME"
echo "🏷️  Target: $APP_TARGET"

# Determine BC version from build type or auto-detect
if [ "$BUILD_TYPE" = "auto" ]; then
    BC_MAJOR_VERSION=$(echo $APP_APPLICATION | cut -d. -f1)
    case $BC_MAJOR_VERSION in
        17) BC_VERSION="bc17" ;;
        18) BC_VERSION="bc18" ;;
        19) BC_VERSION="bc19" ;;
        20) BC_VERSION="bc20" ;;
        21) BC_VERSION="bc21" ;;
        22) BC_VERSION="bc22" ;;
        23) BC_VERSION="bc23" ;;
        24) BC_VERSION="bc24" ;;
        25) BC_VERSION="bc25" ;;
        26) BC_VERSION="bc26" ;;
        *) BC_VERSION="bccloud" ;;
    esac
else
    BC_VERSION="$BUILD_TYPE"
fi

echo "🏢 Detected BC Version: $BC_VERSION"

# Handle version-specific app.json files
VERSION_SPECIFIC_APP_JSON=""
case $BC_VERSION in
    bc17) VERSION_SPECIFIC_APP_JSON="bc17_app.json" ;;
    bc18) VERSION_SPECIFIC_APP_JSON="bc18_app.json" ;;
    bc19) VERSION_SPECIFIC_APP_JSON="bc19_app.json" ;;
    bc22) VERSION_SPECIFIC_APP_JSON="bc22_app.json" ;;
    bccloud) VERSION_SPECIFIC_APP_JSON="cloud_app.json" ;;
esac

if [ -n "$VERSION_SPECIFIC_APP_JSON" ] && [ -f "$VERSION_SPECIFIC_APP_JSON" ]; then
    echo "🔄 Switching to version-specific app.json: $VERSION_SPECIFIC_APP_JSON"
    cp app.json app.json.backup
    cp "$VERSION_SPECIFIC_APP_JSON" app.json
    
    # Re-parse the version-specific app.json
    APP_NAME=$(jq -r '.name' app.json)
    APP_VERSION=$(jq -r '.version' app.json)
    APP_PLATFORM=$(jq -r '.platform' app.json)
    APP_APPLICATION=$(jq -r '.application' app.json)
    APP_RUNTIME=$(jq -r '.runtime' app.json)
    APP_TARGET=$(jq -r '.target // "Cloud"' app.json)
    APP_DEPENDENCIES=$(jq -c '.dependencies // []' app.json)
    APP_ID_RANGES=$(jq -c '.idRanges // []' app.json)
fi

# Check if this is an AppSource app (based on ID ranges)
IS_APPSOURCE_APP="false"
if echo "$APP_ID_RANGES" | jq -e '.[] | select(.from >= 100000)' > /dev/null; then
    IS_APPSOURCE_APP="true"
    echo "🏪 Detected AppSource app (ID ranges include 100000+)"
else
    echo "🏠 Detected internal/PTE app"
fi

# Generate clean app name for file operations
CLEAN_APP_NAME=$(echo "$APP_NAME" | tr -d ' -')

# Output all analysis results
echo "bc-version=$BC_VERSION" >> $GITHUB_OUTPUT
echo "app-name=$APP_NAME" >> $GITHUB_OUTPUT
echo "clean-app-name=$CLEAN_APP_NAME" >> $GITHUB_OUTPUT
echo "app-version=$APP_VERSION" >> $GITHUB_OUTPUT
echo "app-platform=$APP_PLATFORM" >> $GITHUB_OUTPUT
echo "app-application=$APP_APPLICATION" >> $GITHUB_OUTPUT
echo "app-runtime=$APP_RUNTIME" >> $GITHUB_OUTPUT
echo "app-target=$APP_TARGET" >> $GITHUB_OUTPUT
echo "is-appsource-app=$IS_APPSOURCE_APP" >> $GITHUB_OUTPUT

# Create simple structured outputs (avoid JSON escaping issues)
APP_INFO="name=$APP_NAME,cleanName=$CLEAN_APP_NAME,version=$APP_VERSION,platform=$APP_PLATFORM"
BUILD_CONFIG="bcVersion=$BC_VERSION,versionSpecificAppJson=$VERSION_SPECIFIC_APP_JSON"

echo "app-info=$APP_INFO" >> $GITHUB_OUTPUT
echo "build-config=$BUILD_CONFIG" >> $GITHUB_OUTPUT
echo "dependencies=$APP_DEPENDENCIES" >> $GITHUB_OUTPUT

echo "✅ Project analysis complete"