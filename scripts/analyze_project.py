#!/usr/bin/env python3
"""
Project Analyzer - Python Version
Analyze AL project structure and extract metadata
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional


class ALProjectAnalyzer:
    def __init__(self, working_directory: str = "."):
        self.working_directory = Path(working_directory).resolve()
        
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
    
    def parse_app_json(self) -> Optional[Dict[str, Any]]:
        """Parse app.json file"""
        app_json_path = self.working_directory / "app.json"
        
        if not app_json_path.exists():
            self.log("❌ app.json not found in current directory", "red")
            return None
        
        try:
            with open(app_json_path, 'r', encoding='utf-8') as f:
                app_data = json.load(f)
            
            self.log("✅ app.json parsed successfully", "green")
            return app_data
        except json.JSONDecodeError as e:
            self.log(f"❌ Failed to parse app.json: {e}", "red")
            return None
    
    def analyze_id_ranges(self, app_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze ID ranges to determine app type"""
        id_ranges = app_data.get("idRanges", [])
        
        analysis = {
            "isAppSource": False,
            "isPTE": False,
            "isInternal": False,
            "hasCustomRange": False,
            "ranges": id_ranges
        }
        
        for id_range in id_ranges:
            range_from = id_range.get("from", 0)
            range_to = id_range.get("to", 0)
            
            if range_from >= 100000:
                analysis["isAppSource"] = True
            elif range_from >= 50000:
                analysis["isPTE"] = True
            elif range_from >= 1:
                analysis["hasCustomRange"] = True
            else:
                analysis["isInternal"] = True
        
        return analysis
    
    def analyze_dependencies(self, app_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze dependencies"""
        dependencies = app_data.get("dependencies", [])
        
        analysis = {
            "count": len(dependencies),
            "microsoft": [],
            "thirdParty": [],
            "hasBaseApp": False,
            "hasSystemApp": False,
            "hasApplicationApp": False
        }
        
        for dep in dependencies:
            name = dep.get("name", "")
            publisher = dep.get("publisher", "")
            
            if publisher.lower() == "microsoft":
                analysis["microsoft"].append(dep)
                
                # Check for standard Microsoft apps
                if name.lower() == "base application":
                    analysis["hasBaseApp"] = True
                elif name.lower() == "system application":
                    analysis["hasSystemApp"] = True
                elif name.lower() == "application":
                    analysis["hasApplicationApp"] = True
            else:
                analysis["thirdParty"].append(dep)
        
        return analysis
    
    def scan_source_files(self) -> Dict[str, Any]:
        """Scan source files for analysis"""
        analysis = {
            "totalFiles": 0,
            "alFiles": 0,
            "objectTypes": {},
            "largestFile": {"name": "", "size": 0},
            "hasTests": False,
            "hasPermissionSets": False,
            "encoding": "utf-8"
        }
        
        # Find all AL files
        al_files = list(self.working_directory.rglob("*.al"))
        analysis["totalFiles"] = len(al_files)
        analysis["alFiles"] = len(al_files)
        
        object_types = {}
        largest_size = 0
        largest_file = ""
        
        for al_file in al_files:
            try:
                file_size = al_file.stat().st_size
                if file_size > largest_size:
                    largest_size = file_size
                    largest_file = str(al_file.relative_to(self.working_directory))
                
                # Read file to analyze content
                with open(al_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract object type from AL file
                object_type = self._extract_object_type(content)
                if object_type:
                    if object_type not in object_types:
                        object_types[object_type] = 0
                    object_types[object_type] += 1
                
                # Check for tests
                if "test" in al_file.name.lower() or "[TEST]" in content.upper():
                    analysis["hasTests"] = True
                
                # Check for permission sets
                if object_type and object_type.lower() == "permissionset":
                    analysis["hasPermissionSets"] = True
                    
            except (UnicodeDecodeError, OSError) as e:
                self.log(f"⚠️ Could not read {al_file}: {e}", "yellow")
                continue
        
        analysis["objectTypes"] = object_types
        analysis["largestFile"] = {
            "name": largest_file,
            "size": largest_size
        }
        
        return analysis
    
    def _extract_object_type(self, content: str) -> Optional[str]:
        """Extract AL object type from file content"""
        # Match AL object declarations
        patterns = [
            r'^\s*(table|page|report|codeunit|query|xmlport|menusuitenode|profile|pagecustomization|reportextension|tableextension|pageextension|enum|enumextension|interface|controlladdin|permissionset|entitlement)\s+\d+',
            r'^\s*(table|page|report|codeunit|query|xmlport|menusuitenode|profile|pagecustomization|reportextension|tableextension|pageextension|enum|enumextension|interface|controlladdin|permissionset|entitlement)\s+"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
            if match:
                return match.group(1).lower()
        
        return None
    
    def detect_bc_version(self, app_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect Business Central version information"""
        platform = app_data.get("platform", "")
        application = app_data.get("application", "")
        runtime = app_data.get("runtime", "")
        
        analysis = {
            "platform": platform,
            "application": application,
            "runtime": runtime,
            "bcMajorVersion": "",
            "bcVersionName": "",
            "isCloud": False,
            "isOnPrem": False
        }
        
        # Extract BC major version from application
        if application:
            major_version = application.split('.')[0]
            analysis["bcMajorVersion"] = major_version
            
            # Map to BC version names
            version_map = {
                "14": "BC 14 (2019 Release Wave 1)",
                "15": "BC 15 (2019 Release Wave 2)", 
                "16": "BC 16 (2020 Release Wave 1)",
                "17": "BC 17 (2020 Release Wave 2)",
                "18": "BC 18 (2021 Release Wave 1)",
                "19": "BC 19 (2021 Release Wave 2)",
                "20": "BC 20 (2022 Release Wave 1)",
                "21": "BC 21 (2022 Release Wave 2)",
                "22": "BC 22 (2023 Release Wave 1)",
                "23": "BC 23 (2023 Release Wave 2)",
                "24": "BC 24 (2024 Release Wave 1)",
                "25": "BC 25 (2024 Release Wave 2)",
                "26": "BC 26 (2025 Release Wave 1)"
            }
            
            analysis["bcVersionName"] = version_map.get(major_version, f"BC {major_version}")
        
        # Determine deployment target
        target = app_data.get("target", "").lower()
        if target == "cloud":
            analysis["isCloud"] = True
        elif target in ["onprem", "onpremises"]:
            analysis["isOnPrem"] = True
        
        return analysis
    
    def check_build_artifacts(self) -> Dict[str, Any]:
        """Check for existing build artifacts and configuration"""
        artifacts = {
            "hasRuleset": False,
            "rulesetPath": "",
            "hasLaunchJson": False,
            "hasSymbols": False,
            "symbolsCount": 0,
            "hasAppFiles": False,
            "appFilesCount": 0,
            "hasTestResults": False,
            "buildConfigFiles": []
        }
        
        # Check for ruleset file
        ruleset_files = ["LincRuleSet.json", "ruleset.json"]
        for ruleset in ruleset_files:
            ruleset_path = self.working_directory / ruleset
            if ruleset_path.exists():
                artifacts["hasRuleset"] = True
                artifacts["rulesetPath"] = ruleset
                break
        
        # Check for VS Code launch configuration
        launch_json = self.working_directory / ".vscode" / "launch.json"
        if launch_json.exists():
            artifacts["hasLaunchJson"] = True
        
        # Check for symbols
        symbols_dir = self.working_directory / ".symbols"
        if symbols_dir.exists() and symbols_dir.is_dir():
            artifacts["hasSymbols"] = True
            symbol_files = list(symbols_dir.glob("*.app"))
            artifacts["symbolsCount"] = len(symbol_files)
        
        # Check for existing app files
        app_files = list(self.working_directory.glob("*.app"))
        if app_files:
            artifacts["hasAppFiles"] = True
            artifacts["appFilesCount"] = len(app_files)
        
        # Check for test results
        test_files = list(self.working_directory.glob("TestResults*.xml"))
        if test_files:
            artifacts["hasTestResults"] = True
        
        # Check for build configuration files
        config_files = ["build.json", "build.yml", "build.yaml", ".github/workflows/*.yml", ".github/workflows/*.yaml"]
        for pattern in config_files:
            matching_files = list(self.working_directory.glob(pattern))
            for file_path in matching_files:
                artifacts["buildConfigFiles"].append(str(file_path.relative_to(self.working_directory)))
        
        return artifacts
    
    def generate_clean_name(self, app_name: str) -> str:
        """Generate clean app name for file naming"""
        # Remove spaces, hyphens, and special characters
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', app_name)
        return clean_name
    
    def analyze_project(self) -> Dict[str, Any]:
        """Perform complete project analysis"""
        self.log("🔍 Analyzing AL project...", "cyan")
        
        # Parse app.json
        app_data = self.parse_app_json()
        if not app_data:
            return {"error": "Could not parse app.json"}
        
        # Basic app information
        app_info = {
            "name": app_data.get("name", ""),
            "version": app_data.get("version", ""),
            "publisher": app_data.get("publisher", ""),
            "description": app_data.get("description", ""),
            "cleanName": self.generate_clean_name(app_data.get("name", "")),
            "target": app_data.get("target", "Cloud")
        }
        
        # Analyze different aspects
        id_analysis = self.analyze_id_ranges(app_data)
        dep_analysis = self.analyze_dependencies(app_data)
        source_analysis = self.scan_source_files()
        version_analysis = self.detect_bc_version(app_data)
        build_analysis = self.check_build_artifacts()
        
        # Compile complete analysis
        complete_analysis = {
            "appInfo": app_info,
            "idRanges": id_analysis,
            "dependencies": dep_analysis,
            "sourceCode": source_analysis,
            "bcVersion": version_analysis,
            "buildArtifacts": build_analysis,
            "analysisTimestamp": os.environ.get("GITHUB_RUN_NUMBER", "local"),
            "workingDirectory": str(self.working_directory)
        }
        
        return complete_analysis
    
    def print_analysis_summary(self, analysis: Dict[str, Any]):
        """Print a human-readable analysis summary"""
        app_info = analysis["appInfo"]
        id_ranges = analysis["idRanges"]
        deps = analysis["dependencies"]
        source = analysis["sourceCode"]
        bc_version = analysis["bcVersion"]
        
        self.log("\n📊 AL Project Analysis Summary", "green")
        self.log("=" * 50, "green")
        
        # App Information
        self.log(f"📦 App Name: {app_info['name']}", "cyan")
        self.log(f"📋 Version: {app_info['version']}", "cyan")
        self.log(f"👤 Publisher: {app_info['publisher']}", "cyan")
        self.log(f"🎯 Target: {app_info['target']}", "cyan")
        
        # BC Version
        if bc_version['bcVersionName']:
            self.log(f"🏢 BC Version: {bc_version['bcVersionName']}", "cyan")
        
        # App Type
        if id_ranges['isAppSource']:
            self.log("🏪 App Type: AppSource", "green")
        elif id_ranges['isPTE']:
            self.log("🏠 App Type: Per-Tenant Extension (PTE)", "green")
        else:
            self.log("🏠 App Type: Internal/Development", "green")
        
        # Source Code
        self.log(f"📁 AL Files: {source['alFiles']}", "gray")
        if source['objectTypes']:
            self.log("🧩 Object Types:", "gray")
            for obj_type, count in source['objectTypes'].items():
                self.log(f"   {obj_type}: {count}", "gray")
        
        # Dependencies
        self.log(f"📦 Dependencies: {deps['count']} ({len(deps['microsoft'])} Microsoft, {len(deps['thirdParty'])} Third-party)", "gray")
        
        # Tests
        if source['hasTests']:
            self.log("✅ Tests: Found", "green")
        else:
            self.log("⚠️ Tests: Not found", "yellow")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze AL project structure')
    parser.add_argument('--working-directory', default='.', 
                       help='Working directory to analyze')
    parser.add_argument('--output-json', 
                       help='Output analysis as JSON to file')
    parser.add_argument('--summary', action='store_true',
                       help='Print human-readable summary')
    
    args = parser.parse_args()
    
    analyzer = ALProjectAnalyzer(args.working_directory)
    analysis = analyzer.analyze_project()
    
    if "error" in analysis:
        analyzer.log(f"❌ Analysis failed: {analysis['error']}", "red")
        sys.exit(1)
    
    # Output JSON if requested
    if args.output_json:
        with open(args.output_json, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        analyzer.log(f"📁 Analysis saved to: {args.output_json}", "green")
    
    # Print summary if requested
    if args.summary:
        analyzer.print_analysis_summary(analysis)
    
    # Always output basic JSON for GitHub Actions
    print(json.dumps(analysis["appInfo"]))


if __name__ == "__main__":
    main()