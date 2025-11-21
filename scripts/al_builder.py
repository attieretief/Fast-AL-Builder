#!/usr/bin/env python3
"""
AL Extension Builder - Main Orchestrator
Coordinates the complete AL extension build process
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Import our custom modules
sys.path.append(str(Path(__file__).parent))

from build_extension import ALBuilder
from install_al_compiler import ALCompilerInstaller
from download_symbols import SymbolDownloader
from publish_appsource import AppSourcePublisher
from analyze_project import ALProjectAnalyzer
from code_sign import CodeSigner


class ALBuildOrchestrator:
    def __init__(self):
        self.working_directory = Path.cwd()
        
    def log(self, message: str, color: str = None):
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
    
    def setup_environment(self, nuget_feed_url: str = None) -> bool:
        """Setup the build environment"""
        self.log("🛠️ Setting up build environment...", "cyan")
        
        # Install AL compiler if needed
        installer = ALCompilerInstaller()
        if not installer.check_dotnet():
            self.log("📥 .NET SDK not found, installing...", "yellow")
            if not installer.install_dotnet():
                self.log("❌ Failed to install .NET SDK", "red")
                return False
        
        # Install AL compiler
        success = installer.install_al_compiler(nuget_feed_url or "https://api.nuget.org/v3/index.json")
        if not success:
            self.log("⚠️ AL compiler installation had issues, but continuing...", "yellow")
        
        return True
    
    def analyze_project(self) -> dict:
        """Analyze the current project"""
        analyzer = ALProjectAnalyzer()
        analysis = analyzer.analyze_project()
        
        if "error" in analysis:
            self.log(f"❌ Project analysis failed: {analysis['error']}", "red")
            return {}
        
        return analysis
    
    def download_symbols(self, bc_version: str, dependencies: list, 
                        linc_registry_url: str = None, linc_token: str = None) -> bool:
        """Download symbols for compilation"""
        downloader = SymbolDownloader()
        
        # Convert dependencies list to JSON string
        dependencies_json = json.dumps(dependencies) if dependencies else ""
        
        return downloader.download_symbols(
            bc_version=bc_version,
            dependencies_json=dependencies_json,
            linc_registry_url=linc_registry_url,
            linc_token=linc_token
        )
    
    def build_extension(self, mode: str, build_type: str = "auto", 
                       force_showmycode_false: bool = True) -> tuple[bool, str]:
        """Build the AL extension"""
        builder = ALBuilder()
        success = builder.build(
            mode=mode,
            build_type=build_type,
            force_showmycode_false=force_showmycode_false
        )
        
        # Find the generated app file
        app_files = list(Path.cwd().glob("*.app"))
        app_file_path = str(app_files[0]) if app_files else ""
        
        return success, app_file_path
    
    def sign_extension(self, app_file_path: str, cert_base64: str = None, 
                      cert_password: str = None) -> bool:
        """Sign the AL extension"""
        if not cert_base64 or not cert_password:
            self.log("ℹ️ No signing certificate provided, skipping code signing", "cyan")
            return True
        
        signer = CodeSigner()
        return signer.sign_app_file(app_file_path, cert_base64, cert_password)
    
    def publish_to_appsource(self, app_info: dict, app_file_path: str,
                           tenant_id: str = None, client_id: str = None, 
                           client_secret: str = None) -> bool:
        """Publish to AppSource"""
        if not all([tenant_id, client_id, client_secret]):
            self.log("ℹ️ AppSource credentials not provided, skipping publication", "cyan")
            return True
        
        publisher = AppSourcePublisher()
        return publisher.publish(
            app_info_json=json.dumps(app_info),
            app_file_path=app_file_path,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
    
    def full_build_pipeline(self, mode: str = "build", build_type: str = "auto",
                          include_symbols: bool = True, include_signing: bool = True,
                          include_appsource: bool = True) -> bool:
        """Run the complete build pipeline"""
        self.log("🚀 Starting AL extension build pipeline...", "green")
        
        try:
            # 1. Setup environment
            if not self.setup_environment():
                return False
            
            # 2. Analyze project
            self.log("\n📋 Step 1: Analyzing project...", "cyan")
            analysis = self.analyze_project()
            if not analysis:
                return False
            
            app_info = analysis.get("appInfo", {})
            bc_version = analysis.get("bcVersion", {}).get("bcMajorVersion", "26")
            # Include both Microsoft and third-party dependencies  
            all_dependencies = []
            all_dependencies.extend(analysis.get("dependencies", {}).get("microsoft", []))
            all_dependencies.extend(analysis.get("dependencies", {}).get("thirdParty", []))
            
            self.log(f"✅ Project: {app_info.get('name', 'Unknown')}", "green")
            
            # 3. Download symbols
            if include_symbols:
                self.log("\n📦 Step 2: Downloading symbols...", "cyan")
                bc_version_str = f"bc{bc_version}" if bc_version != "26" else "bccloud"
                
                symbols_success = self.download_symbols(
                    bc_version=bc_version_str,
                    dependencies=all_dependencies,
                    linc_registry_url=os.environ.get('LINC_REGISTRY_URL'),
                    linc_token=os.environ.get('LINC_TOKEN')
                )
                
                if not symbols_success:
                    self.log("⚠️ Symbol download had issues, but continuing...", "yellow")
            
            # 4. Build extension
            self.log("\n🔨 Step 3: Building extension...", "cyan")
            build_success, app_file_path = self.build_extension(
                mode=mode,
                build_type=build_type,
                force_showmycode_false=True
            )
            
            if not build_success:
                self.log("❌ Build failed", "red")
                return False
            
            self.log(f"✅ Build successful: {app_file_path}", "green")
            
            # 5. Sign extension
            if include_signing and app_file_path:
                self.log("\n🖊️ Step 4: Signing extension...", "cyan")
                signing_success = self.sign_extension(
                    app_file_path=app_file_path,
                    cert_base64=os.environ.get('SIGNING_CERT_BASE64'),
                    cert_password=os.environ.get('SIGNING_CERT_PASSWORD')
                )
                
                if not signing_success:
                    self.log("⚠️ Signing failed, but continuing...", "yellow")
                else:
                    self.log("✅ Signing successful", "green")
            
            # 6. Publish to AppSource
            if include_appsource and app_file_path:
                self.log("\n🏪 Step 5: Publishing to AppSource...", "cyan")
                publish_success = self.publish_to_appsource(
                    app_info=app_info,
                    app_file_path=app_file_path,
                    tenant_id=os.environ.get('APPSOURCE_TENANT_ID'),
                    client_id=os.environ.get('APPSOURCE_CLIENT_ID'),
                    client_secret=os.environ.get('APPSOURCE_CLIENT_SECRET')
                )
                
                if not publish_success:
                    self.log("⚠️ AppSource publication had issues", "yellow")
                else:
                    self.log("✅ AppSource publication completed", "green")
            
            self.log("\n🎉 Build pipeline completed successfully!", "green")
            self.log(f"📦 Final artifact: {app_file_path}", "cyan")
            
            return True
            
        except Exception as e:
            self.log(f"\n❌ Build pipeline failed with error: {e}", "red")
            return False


def main():
    parser = argparse.ArgumentParser(description='AL Extension Build Orchestrator')
    
    # Main command
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Full build command
    build_parser = subparsers.add_parser('build', help='Run full build pipeline')
    build_parser.add_argument('--mode', choices=['build', 'test'], default='build',
                             help='Build mode')
    build_parser.add_argument('--build-type', default='auto',
                             help='Build type (auto, bc17, bc18, etc.)')
    build_parser.add_argument('--skip-symbols', action='store_true',
                             help='Skip symbol download')
    build_parser.add_argument('--skip-signing', action='store_true',
                             help='Skip code signing')
    build_parser.add_argument('--skip-appsource', action='store_true',
                             help='Skip AppSource publication')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup build environment')
    setup_parser.add_argument('--nuget-feed-url',
                             default='https://api.nuget.org/v3/index.json',
                             help='NuGet feed URL')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze AL project')
    analyze_parser.add_argument('--summary', action='store_true',
                               help='Print human-readable summary')
    analyze_parser.add_argument('--output-json',
                               help='Output analysis as JSON to file')
    
    # Individual step commands
    subparsers.add_parser('download-symbols', help='Download symbols only')
    subparsers.add_parser('build-only', help='Build extension only')
    subparsers.add_parser('sign-only', help='Sign extension only')
    subparsers.add_parser('publish-only', help='Publish to AppSource only')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    orchestrator = ALBuildOrchestrator()
    
    if args.command == 'build':
        success = orchestrator.full_build_pipeline(
            mode=args.mode,
            build_type=args.build_type,
            include_symbols=not args.skip_symbols,
            include_signing=not args.skip_signing,
            include_appsource=not args.skip_appsource
        )
        sys.exit(0 if success else 1)
    
    elif args.command == 'setup':
        success = orchestrator.setup_environment(args.nuget_feed_url)
        sys.exit(0 if success else 1)
    
    elif args.command == 'analyze':
        analyzer = ALProjectAnalyzer()
        analysis = analyzer.analyze_project()
        
        if "error" in analysis:
            orchestrator.log(f"❌ Analysis failed: {analysis['error']}", "red")
            sys.exit(1)
        
        if args.output_json:
            with open(args.output_json, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2)
            orchestrator.log(f"📁 Analysis saved to: {args.output_json}", "green")
        
        if args.summary:
            analyzer.print_analysis_summary(analysis)
        
        # Always output basic info for scripts
        print(json.dumps(analysis["appInfo"]))
    
    elif args.command == 'download-symbols':
        # Analyze project first to get dependencies
        analysis = orchestrator.analyze_project()
        if not analysis:
            sys.exit(1)
        
        bc_version = analysis.get("bcVersion", {}).get("bcMajorVersion", "26")
        # Include both Microsoft and third-party dependencies
        all_dependencies = []
        all_dependencies.extend(analysis.get("dependencies", {}).get("microsoft", []))
        all_dependencies.extend(analysis.get("dependencies", {}).get("thirdParty", []))
        
        bc_version_str = f"bc{bc_version}" if bc_version != "26" else "bccloud"
        
        success = orchestrator.download_symbols(
            bc_version=bc_version_str,
            dependencies=all_dependencies,
            linc_registry_url=os.environ.get('LINC_REGISTRY_URL'),
            linc_token=os.environ.get('LINC_TOKEN')
        )
        sys.exit(0 if success else 1)
    
    elif args.command == 'build-only':
        success, app_file_path = orchestrator.build_extension('build')
        if success:
            orchestrator.log(f"✅ Build successful: {app_file_path}", "green")
        sys.exit(0 if success else 1)
    
    else:
        orchestrator.log(f"❌ Command '{args.command}' not implemented yet", "red")
        sys.exit(1)


if __name__ == "__main__":
    main()