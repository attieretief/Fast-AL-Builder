#!/usr/bin/env python3
"""Code signing helper that wraps AzureSignTool for AL extensions."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


class CodeSigner:
    """Signs .app files by shelling out to AzureSignTool."""

    def __init__(self, azuresigntool_path: Optional[str] = None):
        self.azuresigntool_path = azuresigntool_path or self._find_azuresigntool()

    def log(self, message: str, color: str = None):
        """Print colored log message."""
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

    def _find_azuresigntool(self) -> Optional[str]:
        """Attempt to locate AzureSignTool on the current runner."""
        candidates = [
            "AzureSignTool",
            "AzureSignTool.exe",
            "azuresigntool"
        ]

        for candidate in candidates:
            path = shutil.which(candidate)
            if path:
                return path

        common_paths = [
            r"C:\Program Files\AzureSignTool\AzureSignTool.exe",
            r"C:\Program Files (x86)\AzureSignTool\AzureSignTool.exe"
        ]

        for path in common_paths:
            if Path(path).exists():
                return path

        return None

    def _build_command(
        self,
        app_file_path: str,
        vault_url: str,
        cert_name: str,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        timestamp_url: str
    ) -> list[str]:
        return [
            self.azuresigntool_path,
            "sign",
            "-kvu", vault_url,
            "-kvc", cert_name,
            "-kvi", client_id,
            "-kvs", client_secret,
            "-kvt", tenant_id,
            "-tr", timestamp_url,
            "-v",
            app_file_path
        ]

    def sign_app_file(
        self,
        app_file_path: str,
        vault_url: str,
        cert_name: str,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        timestamp_url: str = "http://timestamp.digicert.com"
    ) -> bool:
        """Sign the provided .app file using AzureSignTool."""

        self.log("🖊️ Starting AzureSignTool signing", "cyan")

        if not self.azuresigntool_path:
            self.log("❌ AzureSignTool not found on PATH", "red")
            self.log("   Install AzureSignTool or provide --azuresigntool-path", "red")
            return False

        if not app_file_path or not Path(app_file_path).exists():
            self.log(f"❌ App file not found: {app_file_path}", "red")
            return False

        required = {
            "vault_url": vault_url,
            "cert_name": cert_name,
            "client_id": client_id,
            "client_secret": client_secret,
            "tenant_id": tenant_id
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            self.log(f"❌ Missing Azure Key Vault parameters: {', '.join(missing)}", "red")
            return False

        cmd = self._build_command(
            app_file_path,
            vault_url,
            cert_name,
            client_id,
            client_secret,
            tenant_id,
            timestamp_url
        )

        masked_cmd = cmd.copy()
        if "-kvs" in masked_cmd:
            secret_index = masked_cmd.index("-kvs") + 1
            if secret_index < len(masked_cmd):
                masked_cmd[secret_index] = "***"
        self.log(f"🔧 Executing: {' '.join(masked_cmd)}", "gray")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            self.log("❌ AzureSignTool executable not found", "red")
            return False

        if result.stdout:
            self.log(result.stdout.strip(), "gray")
        if result.returncode == 0:
            self.log("✅ File signed successfully", "green")
            return True

        self.log("❌ AzureSignTool failed", "red")
        if result.stderr:
            self.log(result.stderr.strip(), "red")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sign AL extension files with AzureSignTool")
    parser.add_argument("app_file_path", help="Path to the .app file to sign")
    parser.add_argument("--vault-url", help="Azure Key Vault URI", default=os.environ.get("AZ_KEY_VAULT_URI"))
    parser.add_argument("--cert-name", help="Azure Key Vault certificate name", default=os.environ.get("AZ_KEY_VAULT_CERTIFICATE_NAME"))
    parser.add_argument("--client-id", help="Azure AD application (client) ID", default=os.environ.get("AZ_KEY_VAULT_APPLICATION_ID"))
    parser.add_argument("--client-secret", help="Azure AD application secret", default=os.environ.get("AZ_KEY_VAULT_APPLICATION_SECRET"))
    parser.add_argument("--tenant-id", help="Azure AD tenant ID", default=os.environ.get("AZ_KEY_VAULT_TENANT_ID"))
    parser.add_argument("--timestamp-url", help="Timestamp server URL", default=os.environ.get("AZ_SIGN_TIMESTAMP_URL", "http://timestamp.digicert.com"))
    parser.add_argument("--azuresigntool-path", help="Explicit path to AzureSignTool")

    args = parser.parse_args()

    signer = CodeSigner(azuresigntool_path=args.azuresigntool_path)
    success = signer.sign_app_file(
        app_file_path=args.app_file_path,
        vault_url=args.vault_url,
        cert_name=args.cert_name,
        client_id=args.client_id,
        client_secret=args.client_secret,
        tenant_id=args.tenant_id,
        timestamp_url=args.timestamp_url
    )

    if success:
        signer.log("🎉 Code signing process completed!", "green")
        sys.exit(0)

    signer.log("❌ Code signing failed", "red")
    sys.exit(1)


if __name__ == "__main__":
    main()