"""
Pytest fixtures and configuration for all tests
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock

# Add scripts to path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))


@pytest.fixture
def sample_app_json():
    """Load sample app.json fixture"""
    fixture_path = Path(__file__).parent / "fixtures" / "mock_app.json"
    with open(fixture_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def appsource_app_json():
    """Load AppSource app.json fixture"""
    fixture_path = Path(__file__).parent / "fixtures" / "mock_appsource_app.json"
    with open(fixture_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def test_al_project(tmp_path, sample_app_json):
    """Create a complete test AL project structure"""
    # Create app.json
    with open(tmp_path / "app.json", 'w') as f:
        json.dump(sample_app_json, f)
    
    # Create source directory
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    
    # Create sample AL files
    (src_dir / "TestTable.Table.al").write_text("""
    table 50000 "Test Table"
    {
        DataClassification = CustomerContent;
        
        fields
        {
            field(1; "Code"; Code[20])
            {
                DataClassification = CustomerContent;
            }
            field(2; "Description"; Text[100])
            {
                DataClassification = CustomerContent;
            }
        }
        
        keys
        {
            key(PK; "Code")
            {
                Clustered = true;
            }
        }
    }
    """)
    
    (src_dir / "TestPage.Page.al").write_text("""
    page 50000 "Test Page"
    {
        PageType = Card;
        SourceTable = "Test Table";
        ApplicationArea = All;
        UsageCategory = Administration;
        
        layout
        {
            area(Content)
            {
                group(General)
                {
                    field("Code"; Rec."Code")
                    {
                        ApplicationArea = All;
                    }
                    field("Description"; Rec."Description")
                    {
                        ApplicationArea = All;
                    }
                }
            }
        }
    }
    """)
    
    return tmp_path


@pytest.fixture
def mock_symbols_directory(tmp_path):
    """Create a mock .symbols directory with sample files"""
    symbols_dir = tmp_path / ".symbols"
    symbols_dir.mkdir()
    
    # Create mock symbol files
    (symbols_dir / "Microsoft_System Application_22.0.0.0.app").write_bytes(b"mock symbol data")
    (symbols_dir / "Microsoft_Base Application_22.0.0.0.app").write_bytes(b"mock symbol data")
    
    return symbols_dir


@pytest.fixture
def mock_environment_vars(monkeypatch):
    """Set up mock environment variables"""
    env_vars = {
        'LINC_TOKEN': 'test-linc-token-12345',
        'GITHUB_ACTIONS': 'true',
        'GITHUB_WORKSPACE': '/github/workspace',
        'AZURE_CLIENT_ID': 'test-client-id',
        'AZURE_CLIENT_SECRET': 'test-client-secret',
        'AZURE_TENANT_ID': 'test-tenant-id'
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


@pytest.fixture
def mock_subprocess_success():
    """Mock successful subprocess calls"""
    mock = Mock()
    mock.return_value = Mock(
        returncode=0,
        stdout="Success",
        stderr=""
    )
    return mock


@pytest.fixture
def mock_subprocess_failure():
    """Mock failed subprocess calls"""
    mock = Mock()
    mock.return_value = Mock(
        returncode=1,
        stdout="",
        stderr="Error occurred"
    )
    return mock


@pytest.fixture
def mock_requests_success():
    """Mock successful HTTP requests"""
    mock = Mock()
    mock.return_value = Mock(
        status_code=200,
        content=b"mock response data",
        text="mock response text",
        json=lambda: {"success": True}
    )
    return mock


@pytest.fixture
def mock_requests_failure():
    """Mock failed HTTP requests"""
    mock = Mock()
    mock.return_value = Mock(
        status_code=404,
        content=b"",
        text="Not Found",
        json=lambda: {"error": "Not found"}
    )
    return mock


@pytest.fixture(autouse=True)
def reset_sys_path():
    """Reset sys.path after each test"""
    original_path = sys.path.copy()
    yield
    sys.path = original_path


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "requires_linc: marks tests that require LINC token"
    )
    config.addinivalue_line(
        "markers", "requires_compiler: marks tests that require AL compiler"
    )
