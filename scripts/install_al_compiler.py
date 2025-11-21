#!/usr/bin/env python3
"""
Lean AL Compiler Installer
Quickly install AL Compiler from NuGet (requires .NET SDK pre-installed)
"""

import os
import sys
import subprocess
from pathlib import Path
import shutil


class ALCompilerInstaller:
    def __init__(self):
        self.home_dir = Path.home()
        self.dotnet_tools_dir = self.home_dir / ".dotnet" / "tools"
        self.is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
        self.is_ubuntu = os.environ.get('RUNNER_OS') == 'Linux' or 'ubuntu' in os.environ.get('RUNNER_NAME', '').lower()
    
    def log(self, message: str, color: str = None):
        """Print colored log message"""
        colors = {
            "green": "\033[92m",
            "yellow": "\033[93m", 
            "red": "\033[91m",
            "cyan": "\033[96m",
            "reset": "\033[0m"
        }
        
        if color and color in colors:
            print(f"{colors[color]}{message}{colors['reset']}")
        else:
            print(message)
    
    def check_dotnet(self) -> bool:
        """Check if .NET is available"""
        try:
            # Use shorter timeout in CI environments
            timeout = 3 if self.is_github_actions else 5
            result = subprocess.run(['dotnet', '--version'], 
                                  capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.log(f"✅ .NET SDK found: {version}", "green")
                
                # Log additional info for GitHub Actions
                if self.is_github_actions:
                    self.log(f"🤖 Running on GitHub Actions ({os.environ.get('RUNNER_OS', 'Unknown')})", "cyan")
                
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        self.log("❌ .NET SDK not found. Please install .NET SDK first.", "red")
        if self.is_github_actions:
            self.log("💡 For GitHub Actions, use: actions/setup-dotnet@v3", "cyan")
        else:
            self.log("💡 Install from: https://dotnet.microsoft.com/download", "cyan")
        return False
    
    def install_al_compiler(self) -> bool:
        """Install AL Compiler from NuGet"""
        self.log("🔧 Installing AL Compiler...", "cyan")
        
        # Check if .NET is available
        if not self.check_dotnet():
            return False
        
        # First check if it's already installed
        if self.verify_installation():
            self.log("✅ AL Compiler is already installed and working!", "green")
            return True
        
        # Try global install using only the public NuGet feed
        self.log("📦 Installing Microsoft.Dynamics.BusinessCentral.Development.Tools globally...", "yellow")
        
        # Use faster timeouts for CI environments
        env = os.environ.copy()
        if self.is_github_actions:
            env['DOTNET_CLI_TELEMETRY_OPTOUT'] = '1'  # Disable telemetry in CI
            env['DOTNET_SKIP_FIRST_TIME_EXPERIENCE'] = '1'  # Skip first-time setup
        
        cmd = [
            'dotnet', 'tool', 'install', 
            'Microsoft.Dynamics.BusinessCentral.Development.Tools',
            '--global',
            '--add-source', 'https://api.nuget.org/v3/index.json',
            '--ignore-failed-sources'
        ]
        
        # Add verbosity for CI debugging if needed
        if self.is_github_actions and os.environ.get('RUNNER_DEBUG') == '1':
            cmd.extend(['--verbosity', 'detailed'])
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        if result.returncode == 0:
            self.log("✅ AL Compiler installed successfully!", "green")
            return self.verify_installation()
        elif "already installed" in result.stderr.lower() or "conflicts with an existing command" in result.stderr.lower():
            self.log("🔄 AL Compiler already installed, updating...", "yellow")
            return self._update_al_compiler()
        else:
            self.log(f"❌ Failed to install AL Compiler: {result.stderr.strip()}", "red")
            return False
    
    def _update_al_compiler(self) -> bool:
        """Update existing AL Compiler installation"""
        env = os.environ.copy()
        if self.is_github_actions:
            env['DOTNET_CLI_TELEMETRY_OPTOUT'] = '1'
            env['DOTNET_SKIP_FIRST_TIME_EXPERIENCE'] = '1'
        
        cmd = [
            'dotnet', 'tool', 'update',
            'Microsoft.Dynamics.BusinessCentral.Development.Tools',
            '--global',
            '--add-source', 'https://api.nuget.org/v3/index.json',
            '--ignore-failed-sources'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        if result.returncode == 0:
            self.log("✅ AL Compiler updated successfully!", "green")
            return self.verify_installation()
        else:
            self.log(f"❌ Failed to update AL Compiler: {result.stderr.strip()}", "red")
            return False
    
    def verify_installation(self) -> bool:
        """Verify AL Compiler installation"""
        self.log("🔍 Verifying AL Compiler installation...", "yellow")
        
        # Check if AL compiler is available via dotnet tool
        result = subprocess.run(['dotnet', 'tool', 'list', '--global'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and 'microsoft.dynamics.businesscentral.development.tools' in result.stdout.lower():
            self.log("✅ AL Compiler is installed as a global tool!", "green")
            
            # Try to find AL compiler executable
            al_path = shutil.which('AL')
            if al_path:
                self.log(f"✅ AL Compiler executable found at: {al_path}", "green")
                
                # Add to GitHub PATH if running in GitHub Actions
                if self.is_github_actions:
                    github_path = os.environ.get('GITHUB_PATH')
                    if github_path and str(self.dotnet_tools_dir) not in os.environ.get('PATH', ''):
                        with open(github_path, 'a') as f:
                            f.write(f"{self.dotnet_tools_dir}\n")
                        self.log("📝 Added .NET tools to GitHub PATH", "cyan")
                
                return True
            else:
                self.log("⚠️ AL Compiler installed but executable not found in PATH", "yellow")
                if self.is_github_actions:
                    self.log("💡 PATH will be updated for subsequent steps", "cyan")
                else:
                    self.log("💡 You may need to restart your shell", "cyan")
                return True  # Still consider it successful since the tool is installed
        
        self.log("❌ AL Compiler not found in global tools", "red")
        return False


def main():
    """Main entry point"""
    installer = ALCompilerInstaller()
    success = installer.install_al_compiler()
    
    if success:
        installer.log("🎉 AL Compiler installation completed!", "green")
        sys.exit(0)
    else:
        installer.log("❌ AL Compiler installation failed", "red")
        sys.exit(1)


if __name__ == "__main__":
    main()