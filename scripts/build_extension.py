#!/usr/bin/env python3
"""
Lean AL Extension Builder
Focused build script: version management + compilation only
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Optional, Dict, Any


class ALBuilder:
    def __init__(self, working_directory: str = "."):
        self.working_directory = Path(working_directory).resolve()
        self.symbols_path = self.working_directory / ".symbols"
        self.error_log = self.working_directory / "errorLog.json"
        self.is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
        
    def log(self, message: str, color: Optional[str] = None):
        """Print colored log message"""
        colors = {
            "green": "\033[92m",
            "yellow": "\033[93m",
            "red": "\033[91m",
            "cyan": "\033[96m",
            "gray": "\033[90m",
            "reset": "\033[0m"
        }
        
        if color and color in colors:
            print(f"{colors[color]}{message}{colors['reset']}")
        else:
            print(message)
    
    def load_app_json(self) -> Dict[str, Any]:
        """Load app.json file (assumes it's already been validated by analysis step)"""
        app_json_path = self.working_directory / "app.json"
        
        if not app_json_path.exists():
            self.log("❌ app.json not found", "red")
            sys.exit(1)
        
        with open(app_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def detect_bc_version(self, app_data: Dict[str, Any], build_type: str) -> str:
        """Detect Business Central version from app.json"""
        if build_type != 'auto':
            return build_type
        
        application = app_data.get("application", "")
        bc_major_version = application.split('.')[0] if application else ""
        
        version_map = {
            '17': 'bc17', '18': 'bc18', '19': 'bc19', '20': 'bc20',
            '21': 'bc21', '22': 'bc22', '23': 'bc23', '24': 'bc24',
            '25': 'bc25', '26': 'bc26'
        }
        
        return version_map.get(bc_major_version, 'bccloud')
    
    def handle_version_specific_app_json(self, bc_version: str) -> Optional[str]:
        """Handle version-specific app.json files"""
        version_files = {
            'bc17': 'bc17_app.json',
            'bc18': 'bc18_app.json',
            'bc19': 'bc19_app.json',
            'bc22': 'bc22_app.json',
            'bccloud': 'cloud_app.json'
        }
        
        version_file = version_files.get(bc_version)
        if not version_file:
            return None
        
        version_path = self.working_directory / version_file
        if version_path.exists():
            self.log(f"🔄 Switching to version-specific app.json: {version_file}", "yellow")
            
            # Backup original
            shutil.copy2(self.working_directory / "app.json", 
                        self.working_directory / "app.json.backup")
            
            # Use version-specific file
            shutil.copy2(version_path, self.working_directory / "app.json")
            return version_file
        
        return None
    
    def check_appsource_app(self, app_data: Dict[str, Any]) -> bool:
        """Check if this is an AppSource app based on ID ranges"""
        id_ranges = app_data.get("idRanges", [])
        for id_range in id_ranges:
            if id_range.get("from", 0) >= 100000:
                self.log("🏪 Detected AppSource app (ID ranges include 100000+)", "green")
                return True
        
        self.log("🏠 Detected internal/PTE app", "cyan")
        return False
    
    def generate_build_version(self, mode: str, platform: str) -> str:
        """Generate build version based on mode and environment"""
        if mode == 'test':
            # Test compilation - use fixed version
            build_version = "0.0.0.0"
            self.log(f"🧪 Test compilation version: {build_version}", "cyan")
            return build_version
        
        # Production build - calculate version
        platform_major = platform.split('.')[0]
        year_minor = datetime.now().strftime('%y')
        
        # Days since 2020-01-01
        epoch_2020 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_build = (now - epoch_2020).days
        
        # Minutes since midnight
        minutes_revision = int(now.hour * 60 + now.minute)
        
        # Production build version
        build_version = f"{platform_major}.{year_minor}.{days_build}.{minutes_revision}"
        self.log(f"🏗️ Production build version: {build_version}", "green")
        
        return build_version
    
    def update_app_json_version(self, build_version: str):
        """Update app.json with build version"""
        self.log(f"📝 Updating app.json version to {build_version}...", "yellow")
        
        # Backup original if not already backed up
        backup_path = self.working_directory / "app.json.backup"
        if not backup_path.exists():
            shutil.copy2(self.working_directory / "app.json", backup_path)
        
        # Update version
        with open(self.working_directory / "app.json", 'r', encoding='utf-8') as f:
            app_data = json.load(f)
        
        app_data["version"] = build_version
        
        # Write updated app.json
        with open(self.working_directory / "app.json", 'w', encoding='utf-8') as f:
            json.dump(app_data, f, indent=2)
    
    def find_al_compiler(self) -> Optional[str]:
        """Find AL compiler executable"""
        # Try common AL compiler locations
        possible_commands = ['AL', 'alc']
        
        for cmd in possible_commands:
            al_path = shutil.which(cmd)
            if al_path:
                return al_path
        
        # Check .dotnet tools directory
        dotnet_tools = Path.home() / ".dotnet" / "tools"
        for cmd in possible_commands:
            tool_path = dotnet_tools / cmd
            if tool_path.exists():
                return str(tool_path)
        
        return None
    
    def compile_extension(self, app_data: Dict[str, Any], build_version: str) -> tuple[bool, Optional[str]]:
        """Compile AL extension"""
        al_compiler = self.find_al_compiler()
        if not al_compiler:
            self.log("❌ AL compiler not found. Please install via: python install_al_compiler.py", "red")
            return False, None
        
        self.log(f"🔧 Using AL compiler: {al_compiler}", "green")
        
        # Prepare compilation parameters
        app_name = app_data["name"]
        clean_app_name = re.sub(r'[ -]', '', app_name)
        commit_short = os.environ.get('GITHUB_SHA', '0000000')[:7]
        output_file = f"{clean_app_name}_{build_version}_{commit_short}.app"
        app_target = app_data.get("target", "Cloud")
        
        # Ensure symbols directory exists
        self.symbols_path.mkdir(exist_ok=True)
        
        # Remove previous error log
        if self.error_log.exists():
            self.error_log.unlink()
        
        # Build compiler arguments
        alc_args = [
            al_compiler, "compile",
            f"/project:{self.working_directory}",
            f"/out:{output_file}",
            f"/packagecachepath:{self.symbols_path}",
            f"/target:{app_target}",
            f"/loglevel:Normal",
            f"/errorlog:{self.error_log}"
        ]
        
        # Add ruleset if it exists
        ruleset_file = self.working_directory / "LincRuleSet.json"
        if ruleset_file.exists():
            alc_args.append(f"/ruleset:{ruleset_file}")
            self.log(f"📋 Using ruleset: {ruleset_file.name}", "cyan")
        
        self.log("🚀 Running AL compiler...", "green")
        
        # Debug: show the command
        if self.is_github_actions or os.environ.get('DEBUG'):
            self.log(f"Command: {' '.join(alc_args)}", "gray")
        
        # Setup environment for CI
        env = os.environ.copy()
        if self.is_github_actions:
            env['DOTNET_CLI_TELEMETRY_OPTOUT'] = '1'
            env['DOTNET_SKIP_FIRST_TIME_EXPERIENCE'] = '1'
        
        # Run compilation
        try:
            result = subprocess.run(alc_args, cwd=self.working_directory, 
                                  capture_output=True, text=True, env=env)
            
            if result.returncode == 0:
                output_path = self.working_directory / output_file
                if output_path.exists():
                    self.log("✅ Compilation successful!", "green")
                    return True, str(output_path)
                else:
                    self.log("⚠️ Compilation reported success but no output file found", "yellow")
                    return False, None
            else:
                self.log("❌ Compilation failed!", "red")
                
                # Show stderr immediately for debugging
                if result.stderr:
                    self.log("📋 Compiler stderr:", "red")
                    self.log(result.stderr, "red")
                
                # Show error log if available
                if self.error_log.exists():
                    self.log("📋 Error log file:", "red")
                    with open(self.error_log, 'r') as f:
                        self.log(f.read(), "red")
                
                return False, None
                
        except Exception as e:
            self.log(f"❌ Failed to run compiler: {e}", "red")
            return False, None
    
    def restore_app_json(self):
        """Restore original app.json from backup"""
        backup_path = self.working_directory / "app.json.backup"
        if backup_path.exists():
            shutil.copy2(backup_path, self.working_directory / "app.json")
            backup_path.unlink()
            self.log("✅ Original app.json restored", "green")
    
    def set_github_outputs(self, success: bool, app_file_path: Optional[str] = None, build_number: Optional[str] = None):
        """Set GitHub Actions outputs"""
        github_output = os.environ.get('GITHUB_OUTPUT')
        if not github_output:
            return
        
        try:
            with open(github_output, 'a') as f:
                f.write(f"compilation-success={'true' if success else 'false'}\n")
                if app_file_path:
                    f.write(f"app-file-path={app_file_path}\n")
                if build_number:
                    f.write(f"build-number={build_number}\n")
        except Exception as e:
            self.log(f"⚠️ Failed to set GitHub outputs: {e}", "yellow")
    
    def build(self, mode: str) -> bool:
        """Main build process - lean and focused"""
        try:
            self.log(f"🔨 Building AL extension in {mode} mode...", "green")
            
            # Load app.json (assumes prior analysis step validated it)
            app_data = self.load_app_json()
            
            app_name = app_data["name"]
            platform = app_data["platform"]
            
            self.log(f"📦 App: {app_name}", "cyan")
            
            # Generate build version
            build_version = self.generate_build_version(mode, platform)
            
            # Update app.json with build version
            self.update_app_json_version(build_version)
            
            # Compile extension
            success, app_file_path = self.compile_extension(app_data, build_version)
            
            # Generate build number for GitHub outputs
            commit_short = os.environ.get('GITHUB_SHA', '0000000')[:7]
            build_number = f"{build_version}_{commit_short}"
            
            # Set GitHub outputs
            self.set_github_outputs(success, app_file_path, build_number)
            
            # Show build summary
            if success and app_file_path:
                file_size_mb = Path(app_file_path).stat().st_size / (1024 * 1024)
                
                self.log("🎉 AL extension build completed!", "green")
                self.log("📊 Build summary:", "cyan")
                self.log(f"  📦 App: {app_name}", "cyan")
                self.log(f"  📋 Version: {build_version}", "cyan")
                self.log(f"  📁 File: {Path(app_file_path).name}", "cyan")
                self.log(f"  📏 Size: {file_size_mb:.2f} MB", "cyan")
                
                return True
            else:
                self.log("❌ AL extension build failed", "red")
                return False
                
        finally:
            # Always restore original app.json
            self.restore_app_json()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Lean AL extension builder')
    parser.add_argument('mode', choices=['build', 'test'], help='Build mode')
    parser.add_argument('--working-directory', default='.', help='Working directory')
    
    args = parser.parse_args()
    
    builder = ALBuilder(args.working_directory)
    success = builder.build(args.mode)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()