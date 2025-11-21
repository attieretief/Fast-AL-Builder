#!/usr/bin/env python3
"""
Mock SignTool for testing AL extension signing logic on macOS
Simulates Windows SignTool behavior without actually signing
"""

import sys
import os
from pathlib import Path
import shutil
import time

def mock_signtool():
    """Simulate Windows SignTool.exe behavior"""
    
    args = sys.argv[1:]
    
    if len(args) < 2:
        print("Error: Invalid arguments", file=sys.stderr)
        sys.exit(1)
    
    command = args[0]
    
    if command == "sign":
        # Parse signing arguments
        cert_file = None
        cert_password = None
        app_file = None
        
        i = 1
        while i < len(args):
            if args[i] == "/f" and i + 1 < len(args):
                cert_file = args[i + 1]
                i += 2
            elif args[i] == "/p" and i + 1 < len(args):
                cert_password = args[i + 1]
                i += 2
            elif args[i] in ["/tr", "/t"] and i + 1 < len(args):
                # Timestamp URL
                i += 2
            elif args[i] in ["/fd", "/td"] and i + 1 < len(args):
                # Hash algorithm
                i += 2
            elif args[i] == "/v":
                # Verbose
                i += 1
            else:
                # Assume it's the file to sign
                app_file = args[i]
                i += 1
        
        # Validate inputs
        if not cert_file:
            print("Error: Certificate file not specified", file=sys.stderr)
            sys.exit(1)
        
        if not Path(cert_file).exists():
            print(f"Error: Certificate file not found: {cert_file}", file=sys.stderr)
            sys.exit(1)
        
        if not app_file or not Path(app_file).exists():
            print(f"Error: App file not found: {app_file}", file=sys.stderr)
            sys.exit(1)
        
        # Simulate signing process
        print(f"The following certificate will be used:")
        print(f"    Issued to: Mock Test Certificate")
        print(f"    Issued by: Mock CA")
        print(f"    Expires:   12/31/2025 11:59:59 PM")
        print(f"    SHA1 hash: 1234567890ABCDEF1234567890ABCDEF12345678")
        print()
        print(f"Attempting to sign: {app_file}")
        
        # Simulate network timestamp
        print("Timestamping file...")
        time.sleep(0.5)
        
        # Check if it's an AL extension
        try:
            with open(app_file, 'rb') as f:
                header = f.read(4)
                if header == b'NAVX':
                    print(f"Successfully signed: {app_file}")
                    print("Number of files successfully Signed: 1")
                    print("Number of warnings: 0")
                    print("Number of errors: 0")
                    sys.exit(0)
                else:
                    print("Error: File format not supported for this certificate type", file=sys.stderr)
                    sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif command == "verify":
        # Parse verify arguments
        app_file = None
        
        i = 1
        while i < len(args):
            if args[i] == "/pa":
                i += 1
            else:
                app_file = args[i]
                i += 1
        
        if not app_file or not Path(app_file).exists():
            print(f"Error: File not found: {app_file}", file=sys.stderr)
            sys.exit(1)
        
        print(f"Verifying: {app_file}")
        print("Hash of file (sha1): 1234567890ABCDEF1234567890ABCDEF12345678")
        print("Signing Certificate Subject:")
        print("    CN=Mock Test Certificate")
        print("    OU=Mock Organization")
        print("Successfully verified: " + app_file)
        sys.exit(0)
    
    else:
        print(f"Error: Unknown command: {command}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    mock_signtool()