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
echo "Installing Microsoft.Dynamics.BusinessCentral.Al.Compiler..."
# Use Microsoft's NuGet feed for AL compiler if default feed is used
if [ "$NUGET_FEED_URL" = "https://api.nuget.org/v3/index.json" ]; then
    MICROSOFT_FEED="https://pkgs.dev.azure.com/ms/BCTech/_packaging/bc-compiler/nuget/v3/index.json"
    dotnet tool install Microsoft.Dynamics.BusinessCentral.Al.Compiler --global --add-source $MICROSOFT_FEED
else
    dotnet tool install Microsoft.Dynamics.BusinessCentral.Al.Compiler --global --add-source $NUGET_FEED_URL
fi

# Verify installation
AL_COMPILER_PATH=$(which alc || echo "")
if [ -z "$AL_COMPILER_PATH" ]; then
    echo "❌ AL Compiler installation failed"
    exit 1
fi

echo "✅ AL Compiler installed successfully at: $AL_COMPILER_PATH"
echo "al-compiler-path=$AL_COMPILER_PATH" >> $GITHUB_OUTPUT

# Also try to find it in the traditional .vscode extensions directory for compatibility
VSCODE_AL_PATH=""
if [ -d "$HOME/.vscode/extensions" ]; then
    VSCODE_AL_PATH=$(find $HOME/.vscode/extensions -name "ms-dynamics-smb.al-*" -type d | head -n 1)
    if [ -n "$VSCODE_AL_PATH" ] && [ -f "$VSCODE_AL_PATH/bin/linux/alc" ]; then
        echo "vscode-al-path=$VSCODE_AL_PATH/bin/linux" >> $GITHUB_OUTPUT
    fi
fi

echo "🎉 AL development environment setup complete"