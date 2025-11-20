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

# Set up DOTNET_ROOT for subsequent steps - critical for AL compiler
export DOTNET_ROOT="$HOME/.dotnet"
echo "DOTNET_ROOT=$HOME/.dotnet" >> $GITHUB_ENV

# Add dotnet tools to PATH for subsequent steps
echo "$HOME/.dotnet" >> $GITHUB_PATH
echo "$HOME/.dotnet/tools" >> $GITHUB_PATH
export PATH="$DOTNET_ROOT:$DOTNET_ROOT/tools:$PATH"

# Verify installation
AL_COMPILER_PATH=$(which AL || echo "")
if [ -z "$AL_COMPILER_PATH" ]; then
    echo "❌ AL Compiler not found in PATH. Adding dotnet tools to PATH..."
    export PATH="$DOTNET_ROOT:$DOTNET_ROOT/tools:$PATH"
    AL_COMPILER_PATH=$(which AL || echo "")
    if [ -z "$AL_COMPILER_PATH" ]; then
        echo "❌ AL Compiler installation failed"
        exit 1
    fi
fi

echo "✅ AL Compiler installed successfully at: $AL_COMPILER_PATH"
echo "al-compiler-path=$AL_COMPILER_PATH" >> $GITHUB_OUTPUT

# Test the installation with proper DOTNET_ROOT
echo "Testing AL Compiler installation..."
DOTNET_ROOT="$HOME/.dotnet" $AL_COMPILER_PATH --help > /dev/null 2>&1 && echo "AL Compiler ready" || echo "AL Compiler ready (help not available)"

# Also try to find it in the traditional .vscode extensions directory for compatibility
VSCODE_AL_PATH=""
if [ -d "$HOME/.vscode/extensions" ]; then
    VSCODE_AL_PATH=$(find $HOME/.vscode/extensions -name "ms-dynamics-smb.al-*" -type d | head -n 1)
    if [ -n "$VSCODE_AL_PATH" ] && [ -f "$VSCODE_AL_PATH/bin/linux/alc" ]; then
        echo "vscode-al-path=$VSCODE_AL_PATH/bin/linux" >> $GITHUB_OUTPUT
    fi
fi

echo "🎉 AL development environment setup complete"