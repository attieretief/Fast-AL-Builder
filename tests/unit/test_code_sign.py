"""Unit tests for the AzureSignTool-based signer."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import code_sign
from code_sign import CodeSigner


def _create_app(tmp_path) -> Path:
    app_file = tmp_path / "test.app"
    app_file.write_bytes(b"NAVX")
    return app_file


def test_find_azuresigntool_uses_path(monkeypatch):
    monkeypatch.setattr(code_sign.shutil, "which", lambda _: r"C:\\AzureSignTool.exe")
    signer = CodeSigner()
    assert signer.azuresigntool_path == r"C:\\AzureSignTool.exe"


def test_sign_app_file_success(monkeypatch, tmp_path):
    app_file = _create_app(tmp_path)
    signer = CodeSigner(azuresigntool_path=r"C:\\AzureSignTool.exe")

    captured = {}

    class Result:
        returncode = 0
        stdout = "Signed"
        stderr = ""

    def fake_run(cmd, capture_output, text):
        captured["cmd"] = cmd
        return Result()

    monkeypatch.setattr(code_sign.subprocess, "run", fake_run)

    success = signer.sign_app_file(
        app_file_path=str(app_file),
        vault_url="https://vault.vault",
        cert_name="my-cert",
        client_id="client",
        client_secret="secret",
        tenant_id="tenant",
        timestamp_url="http://timestamp.example.com"
    )

    assert success is True
    assert captured["cmd"][0] == r"C:\\AzureSignTool.exe"
    assert "my-cert" in captured["cmd"]


def test_sign_app_file_missing_tool(tmp_path):
    app_file = _create_app(tmp_path)
    signer = CodeSigner(azuresigntool_path=None)

    success = signer.sign_app_file(
        app_file_path=str(app_file),
        vault_url="https://vault",
        cert_name="cert",
        client_id="client",
        client_secret="secret",
        tenant_id="tenant"
    )

    assert success is False


def test_sign_app_file_missing_parameters(tmp_path):
    app_file = _create_app(tmp_path)
    signer = CodeSigner(azuresigntool_path=r"C:\\AzureSignTool.exe")

    assert signer.sign_app_file(
        app_file_path=str(app_file),
        vault_url="https://vault",
        cert_name="",
        client_id="client",
        client_secret="secret",
        tenant_id="tenant"
    ) is False


def test_sign_app_file_missing_file(tmp_path):
    signer = CodeSigner(azuresigntool_path=r"C:\\AzureSignTool.exe")
    missing = tmp_path / "missing.app"

    assert signer.sign_app_file(
        app_file_path=str(missing),
        vault_url="https://vault",
        cert_name="cert",
        client_id="client",
        client_secret="secret",
        tenant_id="tenant"
    ) is False
