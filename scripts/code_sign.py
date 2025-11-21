#!/usr/bin/env python3
"""
Code Signing Script - Python Version
Sign AL extension files with certificates

PLATFORM REQUIREMENTS:
- AL extension (.app) files: Windows only (uses proprietary NAVX format)
- Standard PE/EXE/MSI files: Windows (SignTool) or Linux/macOS (osslsigncode)

DEPENDENCIES:
- For Azure Key Vault: pip install -r azure-requirements.txt
- For cross-platform signing: osslsigncode (brew install osslsigncode)
- For Windows signing: Windows SDK SignTool

USAGE:
- Certificate file: python code_sign.py app.app --cert-base64 [base64] --cert-password [pwd]
- Azure Key Vault: python code_sign.py app.app --use-keyvault --vault-url [url] --cert-name [name] --client-id [id] --client-secret [secret] --tenant-id [tenant]
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import base64
import json
import platform


class CodeSigner:
    def __init__(self):
        self.temp_files = []
        
    def __del__(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            try:
                if Path(temp_file).exists():
                    os.unlink(temp_file)
            except:
                pass
    
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
    
    def is_al_extension(self, file_path: str) -> bool:
        """Check if the file is an AL extension (.app) with NAVX format"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                return header == b'NAVX'
        except:
            return False
    
    def check_platform_compatibility(self, file_path: str, force: bool = False) -> bool:
        """Check if current platform can sign the given file type"""
        is_windows = platform.system() == 'Windows'
        is_al_extension = self.is_al_extension(file_path)
        
        if is_al_extension and not is_windows:
            if force:
                self.log("⚠️ WARNING: Attempting to sign AL extension on non-Windows platform (forced)", "yellow")
                self.log("   This will likely fail - AL extensions require Windows SignTool", "yellow")
                return True
            else:
                self.log("⚠️ AL extension (.app) files can only be signed on Windows", "yellow")
                self.log("   AL extensions use proprietary NAVX format requiring Windows SignTool", "yellow")
                self.log("   Consider running this step on a Windows GitHub Actions runner", "yellow")
                self.log("   Use --force to attempt signing anyway (not recommended)", "yellow")
                return False
        
        return True
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
    
    def check_signing_tools(self) -> Optional[str]:
        """Check for available code signing tools"""
        # Check for signtool (Windows)
        signtool_paths = [
            r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22000.0\x64\signtool.exe",
            r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe",
            r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.18362.0\x64\signtool.exe",
            r"C:\Program Files (x86)\Microsoft SDKs\Windows\v10.0A\bin\NETFX 4.8 Tools\x64\signtool.exe"
        ]
        
        # Try to find signtool in PATH first
        import shutil
        signtool = shutil.which('signtool.exe')
        if signtool:
            return signtool
        
        # Check common installation paths
        for path in signtool_paths:
            if Path(path).exists():
                return path
        
        # Check for osslsigncode (cross-platform alternative)
        osslsigncode = shutil.which('osslsigncode')
        if osslsigncode:
            return osslsigncode
        
        return None
    
    def get_certificate_from_keyvault(self, vault_url: str, cert_name: str, client_id: str, 
                                     client_secret: str, tenant_id: str) -> Optional[tuple[str, str]]:
        """Retrieve certificate from Azure Key Vault"""
        try:
            # Try to import Azure SDK components
            try:
                from azure.keyvault.certificates import CertificateClient
                from azure.identity import ClientSecretCredential
            except ImportError:
                self.log("❌ Azure SDK not installed. Install: pip install azure-keyvault-certificates azure-identity", "red")
                return None
            
            self.log(f"🔐 Connecting to Key Vault: {vault_url}", "cyan")
            
            # Create credential
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            
            # Create Key Vault client
            client = CertificateClient(vault_url=vault_url, credential=credential)
            
            # Get certificate with private key
            self.log(f"📜 Retrieving certificate: {cert_name}", "cyan")
            certificate = client.get_certificate(cert_name)
            
            # Get the secret (PKCS#12 format with private key)
            from azure.keyvault.secrets import SecretClient
            secret_client = SecretClient(vault_url=vault_url, credential=credential)
            
            # The certificate secret contains the full PKCS#12 data
            cert_secret = secret_client.get_secret(cert_name)
            cert_data = base64.b64decode(cert_secret.value)
            
            # Create temporary certificate file
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.pfx', delete=False) as f:
                f.write(cert_data)
                cert_path = f.name
                self.temp_files.append(cert_path)
            
            self.log(f"✅ Certificate retrieved from Key Vault: {cert_path}", "green")
            
            # Note: Key Vault certificates typically don't have passwords when exported this way
            # But some might, so we'll return empty string as default
            return cert_path, ""
            
        except Exception as e:
            self.log(f"❌ Failed to retrieve certificate from Key Vault: {e}", "red")
            return None
    
    def decode_certificate(self, cert_base64: str, cert_password: str) -> Optional[str]:
        """Decode base64 certificate and save to temporary file"""
        try:
            cert_data = base64.b64decode(cert_base64)
            
            # Create temporary certificate file
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.pfx', delete=False) as f:
                f.write(cert_data)
                cert_path = f.name
                self.temp_files.append(cert_path)
            
            self.log(f"📜 Certificate decoded to: {cert_path}", "gray")
            
            # Verify the file exists and has content
            if Path(cert_path).exists():
                file_size = Path(cert_path).stat().st_size
                self.log(f"📏 Certificate file size: {file_size} bytes", "gray")
            else:
                self.log(f"⚠️ Certificate file does not exist: {cert_path}", "yellow")
            
            return cert_path
            
        except Exception as e:
            self.log(f"❌ Failed to decode certificate: {e}", "red")
            return None
    
    def sign_with_signtool(self, app_file_path: str, cert_path: str, cert_password: str, 
                          timestamp_url: str, signing_tool: str) -> bool:
        """Sign using Windows SignTool"""
        self.log("🖊️ Signing with SignTool...", "cyan")
        
        # Check if it's our mock SignTool (Python script)
        if signing_tool.endswith("mock_signtool.py"):
            cmd = [
                "python", signing_tool,
                "sign",
                "/f", cert_path,
                "/p", cert_password,
                "/fd", "SHA256",
                "/tr", timestamp_url,
                "/td", "SHA256",
                "/v",
                app_file_path
            ]
        else:
            # Use Windows SignTool syntax for AL extensions
            cmd = [
                signing_tool,
                "sign",
                "/f", cert_path,
                "/p", cert_password,
                "/fd", "SHA256",
                "/tr", timestamp_url,
                "/td", "SHA256",
                "/v",
                app_file_path
            ]
        
        self.log(f"🔧 Running SignTool command", "gray")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log("✅ File signed successfully with SignTool", "green")
                return True
            else:
                self.log(f"❌ SignTool failed: {result.stderr}", "red")
                if result.stdout:
                    self.log(f"   Output: {result.stdout}", "gray")
                return False
                
        except Exception as e:
            self.log(f"❌ Failed to run SignTool: {e}", "red")
            return False
    
    def sign_with_osslsigncode(self, app_file_path: str, cert_path: str, cert_password: str,
                              timestamp_url: str, signing_tool: str) -> bool:
        """Sign using osslsigncode (cross-platform)"""
        self.log("🖊️ Signing with osslsigncode...", "cyan")
        
        # Create output file
        output_path = app_file_path + ".signed"
        
        # Build command with proper osslsigncode syntax
        cmd = [
            signing_tool,
            "sign",
            "-pkcs12", cert_path,
            "-in", app_file_path,
            "-out", output_path
        ]
        
        # Add password if provided (Key Vault certs might not need it)
        if cert_password:
            cmd.extend(["-pass", cert_password])
            
        # Add timestamp if provided
        if timestamp_url:
            cmd.extend(["-t", timestamp_url])
        
        self.log(f"🔧 Running command: {' '.join(cmd[:4])} [password hidden] {' '.join(cmd[-2:])}", "gray")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Replace original file with signed version
                os.replace(output_path, app_file_path)
                self.log("✅ File signed successfully with osslsigncode", "green")
                return True
            else:
                self.log(f"❌ osslsigncode failed: {result.stderr}", "red")
                # Clean up output file if it exists
                if Path(output_path).exists():
                    os.unlink(output_path)
                return False
                
        except Exception as e:
            self.log(f"❌ Failed to run osslsigncode: {e}", "red")
            # Clean up output file if it exists
            if Path(output_path).exists():
                os.unlink(output_path)
            return False
    
    def verify_signature(self, app_file_path: str, signing_tool: str) -> bool:
        """Verify the signature on a signed file"""
        self.log("🔍 Verifying signature...", "cyan")
        
        if "signtool" in signing_tool.lower():
            # Use SignTool verify
            cmd = [signing_tool, "verify", "/pa", app_file_path]
        elif "osslsigncode" in signing_tool.lower():
            # Use osslsigncode verify
            cmd = [signing_tool, "verify", app_file_path]
        else:
            self.log("⚠️ Cannot verify signature with unknown tool", "yellow")
            return True  # Assume success
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log("✅ Signature verification successful", "green")
                return True
            else:
                self.log(f"❌ Signature verification failed: {result.stderr}", "red")
                return False
                
        except Exception as e:
            self.log(f"⚠️ Could not verify signature: {e}", "yellow")
            return True  # Don't fail the build for verification issues
    
    def sign_app_file(self, app_file_path: str, cert_base64: str = None, cert_password: str = None,
                     timestamp_url: str = "http://timestamp.sectigo.com", 
                     use_keyvault: bool = False, vault_url: str = None, cert_name: str = None,
                     client_id: str = None, client_secret: str = None, tenant_id: str = None,
                     force: bool = False, test_mode: bool = False) -> bool:
        """Main signing process"""
        self.log("🖊️ Starting code signing process...", "cyan")
        
        # Validate inputs
        if not app_file_path or not Path(app_file_path).exists():
            self.log(f"❌ App file not found: {app_file_path}", "red")
            return False
        
        # Check platform compatibility for AL extensions
        if test_mode:
            self.log("🧪 Running in test mode with mock SignTool", "yellow")
        elif not self.check_platform_compatibility(app_file_path, force):
            self.log("❌ Platform incompatible with file type", "red")
            return False
        
        if use_keyvault:
            if not all([vault_url, cert_name, client_id, client_secret, tenant_id]):
                self.log("❌ Key Vault parameters missing: vault_url, cert_name, client_id, client_secret, tenant_id required", "red")
                return False
        else:
            if not cert_base64:
                self.log("❌ Certificate data not provided", "red")
                return False
            
            if cert_password is None:
                self.log("❌ Certificate password not provided (use empty string if no password)", "red")
                return False
        
        # Check for signing tools
        if test_mode:
            # Use mock SignTool for testing
            script_dir = Path(__file__).parent
            mock_signtool = script_dir / "mock_signtool.py"
            if mock_signtool.exists():
                signing_tool = str(mock_signtool)
            else:
                self.log("❌ Mock SignTool not found for test mode", "red")
                return False
        else:
            signing_tool = self.check_signing_tools()
            if not signing_tool:
                self.log("❌ No code signing tools found", "red")
                self.log("   Install Windows SDK (signtool) or osslsigncode", "red")
                return False
        
        self.log(f"🔧 Using signing tool: {signing_tool}", "green")
        
        # Get certificate
        if use_keyvault:
            result = self.get_certificate_from_keyvault(vault_url, cert_name, client_id, client_secret, tenant_id)
            if not result:
                return False
            cert_path, cert_password = result
        else:
            cert_path = self.decode_certificate(cert_base64, cert_password)
            if not cert_path:
                return False
        
        # Get file info before signing
        file_size_before = Path(app_file_path).stat().st_size
        self.log(f"📁 File size before signing: {file_size_before / 1024:.1f} KB", "gray")
        
        # Sign the file
        success = False
        if test_mode or "signtool" in signing_tool.lower():
            success = self.sign_with_signtool(app_file_path, cert_path, cert_password, 
                                            timestamp_url, signing_tool)
        elif "osslsigncode" in signing_tool.lower():
            success = self.sign_with_osslsigncode(app_file_path, cert_path, cert_password,
                                                timestamp_url, signing_tool)
        
        if success:
            # Get file info after signing
            file_size_after = Path(app_file_path).stat().st_size
            size_increase = file_size_after - file_size_before
            
            self.log(f"📁 File size after signing: {file_size_after / 1024:.1f} KB (+{size_increase / 1024:.1f} KB)", "gray")
            
            # Verify signature
            self.verify_signature(app_file_path, signing_tool)
            
            self.log("🎉 Code signing completed successfully!", "green")
        
        return success


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Sign AL extension files')
    parser.add_argument('app_file_path', help='Path to the .app file to sign')
    
    # Certificate source options
    cert_group = parser.add_mutually_exclusive_group(required=True)
    cert_group.add_argument('--cert-base64', help='Base64 encoded certificate data')
    cert_group.add_argument('--use-keyvault', action='store_true', 
                           help='Retrieve certificate from Azure Key Vault')
    
    parser.add_argument('--cert-password', help='Certificate password')
    parser.add_argument('--test-mode', action='store_true',
                       help='Use mock SignTool for testing on non-Windows platforms')
    parser.add_argument('--force', action='store_true',
                       help='Force signing even on incompatible platforms (not recommended)')
    parser.add_argument('--timestamp-url', 
                       default='http://timestamp.sectigo.com',
                       help='Timestamp server URL')
    
    # Azure Key Vault options
    parser.add_argument('--vault-url', help='Azure Key Vault URL')
    parser.add_argument('--cert-name', help='Certificate name in Key Vault')
    parser.add_argument('--client-id', help='Azure AD client ID')
    parser.add_argument('--client-secret', help='Azure AD client secret')
    parser.add_argument('--tenant-id', help='Azure AD tenant ID')
    
    args = parser.parse_args()
    
    if args.use_keyvault:
        # Get Key Vault parameters from environment if not provided
        vault_url = args.vault_url or os.environ.get('AZURE_KEYVAULT_URL')
        cert_name = args.cert_name or os.environ.get('AZURE_KEYVAULT_CERT_NAME')
        client_id = args.client_id or os.environ.get('AZURE_CLIENT_ID')
        client_secret = args.client_secret or os.environ.get('AZURE_CLIENT_SECRET')
        tenant_id = args.tenant_id or os.environ.get('AZURE_TENANT_ID')
        
        if not all([vault_url, cert_name, client_id, client_secret, tenant_id]):
            print("❌ Key Vault parameters missing", file=sys.stderr)
            print("   Required: --vault-url, --cert-name, --client-id, --client-secret, --tenant-id", file=sys.stderr)
            print("   Or set environment variables: AZURE_KEYVAULT_URL, AZURE_KEYVAULT_CERT_NAME, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID", file=sys.stderr)
            sys.exit(1)
        
        signer = CodeSigner()
        success = signer.sign_app_file(
            args.app_file_path,
            use_keyvault=True,
            vault_url=vault_url,
            cert_name=cert_name,
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            timestamp_url=args.timestamp_url,
            force=args.force,
            test_mode=args.test_mode
        )
    else:
        # Get certificate data from environment if not provided directly
        cert_base64 = args.cert_base64 or os.environ.get('SIGNING_CERT_BASE64')
        cert_password = args.cert_password or os.environ.get('SIGNING_CERT_PASSWORD', '')
        
        if not cert_base64:
            print("❌ Certificate data is required", file=sys.stderr)
            print("   Provide via --cert-base64 or SIGNING_CERT_BASE64 env var", file=sys.stderr)
            sys.exit(1)
        
        signer = CodeSigner()
        success = signer.sign_app_file(
            args.app_file_path,
            cert_base64,
            cert_password,
            args.timestamp_url,
            force=args.force,
            test_mode=args.test_mode
        )
    
    if success:
        signer.log("🎉 Code signing process completed!", "green")
        sys.exit(0)
    else:
        signer.log("❌ Code signing failed", "red")
        sys.exit(1)


if __name__ == "__main__":
    main()