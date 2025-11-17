#!/bin/bash

# Install AL Compiler from NuGet
# Usage: install-al-compiler.sh <nuget-feed-url>

set -e

NUGET_FEED_URL="${1:-https://api.nuget.org/v3/index.json}"

echo "🔧 Installing AL Compiler from NuGet..."

# Create tools directory
mkdir -p $HOME/.local/share/al-tools
cd $HOME/.local/share/al-tools

# Install .NET if not available
if ! command -v dotnet &> /dev/null; then
    echo "Installing .NET SDK..."
    wget https://dot.net/v1/dotnet-install.sh -O dotnet-install.sh
    chmod +x dotnet-install.sh
    ./dotnet-install.sh --channel 8.0 --install-dir $HOME/.dotnet
    export PATH="$HOME/.dotnet:$PATH"
    echo "$HOME/.dotnet" >> $GITHUB_PATH
fi

# Create a global tool manifest if it doesn't exist
if [ ! -f .config/dotnet-tools.json ]; then
    dotnet new tool-manifest
fi

# Install AL compiler
echo "Installing Microsoft.Dynamics.BusinessCentral.Development.Tools..."
# This package is publicly available on nuget.org
dotnet tool install Microsoft.Dynamics.BusinessCentral.Development.Tools --global --add-source $NUGET_FEED_URL

# Verify installation
AL_COMPILER_PATH=$(which alc || echo "")
if [ -z "$AL_COMPILER_PATH" ]; then
    echo "❌ AL Compiler installation failed"
    exit 1
fi

echo "✅ AL Compiler installed successfully at: $AL_COMPILER_PATH"
echo "al-compiler-path=$AL_COMPILER_PATH" >> $GITHUB_OUTPUT

# Test the installation
echo "Testing AL Compiler installation..."
$AL_COMPILER_PATH --version || echo "AL Compiler ready (version info not available)"

# Also try to find it in the traditional .vscode extensions directory for compatibility
VSCODE_AL_PATH=""
if [ -d "$HOME/.vscode/extensions" ]; then
    VSCODE_AL_PATH=$(find $HOME/.vscode/extensions -name "ms-dynamics-smb.al-*" -type d | head -n 1)
    if [ -n "$VSCODE_AL_PATH" ] && [ -f "$VSCODE_AL_PATH/bin/linux/alc" ]; then
        echo "vscode-al-path=$VSCODE_AL_PATH/bin/linux" >> $GITHUB_OUTPUT
    fi
fi

echo "🎉 AL development environment setup complete"