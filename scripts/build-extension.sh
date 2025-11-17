#!/bin/bash

# Build AL extension with version management
# Usage: build-extension.sh <mode> <app-info-json> <build-config-json> <force-showmycode-false>

set -e

MODE="$1"
APP_INFO_JSON="$2"
BUILD_CONFIG_JSON="$3"
FORCE_SHOWMYCODE_FALSE="$4"

echo "🔨 Building AL extension in $MODE mode..."

# Parse app info (handle both simple string and JSON formats)
if [[ "$APP_INFO_JSON" =~ ^name= ]]; then
    # Simple format: "name=TestApp,version=1.0.0.0,platform=22.0.0.0"
    APP_NAME=$(echo "$APP_INFO_JSON" | sed 's/.*name=\([^,]*\).*/\1/')
    APP_VERSION=$(echo "$APP_INFO_JSON" | sed 's/.*version=\([^,]*\).*/\1/')
    APP_PLATFORM=$(echo "$APP_INFO_JSON" | sed 's/.*platform=\([^,]*\).*/\1/')
    CLEAN_APP_NAME=$(echo "$APP_NAME" | sed 's/[^a-zA-Z0-9]//g')
    APP_APPLICATION="22.0.0.0"  # Default for BC22
    APP_RUNTIME="10.0"  # Default for BC22
    APP_TARGET="Cloud"  # Default
else
    # JSON format (fallback)
    APP_NAME=$(echo "$APP_INFO_JSON" | jq -r '.name // "Unknown"')
    CLEAN_APP_NAME=$(echo "$APP_INFO_JSON" | jq -r '.cleanName // "Unknown"')
    APP_VERSION=$(echo "$APP_INFO_JSON" | jq -r '.version // "1.0.0.0"')
    APP_PLATFORM=$(echo "$APP_INFO_JSON" | jq -r '.platform // "22.0.0.0"')
    APP_APPLICATION=$(echo "$APP_INFO_JSON" | jq -r '.application // "22.0.0.0"')
    APP_RUNTIME=$(echo "$APP_INFO_JSON" | jq -r '.runtime // "10.0"')
    APP_TARGET=$(echo "$APP_INFO_JSON" | jq -r '.target // "Cloud"')
fi

echo "📦 Building: $APP_NAME"
echo "📊 Original version: $APP_VERSION"

# Backup original app.json
cp app.json app.json.original

# Generate build version
generate_build_version() {
    local event_name="${GITHUB_EVENT_NAME:-push}"
    local ref_name="${GITHUB_REF_NAME:-main}"
    local commit_sha="${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo '0000000')}"
    
    # Extract version components
    local platform_major=$(echo "$APP_PLATFORM" | cut -d. -f1)
    local year_minor=$(date +'%y')
    local epoch_2020=1577836800  # 2020-01-01 00:00:00 UTC
    local current_epoch=$(date +%s)
    local days_build=$(( (current_epoch - epoch_2020) / 86400 ))
    local minutes_revision=$(( (current_epoch % 86400) / 60 ))
    
    if [ "$MODE" = "build" ] && ([ "$event_name" = "push" ] && ([ "$ref_name" = "main" ] || [ "$ref_name" = "master" ] || [[ "$ref_name" =~ ^bc[0-9]+$ ]])); then
        # Production build
        BUILD_VERSION="${platform_major}.${year_minor}.${days_build}.${minutes_revision}"
        echo "🏗️  Production build version: $BUILD_VERSION"
    elif [ "$MODE" = "build" ] && [ "$event_name" = "workflow_dispatch" ] && [ "$ref_name" = "develop" ]; then
        # Development build
        BUILD_VERSION="99.${year_minor}.${days_build}.${minutes_revision}"
        echo "🧪 Development build version: $BUILD_VERSION"
    else
        # Test compilation
        BUILD_VERSION="0.0.0.0"
        echo "🧪 Test compilation version: $BUILD_VERSION"
    fi
    
    echo "build-version=$BUILD_VERSION" >> $GITHUB_OUTPUT
}

# Update app.json for build
update_app_json_for_build() {
    echo "📝 Updating app.json for build..."
    
    # Update version in app.json
    jq --arg version "$BUILD_VERSION" '.version = $version' app.json > app.json.tmp && mv app.json.tmp app.json
    
    # Force showMyCode to false for customer repos if requested
    if [ "$FORCE_SHOWMYCODE_FALSE" = "true" ] && [[ "$GITHUB_REPOSITORY" =~ [Cc]ustomer ]]; then
        echo "🔒 Forcing showMyCode to false for customer repository"
        jq '.showMyCode = false' app.json > app.json.tmp && mv app.json.tmp app.json
    fi
    
    echo "✅ app.json updated with build configuration"
}

# Clean up permission files based on runtime version
cleanup_permission_files() {
    echo "🧹 Cleaning up permission files based on runtime..."
    
    local runtime_version=$(echo "$APP_RUNTIME" | cut -d. -f1-2)
    local runtime_decimal=$(echo "$runtime_version" | tr -d '.' | grep '^[0-9]*$' || echo "100")
    
    if [ "$runtime_decimal" -ge 81 ] 2>/dev/null; then
        # Runtime 8.1+: Remove old XML permission files
        find . -name "extensionsPermissionSet.xml" -delete 2>/dev/null || true
        echo "🗑️  Removed extensionsPermissionSet.xml files"
    else
        # Older runtime: Remove new AL permission files
        find . -name "PermissionSet*.al" -delete 2>/dev/null || true
        echo "🗑️  Removed PermissionSet*.al files"
    fi
}

# Perform AL compilation
compile_al_extension() {
    echo "⚙️  Starting AL compilation..."
    
    # Find AL compiler
    AL_COMPILER=""
    if command -v AL &> /dev/null; then
        AL_COMPILER="AL"
    elif [ -f "$HOME/.dotnet/tools/AL" ]; then
        AL_COMPILER="$HOME/.dotnet/tools/AL"
    else
        echo "❌ AL compiler not found"
        exit 1
    fi
    
    echo "🔧 Using AL compiler: $AL_COMPILER"
    
    # Set up compilation parameters
    local symbols_path="$(pwd)/.symbols"
    local output_file="${CLEAN_APP_NAME}_${BUILD_VERSION}_$(echo $GITHUB_SHA | cut -c1-7).app"
    local error_log="$(pwd)/errorLog.json"
    local ruleset_file="$(pwd)/LincRuleSet.json"
    
    # Remove previous error log
    rm -f "$error_log"
    
    # Build compiler arguments
    local alc_args=(
        "/project:$(pwd)"
        "/out:$output_file"
        "/packagecachepath:$symbols_path"
        "/target:$APP_TARGET"
        "/loglevel:Normal"
        "/errorlog:$error_log"
    )
    
    # Add ruleset if it exists
    if [ -f "$ruleset_file" ]; then
        alc_args+=("/ruleset:$ruleset_file")
        echo "📋 Using ruleset: $ruleset_file"
    fi
    
    # Add assembly probing paths (Linux equivalent)
    alc_args+=("/assemblyprobingpaths:/usr/lib/mono/4.5")
    
    echo "🚀 Running AL compiler with arguments:"
    printf '%s\n' "${alc_args[@]}"
    
    # Run compilation
    if "$AL_COMPILER" "${alc_args[@]}"; then
        COMPILATION_SUCCESS="true"
        echo "✅ Compilation successful!"
        
        # Check if output file was created
        if [ -f "$output_file" ]; then
            APP_FILE_PATH="$(pwd)/$output_file"
            echo "📦 App file created: $APP_FILE_PATH"
            
            # Generate build number for output
            local commit_short=$(echo $GITHUB_SHA | cut -c1-7)
            BUILD_NUMBER="${BUILD_VERSION}_${commit_short}"
            
        else
            echo "⚠️ Compilation reported success but no output file found"
            COMPILATION_SUCCESS="false"
        fi
    else
        COMPILATION_SUCCESS="false"
        echo "❌ Compilation failed!"
        
        # Display error log if it exists
        if [ -f "$error_log" ]; then
            echo "📋 Error log:"
            cat "$error_log"
        fi
    fi
    
    # Set outputs
    echo "compilation-success=$COMPILATION_SUCCESS" >> $GITHUB_OUTPUT
    echo "app-file-path=${APP_FILE_PATH:-}" >> $GITHUB_OUTPUT
    echo "build-number=${BUILD_NUMBER:-}" >> $GITHUB_OUTPUT
}

# Restore original app.json
restore_app_json() {
    echo "🔄 Restoring original app.json..."
    if [ -f "app.json.original" ]; then
        mv app.json.original app.json
        echo "✅ Original app.json restored"
    fi
}

# Main execution flow
generate_build_version
update_app_json_for_build
cleanup_permission_files
compile_al_extension

# Always restore app.json, regardless of compilation result
restore_app_json

if [ "$COMPILATION_SUCCESS" = "true" ]; then
    echo "🎉 AL extension build completed successfully!"
    if [ -n "${APP_FILE_PATH:-}" ]; then
        echo "📊 Build summary:"
        echo "  📦 App: $APP_NAME"
        echo "  📋 Version: $BUILD_VERSION"
        echo "  📁 File: $(basename "$APP_FILE_PATH")"
        echo "  📏 Size: $(du -h "$APP_FILE_PATH" | cut -f1)"
    fi
else
    echo "❌ AL extension build failed"
    exit 1
fi