#!/bin/bash

# Code sign AL extension using Azure Key Vault
# Usage: code-sign.sh <app-file-path> <vault-uri> <cert-name> <app-id> <app-secret> <tenant-id>

set -e

APP_FILE_PATH="$1"
VAULT_URI="$2"
CERT_NAME="$3"
APP_ID="$4"
APP_SECRET="$5"
TENANT_ID="$6"

echo "✍️  Code signing app file: $(basename "$APP_FILE_PATH")"

# Validate inputs
if [ -z "$APP_FILE_PATH" ] || [ ! -f "$APP_FILE_PATH" ]; then
    echo "❌ App file not found: $APP_FILE_PATH"
    exit 1
fi

if [ -z "$VAULT_URI" ] || [ -z "$CERT_NAME" ] || [ -z "$APP_ID" ] || [ -z "$APP_SECRET" ] || [ -z "$TENANT_ID" ]; then
    echo "⚠️ Code signing credentials not provided. Skipping code signing."
    echo "code-signing-skipped=true" >> $GITHUB_OUTPUT
    exit 0
fi

echo "🔑 Code signing configuration:"
echo "  🏛️  Vault: $VAULT_URI"
echo "  📜 Certificate: $CERT_NAME"
echo "  🆔 App ID: $APP_ID"
echo "  🏢 Tenant: $TENANT_ID"

# Install Azure Sign Tool if not present
install_azure_sign_tool() {
    if ! command -v azuresigntool &> /dev/null; then
        echo "📥 Installing Azure Sign Tool..."
        dotnet tool install --global azuresigntool --version 4.0.1
        echo "✅ Azure Sign Tool installed"
    else
        echo "✅ Azure Sign Tool already available"
    fi
}

# Perform code signing
sign_app_file() {
    echo "🔐 Starting code signing process..."
    
    # Azure Sign Tool arguments
    local sign_args=(
        "sign"
        "-kvu" "$VAULT_URI"
        "-kvc" "$CERT_NAME"
        "-kvi" "$APP_ID"
        "-kvs" "$APP_SECRET"
        "-kvt" "$TENANT_ID"
        "-tr" "http://timestamp.digicert.com"
        "-v"
        "$APP_FILE_PATH"
    )
    
    echo "🚀 Running azuresigntool with arguments:"
    echo "azuresigntool sign -kvu [VAULT] -kvc [CERT] -kvi [APP_ID] -kvs [HIDDEN] -kvt [TENANT] -tr [TIMESTAMP] -v [FILE]"
    
    # Execute signing
    if azuresigntool "${sign_args[@]}"; then
        echo "✅ Code signing successful!"
        echo "code-signing-success=true" >> $GITHUB_OUTPUT
        
        # Verify the signature
        verify_signature
        
    else
        echo "❌ Code signing failed!"
        echo "code-signing-success=false" >> $GITHUB_OUTPUT
        exit 1
    fi
}

# Verify the code signature
verify_signature() {
    echo "🔍 Verifying code signature..."
    
    # On Linux, we can use osslsigncode to verify if available
    if command -v osslsigncode &> /dev/null; then
        if osslsigncode verify "$APP_FILE_PATH"; then
            echo "✅ Signature verification successful"
            echo "signature-verified=true" >> $GITHUB_OUTPUT
        else
            echo "⚠️ Signature verification failed"
            echo "signature-verified=false" >> $GITHUB_OUTPUT
        fi
    else
        echo "ℹ️ osslsigncode not available for signature verification on Linux"
        echo "signature-verified=unknown" >> $GITHUB_OUTPUT
    fi
}

# Alternative: Use Windows runner for code signing if needed
check_windows_requirement() {
    if [ "$RUNNER_OS" != "Windows" ]; then
        echo "⚠️ Warning: Code signing is typically more reliable on Windows runners"
        echo "Consider using a Windows runner for the code signing step if you encounter issues"
    fi
}

# Main execution
check_windows_requirement
install_azure_sign_tool
sign_app_file

echo "🎉 Code signing process completed!"