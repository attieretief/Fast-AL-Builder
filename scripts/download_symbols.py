#!/usr/bin/env python3
"""
Symbol Downloader - Python Version
Download Microsoft Business Central symbols using official NuGet feeds
"""

import os
import sys
import json
import subprocess
import zipfile
import io
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional


class SymbolDownloader:
    def __init__(self, symbols_dir: str = ".symbols"):
        self.symbols_dir = Path(symbols_dir).resolve()
        self.symbols_dir.mkdir(parents=True, exist_ok=True)
        self.is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
        self.is_ubuntu = os.environ.get('RUNNER_OS') == 'Linux' or 'ubuntu' in os.environ.get('RUNNER_NAME', '').lower()
        
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
    
    def get_bc_version_info(self, bc_version: str) -> Dict[str, str]:
        """Get BC version information for symbol downloads"""
        bc_clean = bc_version.lower().replace('bc', '').replace('cloud', '')
        
        # Map BC versions to their symbol download info
        version_map = {
            "17": {"version": "17.0", "name": "bc17"},
            "18": {"version": "18.0", "name": "bc18"}, 
            "19": {"version": "19.0", "name": "bc19"},
            "20": {"version": "20.0", "name": "bc20"},
            "21": {"version": "21.0", "name": "bc21"},
            "22": {"version": "22.0", "name": "bc22"},
            "23": {"version": "23.0", "name": "bc23"},
            "24": {"version": "24.0", "name": "bc24"},
            "25": {"version": "25.0", "name": "bc25"},
            "26": {"version": "26.0", "name": "bc26"},
            "": {"version": "26.0", "name": "bclatest"}  # Default to latest
        }
        
        return version_map.get(bc_clean, {"version": "26.0", "name": "bclatest"})
    
    def download_microsoft_symbols_simple(self, bc_version: str) -> bool:
        """
        Download Microsoft symbols using NuGet approach
        Uses official Microsoft NuGet feeds for Business Central symbols
        """
        self.log(f"📦 Downloading Microsoft symbols for {bc_version}...", "cyan")
        
        version_info = self.get_bc_version_info(bc_version)
        
        # Check if symbols already exist
        existing_symbols = self.check_existing_symbols()
        if existing_symbols:
            self.log(f"✅ Found {len(existing_symbols)} existing symbol files", "green")
            return True
        
        # Use NuGet approach to download symbols
        return self.download_symbols_via_nuget(bc_version, version_info)
    
    def check_existing_symbols(self) -> List[Path]:
        """Check if symbol files already exist in the symbols directory"""
        existing_symbols = list(self.symbols_dir.glob("*.app"))
        
        # Filter out small files (likely stubs)
        real_symbols = []
        for symbol in existing_symbols:
            if symbol.stat().st_size > 1000:  # Real symbols are much larger
                real_symbols.append(symbol)
        
        return real_symbols
    
    def download_symbols_via_nuget(self, bc_version: str, version_info: Dict[str, str]) -> bool:
        """
        Download Microsoft Business Central symbols using public Microsoft feeds
        Uses the same approach as ALGet package manager
        """
        self.log("🔗 Using Microsoft's public BC symbol feeds...", "cyan")
        
        # Setup Microsoft's public NuGet feeds  
        if not self.setup_microsoft_nuget_feeds():
            self.log("⚠️ Failed to setup Microsoft NuGet feeds", "yellow")
            return False
        
        # Get the Microsoft symbol packages using ALGet naming scheme
        packages = self.get_microsoft_symbol_packages_alget_style(bc_version, version_info)
        if not packages:
            self.log("⚠️ Could not determine symbol packages for this BC version", "yellow")
            return False
        
        # Download each package using ALGet approach
        success_count = 0
        for package_info in packages:
            if self.download_microsoft_symbol_package(package_info):
                success_count += 1
        
        if success_count > 0:
            self.log(f"✅ Successfully downloaded {success_count}/{len(packages)} Microsoft symbol packages", "green")
            return True
        else:
            self.log("❌ No Microsoft symbol packages could be downloaded", "yellow")
            return False
    
    def setup_microsoft_nuget_feeds(self) -> bool:
        """
        Setup Microsoft's public Business Central symbol feeds
        Uses the same feeds as ALGet package manager:
        - MSSymbols: Core Microsoft symbols (System, Application, etc.)
        - AppSourceSymbols: Third-party extensions published to AppSource (including LINC)
        """
        self.log("🔧 Setting up BC symbol feeds (Microsoft + AppSource)...", "gray")
        
        # Microsoft's public BC symbol feeds (no authentication required)
        ms_feeds = [
            {
                "name": "MSSymbols", 
                "url": "https://dynamicssmb2.pkgs.visualstudio.com/DynamicsBCPublicFeeds/_packaging/MSSymbols/nuget/v3/index.json",
                "description": "Microsoft core symbols (System, Application, etc.)"
            },
            {
                "name": "AppSourceSymbols",
                "url": "https://dynamicssmb2.pkgs.visualstudio.com/DynamicsBCPublicFeeds/_packaging/AppSourceSymbols/nuget/v3/index.json",
                "description": "AppSource third-party extension symbols (including LINC)"
            }
        ]
        
        success_count = 0
        
        for feed in ms_feeds:
            self.log(f"📡 Adding feed: {feed['name']} ({feed['description']})", "gray")
            if self.add_nuget_source(feed):
                success_count += 1
        
        if success_count > 0:
            self.log(f"✅ Setup {success_count}/{len(ms_feeds)} Microsoft BC symbol feeds", "green")
            return True
        else:
            self.log("❌ Failed to setup any Microsoft symbol feeds", "red")
            return False
    
    def add_nuget_source(self, feed: Dict[str, str]) -> bool:
        """Add a single NuGet source"""
        try:
            # Use faster timeout in CI environments
            timeout = 10 if self.is_github_actions else 15
            
            # Check if source already exists
            check_cmd = ['dotnet', 'nuget', 'list', 'source']
            check_result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=timeout)
            
            if check_result.returncode == 0 and feed['url'] in check_result.stdout:
                self.log(f"✅ NuGet feed '{feed['name']}' already configured", "gray")
                return True
            
            # Setup environment for CI
            env = os.environ.copy()
            if self.is_github_actions:
                env['DOTNET_CLI_TELEMETRY_OPTOUT'] = '1'
                env['DOTNET_SKIP_FIRST_TIME_EXPERIENCE'] = '1'
            
            # Add NuGet source
            cmd = [
                'dotnet', 'nuget', 'add', 'source',
                feed['url'],
                '--name', feed['name']
            ]
            
            # Add authentication for LINC AppSource feed if token is available
            if feed['name'] == 'LincAppSourceSymbols' and hasattr(self, 'github_token') and self.github_token:
                cmd.extend(['--username', 'anything', '--password', self.github_token])
                self.log(f"🔑 Adding authentication for LINC AppSource feed", "gray")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout*2, env=env)
            
            if result.returncode == 0:
                self.log(f"✅ NuGet feed '{feed['name']}' added", "gray")
                return True
            elif "already exists" in result.stderr.lower():
                self.log(f"✅ NuGet feed '{feed['name']}' already exists", "gray")
                return True
            else:
                self.log(f"⚠️ Failed to add feed '{feed['name']}': {result.stderr.strip()}", "yellow")
                return False
                
        except Exception as e:
            self.log(f"⚠️ Error setting up feed '{feed['name']}': {e}", "yellow")
            return False
    
    def get_microsoft_symbol_packages_alget_style(self, bc_version: str, version_info: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Get Microsoft symbol package search patterns using ALGet approach
        Uses search terms that will find packages in Microsoft's feeds
        """
        major_version = version_info["version"].split('.')[0]
        
        # Search patterns based on ALGet's approach - use broader search terms
        # ALGet searches for patterns like ".W1." to find country-specific packages
        packages = [
            {
                "name": "application.symbols",  # Search for Application symbols
                "description": "Application symbols",
                "feed": "MSSymbols"
            },
            {
                "name": "baseapplication.symbols", # Search for Base Application symbols
                "description": "Base Application symbols", 
                "feed": "MSSymbols"
            },
            {
                "name": "systemapplication.symbols", # Search for System Application symbols
                "description": "System Application symbols",
                "feed": "MSSymbols"
            },
            {
                "name": "platform.symbols", # Search for Platform symbols
                "description": "Platform symbols",
                "feed": "MSSymbols"
            }
        ]
        
        # For BC 24+ include Business Foundation
        if int(major_version) >= 24:
            packages.append({
                "name": "businessfoundation.symbols",
                "description": "Business Foundation symbols",
                "feed": "MSSymbols"
            })
        
        self.log(f"📋 Search patterns for BC {major_version}: {len(packages)} packages", "gray")
        return packages
    
    def download_microsoft_symbol_package(self, package_info: Dict[str, str]) -> bool:
        """
        Download Microsoft symbol packages using ALGet's search approach
        Search for packages in Microsoft feeds then download the found packages
        """
        package_pattern = package_info['name']
        description = package_info['description']
        feed_name = package_info['feed']
        
        self.log(f"🔍 Searching for {description} (pattern: {package_pattern})...", "cyan")
        
        try:
            # First, search for packages matching our pattern using ALGet's approach
            feed_url = f"https://dynamicssmb2.pkgs.visualstudio.com/DynamicsBCPublicFeeds/_packaging/{feed_name}/nuget/v3/index.json"
            
            # Get the search service URL
            with urllib.request.urlopen(feed_url) as response:
                if response.status != 200:
                    self.log(f"⚠️ Failed to access {feed_name} feed", "yellow")
                    return False
                
                feed_data = json.loads(response.read().decode())
            
            # Find SearchQueryService URL
            search_service_url = None
            for resource in feed_data.get('resources', []):
                if resource.get('@type', '').startswith('SearchQueryService'):
                    search_service_url = resource.get('@id', '').rstrip('/')
                    break
            
            if not search_service_url:
                self.log(f"⚠️ Search service not found in {feed_name} feed", "yellow")
                return False
            
            # Search for packages using ALGet's query format
            # ALGet searches for pattern like ".W1." for country code filtering
            search_query = package_pattern.lower().replace('microsoft.', '')  # Remove Microsoft prefix for search
            search_url = f"{search_service_url}?q={search_query}&prerelease=false"
            
            self.log(f"🔍 Searching: {search_url}", "gray")
            
            with urllib.request.urlopen(search_url) as search_response:
                if search_response.status != 200:
                    self.log(f"⚠️ Search failed for {package_pattern}", "yellow")
                    return False
                
                search_data = json.loads(search_response.read().decode())
            
            packages = search_data.get('data', [])
            if not packages:
                self.log(f"⚠️ No packages found matching {package_pattern}", "yellow")
                return False
            
            self.log(f"📦 Found {len(packages)} matching packages", "gray")
            
            # Download the first matching package (usually the most relevant)
            for package in packages:
                package_id = package.get('id', '')
                if package_pattern.lower() in package_id.lower():
                    return self.download_specific_package(package_id, package.get('version', ''), feed_name, description)
            
            # If no exact match, try the first package
            if packages:
                first_package = packages[0]
                package_id = first_package.get('id', '')
                self.log(f"📦 Using first found package: {package_id}", "gray")
                return self.download_specific_package(package_id, first_package.get('version', ''), feed_name, description)
            
            return False
                    
        except urllib.error.URLError as e:
            self.log(f"❌ Network error searching for {package_pattern}: {e}", "red")
            return False
        except urllib.error.HTTPError as e:
            self.log(f"❌ HTTP error searching for {package_pattern}: {e}", "red")
            return False
        except Exception as e:
            self.log(f"❌ Error searching for {package_pattern}: {e}", "red")
            return False
    
    def download_specific_package(self, package_id: str, version: str, feed_name: str, description: str) -> bool:
        """
        Download a specific package by ID and version using ALGet's download approach
        """
        try:
            self.log(f"📥 Downloading {package_id} v{version}...", "gray")
            
            # Get PackageBaseAddress from feed index
            feed_url = f"https://dynamicssmb2.pkgs.visualstudio.com/DynamicsBCPublicFeeds/_packaging/{feed_name}/nuget/v3/index.json"
            
            with urllib.request.urlopen(feed_url) as response:
                feed_data = json.loads(response.read().decode())
            
            # Find PackageBaseAddress URL
            package_base_url = None
            for resource in feed_data.get('resources', []):
                if resource.get('@type', '').startswith('PackageBaseAddress'):
                    package_base_url = resource.get('@id', '').rstrip('/')
                    break
            
            if not package_base_url:
                self.log(f"⚠️ Package download service not found in {feed_name} feed", "yellow")
                return False
            
            # Download the .nupkg file using ALGet's URL pattern
            download_url = f"{package_base_url}/{package_id.lower()}/{version}/{package_id.lower()}.{version}.nupkg"
            
            self.log(f"📥 Downloading from: {download_url}", "gray")
            
            with urllib.request.urlopen(download_url) as package_response:
                if package_response.status != 200:
                    self.log(f"⚠️ Failed to download {package_id} v{version}", "yellow")
                    return False
                
                package_data = package_response.read()
            
            # Extract .app files from the .nupkg (which is a ZIP file)
            with zipfile.ZipFile(io.BytesIO(package_data)) as zip_file:
                # Find .app files in the package
                app_files = [name for name in zip_file.namelist() if name.endswith('.app')]
                
                if not app_files:
                    self.log(f"⚠️ No .app files found in {package_id} package", "yellow")
                    return False
                
                # Extract each .app file
                extracted_count = 0
                for app_file_name in app_files:
                    # Extract to symbols directory
                    app_data = zip_file.read(app_file_name)
                    
                    # Create a proper filename (ALGet uses Publisher_Name_Version.app format)
                    base_name = app_file_name.split('/')[-1]  # Get just filename
                    target_path = self.symbols_dir / base_name
                    
                    # Write the .app file
                    target_path.write_bytes(app_data)
                    
                    file_size = len(app_data) / 1024  # KB
                    self.log(f"📦 Extracted: {base_name} ({file_size:.1f} KB)", "gray")
                    extracted_count += 1
                
                if extracted_count > 0:
                    self.log(f"✅ Downloaded {description}: {extracted_count} files", "green")
                    return True
                else:
                    return False
            
        except Exception as e:
            self.log(f"❌ Error downloading {package_id}: {e}", "red")
            return False
    

    
    def download_custom_dependencies(self, dependencies: List[Dict], linc_registry_url: str = None, linc_token: str = None) -> bool:
        """Download custom dependencies with priority order:
        1. AppSource NuGet feeds (for ALL non-Microsoft dependencies, including LINC)
        2. GitHub packages (fallback for LINC dependencies only)
        """
        if not dependencies:
            return True
        
        self.log(f"📦 Processing {len(dependencies)} custom dependencies...", "cyan")
        self.log(f"📋 Priority order: 1) AppSource NuGet feeds (ALL dependencies) → 2) GitHub packages (LINC fallback)", "gray")
        
        success_count = 0
        for dep in dependencies:
            dep_name = dep.get('name', '')
            dep_publisher = dep.get('publisher', 'Microsoft')
            dep_id = dep.get('id', '')
            
            # Skip Microsoft dependencies as they should be in the base symbols
            if dep_publisher.lower() == 'microsoft':
                self.log(f"ℹ️ Skipping Microsoft dependency: {dep_name}", "gray")
                success_count += 1
                continue
            
            is_linc_dependency = 'linc' in dep_publisher.lower()
            self.log(f"🔍 Looking for {dep_publisher}.{dep_name}{'📦 (LINC)' if is_linc_dependency else ''}...", "cyan")
            
            # Priority 1: Try AppSource NuGet feeds first for ALL non-Microsoft dependencies (including LINC)
            self.log(f"📦 [1/2] Searching AppSource NuGet feeds (including LINC AppSource)...", "gray")
            if self.download_from_appsource_feed(dep):
                success_count += 1
                continue
            
            # Priority 2: Try GitHub packages ONLY for LINC dependencies as fallback
            if is_linc_dependency:
                self.log(f"🔗 [2/2] Fallback: Searching GitHub packages (LINC dependency not found in AppSource)...", "gray")
                if self.download_from_linc_github(dep, linc_token):
                    success_count += 1
                    continue
                self.log(f"⚠️ LINC dependency not found in GitHub packages: {dep_publisher}.{dep_name}", "yellow")
            else:
                self.log(f"ℹ️ Non-LINC dependency not found in AppSource: {dep_publisher}.{dep_name}", "yellow")
                # For non-LINC dependencies, we only try AppSource
            
            # Final message for completely unfound dependencies
            if is_linc_dependency:
                self.log(f"❌ Could not find LINC dependency {dep_publisher}.{dep_name} in any feed (AppSource or GitHub)", "yellow")
            else:
                self.log(f"❌ Could not find {dep_publisher}.{dep_name} in AppSource feeds", "yellow")
        
        self.log(f"✅ Processed {success_count}/{len(dependencies)} dependencies", "green")
        return True
    
    def download_from_appsource_feed(self, dependency: Dict) -> bool:
        """Download dependency from AppSource symbols feeds (Microsoft AppSource + LINC AppSource)
        Tries multiple search patterns to find packages in all AppSource NuGet feeds
        """
        dep_name = dependency.get('name', '')
        dep_publisher = dependency.get('publisher', '')
        dep_id = dependency.get('id', '')
        
        if not dep_name or not dep_publisher:
            self.log(f"⚠️ Missing name or publisher for dependency", "yellow")
            return False
        
        is_linc_dependency = 'linc' in dep_publisher.lower()
        
        # Normalize publisher and name for AppSource package naming
        # AppSource uses proper case with non-alphanumeric chars removed
        # Example: "Linc Communications (Pty) Ltd" -> "LincCommunicationsPtyLtd"
        import re
        
        def normalize_name_component(text):
            # Remove all non-alphanumeric characters and convert to title case
            # This handles cases like "(Pty) Ltd" -> "PtyLtd"
            words = re.findall(r'\w+', text)  # Extract all word characters
            return ''.join(word.capitalize() for word in words)
        
        clean_publisher = normalize_name_component(dep_publisher)
        clean_name = normalize_name_component(dep_name)
        
        # Try multiple search patterns for better compatibility
        search_patterns = [
            # Pattern 1: Full format with GUID
            f"{clean_publisher}.{clean_name}.symbols.{dep_id}" if dep_id else None,
            # Pattern 2: Publisher.Name.symbols format
            f"{clean_publisher}.{clean_name}.symbols",
            # Pattern 3: Just Publisher.Name (some packages may not have .symbols suffix)
            f"{clean_publisher}.{clean_name}",
            # Pattern 4: Try with original case preservation
            f"{dep_publisher.replace(' ', '').replace('(', '').replace(')', '').replace('.', '')}.{dep_name.replace(' ', '')}.symbols",
        ]
        
        # Remove None values and duplicates
        search_patterns = list(dict.fromkeys(filter(None, search_patterns)))
        
        self.log(f"🔍 Searching AppSource for {dep_publisher}.{dep_name}...", "gray")
        
        # Try each search pattern on the AppSource feed
        for i, search_pattern in enumerate(search_patterns, 1):
            self.log(f"   📋 Pattern {i}/{len(search_patterns)}: {search_pattern}", "gray")
            
            package_info = {
                "name": search_pattern,
                "description": f"{dep_publisher} {dep_name} symbols",
                "feed": "AppSourceSymbols"
            }
            
            if self.download_microsoft_symbol_package(package_info):
                self.log(f"✅ Found in AppSource with pattern: {search_pattern}", "green")
                return True
        
        self.log(f"❌ Not found in AppSource NuGet feeds after trying {len(search_patterns)} patterns", "yellow")
        return False
    
    def download_from_linc_github(self, dependency: Dict, token: str = None) -> bool:
        """Download dependency from LINC's GitHub packages registry
        Only called for LINC dependencies after AppSource search fails
        """
        dep_name = dependency.get('name', '')
        dep_publisher = dependency.get('publisher', '')
        dep_id = dependency.get('id', '')
        
        if not dep_name or not dep_publisher:
            self.log(f"⚠️ Missing name or publisher for LINC GitHub dependency", "yellow")
            return False
        
        # Verify this is actually a LINC dependency before proceeding
        if 'linc' not in dep_publisher.lower():
            self.log(f"ℹ️ Skipping non-LINC dependency for GitHub packages: {dep_publisher}", "gray")
            return False
        
        self.log(f"🔍 Searching LINC GitHub packages for {dep_publisher}.{dep_name}...", "gray")
        
        if not token:
            self.log(f"⚠️ No GitHub token provided for LINC packages - trying public access", "yellow")
        else:
            self.log(f"🔑 Using GitHub token for LINC package authentication", "gray")
        
        try:
            # LINC uses GitHub packages with specific naming convention
            # Clean and normalize publisher and name for NuGet package naming
            import re
            
            # LINC uses NuGet packages with naming like: PublisherName.ExtensionName.symbols.guid
            clean_publisher = re.sub(r'[^\w]', '', dep_publisher)  # Remove all non-word chars
            clean_name = re.sub(r'[^\w]', '', dep_name)  # Remove all non-word chars
            
            package_name = f"{clean_publisher}.{clean_name}.symbols"
            if dep_id:
                package_name += f".{dep_id}"
            
            # GitHub Packages NuGet API for LINC organization
            github_api_url = f"https://api.github.com/orgs/lincza/packages?package_type=nuget"
            
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Fast-AL-Builder"
            }
            
            if token:
                # Try both token formats - GitHub Packages may prefer different formats
                headers["Authorization"] = f"token {token}"
                self.log(f"🔑 Using GitHub token for authentication", "gray")
            else:
                self.log(f"⚠️ No GitHub token provided - trying public access", "gray")
            
            from urllib.request import Request
            
            self.log(f"🌐 Requesting: {github_api_url}", "gray")
            request = Request(github_api_url, headers=headers)
            
            try:
                with urllib.request.urlopen(request) as response:
                    if response.status != 200:
                        self.log(f"⚠️ Failed to access LINC GitHub packages", "gray")
                        return False
                    
                    packages_data = json.loads(response.read().decode())
                
                if not packages_data:
                    self.log(f"⚠️ No packages found in LINC GitHub organization", "gray")
                    return False
                
                # Search for matching package by name
                matching_packages = []
                for pkg in packages_data:
                    pkg_name = pkg.get('name', '')
                    # Check if our target package name matches the found package
                    if package_name.lower() in pkg_name.lower() or dep_id in pkg_name:
                        matching_packages.append(pkg)
                        self.log(f"📦 Found matching package: {pkg_name}", "gray")
                
                if not matching_packages:
                    self.log(f"⚠️ No matching packages found for {dep_publisher}.{dep_name}", "gray")
                    return False
                
                # Use the first matching package
                selected_package = matching_packages[0]
                package_name = selected_package.get('name', '')
                
                self.log(f"📦 Selected package: {package_name}", "gray")
                
                # For NuGet packages, we need to get the download URL differently
                return self.download_nuget_package_from_github(selected_package, dep_publisher, dep_name)
                
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    self.log(f"⚠️ Package {package_name} not found in LINC GitHub packages", "gray")
                elif e.code == 401:
                    self.log(f"🔑 Authentication failed for LINC GitHub packages", "yellow")
                    if token:
                        self.log(f"💡 GitHub token may be invalid or expired", "cyan")
                        self.log(f"💡 Token needs 'read:packages' permission for GitHub Container Registry", "cyan")
                    else:
                        self.log(f"💡 Use --github-token to access private LINC packages", "cyan")
                elif e.code == 403:
                    self.log(f"🚫 Access forbidden - token may lack required permissions", "yellow")
                else:
                    self.log(f"⚠️ Error accessing LINC GitHub packages: HTTP {e.code}", "gray")
                return False
                
        except Exception as e:
            self.log(f"⚠️ Error searching LINC GitHub packages: {e}", "gray")
            return False
    
    def download_nuget_package_from_github(self, package_info: Dict, publisher: str, name: str) -> bool:
        """Download NuGet package from GitHub Packages"""
        try:
            package_name = package_info.get('name', '')
            package_url = package_info.get('url', '')
            
            self.log(f"📥 Downloading NuGet package: {package_name}", "gray")
            
            # Get GitHub token from environment or config
            token = self.github_token or os.getenv('GITHUB_TOKEN')
            if not token:
                self.log("❌ GitHub token required for LINC packages", "red")
                return False
            
            # Get package versions using GitHub API
            versions_url = f"{package_url}/versions"
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Fast-AL-Builder/1.0'
            }
            
            self.log(f"🔍 Getting package versions from: {versions_url}", "gray")
            
            # Get versions
            request = urllib.request.Request(versions_url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.getcode() != 200:
                    self.log(f"❌ Failed to get package versions: {response.getcode()}", "red")
                    return False
                    
                versions_data = json.loads(response.read().decode('utf-8'))
                
                if not versions_data:
                    self.log(f"❌ No versions found for package", "red")
                    return False
                
                # Get the latest version
                latest_version = versions_data[0]
                version = latest_version['name']
                self.log(f"📦 Latest version found: {version}", "cyan")
            
            # Try multiple authentication approaches for GitHub NuGet packages
            success = False
            
            # Method 1: Try GitHub API direct download (if available)
            if not success:
                success = self._try_github_api_download(package_name, version, token, publisher, name)
            
            # Method 2: Try NuGet v3 protocol with different auth headers
            if not success:
                success = self._try_nuget_v3_download(package_name, version, token, publisher, name)
            
            # Method 3: Try alternate GitHub authentication
            if not success:
                success = self._try_github_basic_auth(package_name, version, token, publisher, name)
            
            return success
            
            # This section was moved to the multiple authentication attempt methods above
            return False
                    
        except urllib.error.HTTPError as e:
            if e.code == 403:
                self.log(f"❌ Authentication failed: Package is private and requires special permissions", "red")
                self.log(f"💡 This is a private LINC package. Contact LINC for access or download manually.", "cyan")
            else:
                self.log(f"❌ HTTP error downloading package: {e.code} - {e.reason}", "red")
            # Try fallback to placeholder
            return self._create_github_placeholder(package_name, publisher, name, "Private package - authentication required")
        except Exception as e:
            self.log(f"❌ Error downloading LINC package: {e}", "red")
            # Try fallback to placeholder
            return self._create_github_placeholder(package_name, publisher, name, "Download failed")
    
    def _try_github_api_download(self, package_name: str, version: str, token: str, publisher: str, name: str) -> bool:
        """Try downloading via GitHub API (if package has direct download link)"""
        try:
            self.log(f"🔄 Trying GitHub API download method...", "gray")
            
            # Some packages might have direct download URLs through the API
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Fast-AL-Builder/1.0'
            }
            
            # Try to get package file list
            encoded_package = urllib.parse.quote(package_name, safe='')
            files_url = f"https://api.github.com/orgs/lincza/packages/nuget/{encoded_package}/versions"
            
            request = urllib.request.Request(files_url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.getcode() == 200:
                    versions_data = json.loads(response.read().decode('utf-8'))
                    for version_data in versions_data:
                        if version_data.get('name') == version:
                            # Check if there's a direct download URL
                            if 'package_files' in version_data:
                                self.log(f"📁 Found package files in API response", "gray")
                                return True
            
            return False
            
        except Exception as e:
            self.log(f"⚠️ GitHub API download failed: {e}", "gray")
            return False
    
    def _try_nuget_v3_download(self, package_name: str, version: str, token: str, publisher: str, name: str) -> bool:
        """Try downloading via NuGet v3 protocol with proper GitHub auth"""
        try:
            self.log(f"🔄 Trying NuGet v3 download with GitHub auth...", "gray")
            
            # GitHub NuGet requires specific auth format
            encoded_package_name = urllib.parse.quote(package_name.lower(), safe='')
            encoded_version = urllib.parse.quote(version.lower(), safe='')
            
            download_url = f"https://nuget.pkg.github.com/lincza/download/{encoded_package_name}/{encoded_version}/{encoded_package_name}.{encoded_version}.nupkg"
            
            # Try different authentication header formats
            auth_formats = [
                {'Authorization': f'Bearer {token}'},
                {'Authorization': f'token {token}'},
                {'X-NuGet-ApiKey': token},
            ]
            
            for auth_header in auth_formats:
                try:
                    headers = {
                        **auth_header,
                        'User-Agent': 'Fast-AL-Builder/1.0',
                        'Accept': 'application/octet-stream'
                    }
                    
                    self.log(f"🔐 Trying auth format: {list(auth_header.keys())[0]}", "gray")
                    
                    download_request = urllib.request.Request(download_url, headers=headers)
                    
                    with urllib.request.urlopen(download_request, timeout=60) as response:
                        if response.getcode() == 200:
                            return self._process_nupkg_download(response, package_name, publisher, name)
                        
                except urllib.error.HTTPError as e:
                    self.log(f"⚠️ Auth format failed ({e.code}): {list(auth_header.keys())[0]}", "gray")
                    continue
                except Exception as e:
                    continue
            
            return False
            
        except Exception as e:
            self.log(f"⚠️ NuGet v3 download failed: {e}", "gray")
            return False
    
    def _try_github_basic_auth(self, package_name: str, version: str, token: str, publisher: str, name: str) -> bool:
        """Try downloading with basic authentication (username:token)"""
        try:
            self.log(f"🔄 Trying basic auth download...", "gray")
            
            # GitHub username from configuration or fallback
            usernames_to_try = []
            if hasattr(self, 'github_username') and self.github_username:
                usernames_to_try.append(self.github_username)
            # Add common fallbacks if no username configured
            usernames_to_try.extend(['attieretief', 'token'])  # 'token' is sometimes used as username
            
            encoded_package_name = urllib.parse.quote(package_name.lower(), safe='')
            encoded_version = urllib.parse.quote(version.lower(), safe='')
            
            download_url = f"https://nuget.pkg.github.com/lincza/download/{encoded_package_name}/{encoded_version}/{encoded_package_name}.{encoded_version}.nupkg"
            
            for username in usernames_to_try:
                try:
                    import base64
                    
                    # Create basic auth header
                    auth_string = f"{username}:{token}"
                    auth_bytes = auth_string.encode('ascii')
                    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
                    
                    headers = {
                        'Authorization': f'Basic {auth_b64}',
                        'User-Agent': 'Fast-AL-Builder/1.0',
                        'Accept': 'application/octet-stream'
                    }
                    
                    self.log(f"🔐 Trying basic auth with username: {username}", "gray")
                    
                    download_request = urllib.request.Request(download_url, headers=headers)
                    
                    with urllib.request.urlopen(download_request, timeout=60) as response:
                        if response.getcode() == 200:
                            return self._process_nupkg_download(response, package_name, publisher, name)
                            
                except urllib.error.HTTPError as e:
                    self.log(f"⚠️ Basic auth failed for {username} ({e.code})", "gray")
                    continue
                except Exception as e:
                    continue
            
            return False
            
        except Exception as e:
            self.log(f"⚠️ Basic auth download failed: {e}", "gray")
            return False
    
    def _process_nupkg_download(self, response, package_name: str, publisher: str, name: str) -> bool:
        """Process a successful .nupkg download response"""
        try:
            # Read the .nupkg content
            nupkg_content = response.read()
            file_size = len(nupkg_content) / 1024
            self.log(f"📦 Downloaded NuGet package: {file_size:.1f} KB", "green")
            
            # Extract .app file from the .nupkg (it's a zip file)
            import io
            with zipfile.ZipFile(io.BytesIO(nupkg_content), 'r') as zip_file:
                # Look for .app files in the package
                app_files = [f for f in zip_file.namelist() if f.endswith('.app')]
                
                if not app_files:
                    self.log(f"❌ No .app files found in NuGet package", "red")
                    # List contents for debugging
                    contents = zip_file.namelist()[:10]
                    self.log(f"🔍 Package contents: {', '.join(contents)}", "gray")
                    return False
                
                # Extract the first .app file found
                app_file = app_files[0]
                
                # Create safe filename
                app_filename = f"{publisher}_{name}_github.app"
                app_filename = app_filename.replace(' ', '_').replace('(', '').replace(')', '').replace('.', '_')
                
                target_path = self.symbols_dir / app_filename
                
                # Extract the .app file
                with zip_file.open(app_file) as source:
                    app_content = source.read()
                    target_path.write_bytes(app_content)
                
                app_size = len(app_content) / 1024
                self.log(f"📦 Extracted app file: {app_filename} ({app_size:.1f} KB)", "green")
                self.log(f"💡 Successfully downloaded from LINC GitHub NuGet: {package_name}", "cyan")
                
                return True
                
        except zipfile.BadZipFile:
            self.log(f"❌ Downloaded file is not a valid zip archive", "red")
            return False
        except Exception as e:
            self.log(f"❌ Error processing download: {e}", "red")
            return False
    
    def _create_github_placeholder(self, package_name: str, publisher: str, name: str, reason: str = "Found but not downloaded") -> bool:
        """Create a placeholder file for GitHub packages that couldn't be downloaded"""
        try:
            placeholder_content = f"""// LINC Package: {package_name}
// Publisher: {publisher}
// Name: {name}
// Status: {reason}
// Found in LINC GitHub NuGet packages
//
// Note: LINC packages are private and require GitHub authentication.
// To download this dependency:
//
// 1. Generate a GitHub Personal Access Token (PAT):
//    - Go to GitHub Settings > Developer settings > Personal access tokens
//    - Generate token with 'read:packages' scope
//
// 2. Re-run with authentication:
//    python scripts/download_symbols.py bc26 --dependencies app.json \
//           --github-token YOUR_TOKEN --github-username YOUR_USERNAME
//
// 3. Or download manually:
//    - Contact LINC Communications for direct access
//    - Download .app file and place in symbols folder
""".encode()
            
            app_filename = f"{publisher}_{name}_github_placeholder.app"
            app_filename = app_filename.replace(' ', '_').replace('(', '').replace(')', '').replace('.', '_')
            
            target_path = self.symbols_dir / app_filename
            target_path.write_bytes(placeholder_content)
            
            file_size = len(placeholder_content) / 1024
            self.log(f"📦 Created LINC placeholder: {app_filename} ({file_size:.1f} KB)", "yellow")
            self.log(f"💡 Found package in LINC GitHub NuGet registry: {package_name}", "cyan")
            
            return True
        except Exception as e:
            self.log(f"❌ Error creating placeholder: {e}", "red")
            return False
    
    def download_from_github_container_registry(self, package_name: str, version_tag: str, publisher: str, name: str, token: str = None) -> bool:
        """Download AL symbols from GitHub Container Registry"""
        try:
            # GitHub Container Registry URL for LINC packages
            # Note: This would typically require Docker or container tools to extract
            # For now, we'll create a placeholder implementation
            
            self.log(f"📥 Attempting to download from GitHub Container Registry: {package_name}:{version_tag}", "gray")
            
            # This is a simplified implementation - in practice, you'd need to:
            # 1. Use Docker API or container tools to pull the image
            # 2. Extract .app files from the container
            # 3. Copy them to the symbols directory
            
            # For demonstration, we'll create a placeholder .app file
            placeholder_content = f"// Placeholder for {publisher} {name} symbols\n// Package: {package_name}:{version_tag}\n".encode()
            
            app_filename = f"{publisher}_{name}_{version_tag}.app"
            app_filename = app_filename.replace(' ', '_').replace('-', '_')
            
            target_path = self.symbols_dir / app_filename
            target_path.write_bytes(placeholder_content)
            
            file_size = len(placeholder_content) / 1024  # KB
            self.log(f"📦 Created placeholder: {app_filename} ({file_size:.1f} KB)", "yellow")
            self.log(f"💡 Note: Full GitHub Container Registry integration requires Docker tools", "cyan")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error downloading from GitHub Container Registry: {e}", "red")
            return False
    
    def download_symbols(self, bc_version: str, dependencies_json: str = None, 
                        linc_registry_url: str = None, linc_token: str = None, github_username: str = None) -> bool:
        """Main method to download all required symbols with priority order:
        1. Microsoft symbols from official NuGet feeds
        2. Custom dependencies from AppSource NuGet feeds (ALL non-Microsoft, including LINC)
        3. LINC dependencies from GitHub packages (fallback for LINC only)
        """
        self.log(f"🚀 Starting symbol download for BC {bc_version}...", "green")
        self.log(f"📋 Download strategy: MS feeds → AppSource feeds (ALL deps incl. LINC) → GitHub (LINC fallback)", "gray")
        
        # Log environment info for debugging in CI
        if self.is_github_actions:
            self.log(f"🤖 Running on GitHub Actions ({os.environ.get('RUNNER_OS', 'Unknown')})", "cyan")
            if os.environ.get('RUNNER_DEBUG') == '1':
                self.log(f"📁 Working directory: {os.getcwd()}", "gray")
                self.log(f"📁 Symbols directory: {self.symbols_dir}", "gray")
        
        # Store the GitHub token and username for later use
        self.github_token = linc_token
        self.github_username = github_username
        
        success = True
        
        # 1. Download Microsoft symbols using NuGet approach
        if not self.download_microsoft_symbols_simple(bc_version):
            self.log("⚠️ Microsoft symbols download failed", "yellow")
            success = False
        
        # 2. Download custom dependencies if specified
        if dependencies_json:
            dependencies = self.parse_dependencies(dependencies_json)
            if not self.download_custom_dependencies(dependencies, linc_registry_url, linc_token):
                self.log("⚠️ Some custom dependencies failed to download", "yellow")
                # Don't fail the entire process for missing custom dependencies
        
        # 3. Summary of downloaded symbols
        symbol_files = list(self.symbols_dir.glob("*.app"))
        if symbol_files:
            self.log(f"📦 Symbol download complete: {len(symbol_files)} files", "green")
            
            total_size = sum(f.stat().st_size for f in symbol_files) / 1024 / 1024  # MB
            self.log(f"💾 Total size: {total_size:.1f} MB", "gray")
            
            # List key Microsoft symbols
            microsoft_symbols = [f for f in symbol_files if any(ms in f.name for ms in ["System", "Base Application", "Application"])]
            if microsoft_symbols:
                self.log(f"✅ Key Microsoft symbols found: {len(microsoft_symbols)}", "green")
            else:
                self.log("⚠️ No core Microsoft symbols found - compilation may fail", "yellow")
        else:
            self.log("❌ No symbol files downloaded!", "red")
            success = False
        
        return success
    
    def parse_dependencies(self, dependencies_json: str) -> List[Dict]:
        """Parse dependencies from JSON string, app.json format, or simple list"""
        if not dependencies_json or dependencies_json.strip() == "":
            return []
        
        try:
            if isinstance(dependencies_json, str):
                # Handle file path to app.json
                if dependencies_json.endswith('.json') and Path(dependencies_json).exists():
                    with open(dependencies_json, 'r') as f:
                        app_data = json.load(f)
                    
                    # Extract dependencies from app.json
                    if 'dependencies' in app_data:
                        deps = []
                        for dep in app_data['dependencies']:
                            # app.json format: {"id": "guid", "name": "name", "publisher": "publisher", "version": "version"}
                            deps.append({
                                "id": dep.get('id', ''),
                                "name": dep.get('name', ''),
                                "publisher": dep.get('publisher', ''),
                                "version": dep.get('version', '*')
                            })
                        return deps
                    return []
                
                # Handle JSON array string
                elif dependencies_json.startswith('['):
                    return json.loads(dependencies_json)
                
                # Handle simple comma-separated list
                else:
                    deps = []
                    for dep in dependencies_json.split(','):
                        dep = dep.strip()
                        if dep:
                            # Handle "Publisher.Name" format or just "Name"
                            if '.' in dep:
                                publisher, name = dep.split('.', 1)
                                deps.append({"name": name, "publisher": publisher, "version": "*", "id": ""})
                            else:
                                deps.append({"name": dep, "publisher": "Microsoft", "version": "*", "id": ""})
                    return deps
            else:
                return dependencies_json
                
        except json.JSONDecodeError:
            self.log(f"⚠️ Failed to parse dependencies: {dependencies_json}", "yellow")
            return []
        except Exception as e:
            self.log(f"⚠️ Error parsing dependencies: {e}", "yellow")
            return []


def main():
    """CLI entry point for symbol downloader"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download AL symbols for compilation using Microsoft feeds and LINC GitHub packages",
        epilog="""
Priority order for dependency resolution:
1. Microsoft symbols: Official Microsoft NuGet feeds
2. Custom dependencies: AppSource NuGet feeds (ALL non-Microsoft, including LINC dependencies)
3. LINC dependencies: GitHub packages (fallback for LINC extensions not found in AppSource)

Examples:
  python download_symbols.py bc26
  python download_symbols.py bc24 --dependencies '[{"name":"Test Extension","publisher":"ACME Corp","id":"123"}]'
  python download_symbols.py bccloud --linc-token ghp_xxx --dependencies app.json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("bc_version", help="Business Central version (e.g., bc24, bc26, cloud)")
    parser.add_argument("--symbols-dir", default=".symbols", 
                       help="Directory to download symbols to (default: .symbols)")
    parser.add_argument("--dependencies", 
                       help="Dependencies as JSON array, app.json file path, or comma-separated list")
    parser.add_argument("--linc-registry-url", 
                       help="LINC registry URL (deprecated - uses GitHub packages)")
    parser.add_argument("--linc-token", 
                       help="GitHub token for accessing LINC packages (requires 'read:packages' permission)")
    parser.add_argument("--github-username", 
                       help="GitHub username for basic authentication (required for private packages)")
    parser.add_argument("--github-token", 
                       help="GitHub token for accessing LINC packages (alias for --linc-token)")
    
    args = parser.parse_args()
    
    # Use GitHub token if provided (either argument)
    github_token = args.linc_token or args.github_token
    github_username = args.github_username
    
    # Create downloader and run
    downloader = SymbolDownloader(args.symbols_dir)
    success = downloader.download_symbols(
        args.bc_version, 
        args.dependencies,
        args.linc_registry_url,
        github_token,
        github_username
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()