"""
Unit tests for build_extension.py
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from build_extension import ALBuilder


class TestALBuilder:
    """Test suite for ALBuilder class"""
    
    @pytest.fixture
    def builder(self, tmp_path):
        """Create ALBuilder instance with temporary directory"""
        return ALBuilder(str(tmp_path))
    
    @pytest.fixture
    def sample_app_json(self):
        """Sample app.json data"""
        return {
            "id": "12345678-1234-1234-1234-123456789012",
            "name": "Test Extension",
            "publisher": "Test Publisher",
            "version": "1.0.0.0",
            "application": "22.0.0.0",
            "platform": "22.0.0.0",
            "idRanges": [
                {"from": 50000, "to": 50099}
            ],
            "dependencies": []
        }
    
    def test_init_creates_paths(self, tmp_path):
        """Test initialization creates correct paths"""
        builder = ALBuilder(str(tmp_path))
        
        assert builder.working_directory == tmp_path
        assert builder.symbols_path == tmp_path / ".symbols"
        assert builder.error_log == tmp_path / "errorLog.json"
    
    def test_log_without_color(self, builder, capsys):
        """Test logging without color"""
        builder.log("Test message")
        captured = capsys.readouterr()
        assert "Test message" in captured.out
    
    def test_log_with_color(self, builder, capsys):
        """Test logging with color"""
        builder.log("Test message", "green")
        captured = capsys.readouterr()
        assert "Test message" in captured.out
    
    def test_load_app_json_file_not_found(self, builder):
        """Test load_app_json when file doesn't exist"""
        with pytest.raises(SystemExit):
            builder.load_app_json()
    
    def test_load_app_json_success(self, builder, sample_app_json, tmp_path):
        """Test successful app.json loading"""
        app_json_path = tmp_path / "app.json"
        with open(app_json_path, 'w') as f:
            json.dump(sample_app_json, f)
        
        result = builder.load_app_json()
        
        assert result == sample_app_json
        assert result["name"] == "Test Extension"
        assert result["version"] == "1.0.0.0"
    
    def test_detect_bc_version_auto_bc22(self, builder, sample_app_json):
        """Test BC version detection for BC22"""
        result = builder.detect_bc_version(sample_app_json, 'auto')
        assert result == 'bc22'
    
    def test_detect_bc_version_explicit(self, builder, sample_app_json):
        """Test explicit BC version specification"""
        result = builder.detect_bc_version(sample_app_json, 'bc19')
        assert result == 'bc19'
    
    def test_detect_bc_version_unknown_defaults_to_bccloud(self, builder):
        """Test unknown BC version defaults to bccloud"""
        app_data = {"application": "99.0.0.0"}
        result = builder.detect_bc_version(app_data, 'auto')
        assert result == 'bccloud'
    
    @pytest.mark.parametrize("application,expected", [
        ("17.0.0.0", "bc17"),
        ("18.0.0.0", "bc18"),
        ("19.0.0.0", "bc19"),
        ("20.0.0.0", "bc20"),
        ("21.0.0.0", "bc21"),
        ("22.0.0.0", "bc22"),
        ("23.0.0.0", "bc23"),
        ("24.0.0.0", "bc24"),
    ])
    def test_detect_bc_version_parametrized(self, builder, application, expected):
        """Test BC version detection for various versions"""
        app_data = {"application": application}
        result = builder.detect_bc_version(app_data, 'auto')
        assert result == expected
    
    def test_check_appsource_app_true(self, builder):
        """Test AppSource app detection (ID >= 100000)"""
        app_data = {
            "idRanges": [
                {"from": 100000, "to": 100099}
            ]
        }
        result = builder.check_appsource_app(app_data)
        assert result is True
    
    def test_check_appsource_app_false(self, builder):
        """Test non-AppSource app detection"""
        app_data = {
            "idRanges": [
                {"from": 50000, "to": 50099}
            ]
        }
        result = builder.check_appsource_app(app_data)
        assert result is False
    
    def test_check_appsource_app_empty_ranges(self, builder):
        """Test AppSource check with empty ID ranges"""
        app_data = {"idRanges": []}
        result = builder.check_appsource_app(app_data)
        assert result is False
    
    def test_handle_version_specific_app_json_not_exists(self, builder):
        """Test version-specific app.json when file doesn't exist"""
        result = builder.handle_version_specific_app_json('bc22')
        assert result is None
    
    def test_handle_version_specific_app_json_exists(self, builder, tmp_path, sample_app_json):
        """Test version-specific app.json when file exists"""
        # Create original app.json
        app_json_path = tmp_path / "app.json"
        with open(app_json_path, 'w') as f:
            json.dump(sample_app_json, f)
        
        # Create version-specific file
        bc22_path = tmp_path / "bc22_app.json"
        version_specific = sample_app_json.copy()
        version_specific["version"] = "2.0.0.0"
        with open(bc22_path, 'w') as f:
            json.dump(version_specific, f)
        
        result = builder.handle_version_specific_app_json('bc22')
        
        assert result == "bc22_app.json"
        assert (tmp_path / "app.json.backup").exists()
        
        # Verify switched to version-specific file
        with open(app_json_path, 'r') as f:
            current_app = json.load(f)
        assert current_app["version"] == "2.0.0.0"
    
    def test_github_actions_detection(self, tmp_path, monkeypatch):
        """Test GitHub Actions environment detection"""
        monkeypatch.setenv('GITHUB_ACTIONS', 'true')
        builder = ALBuilder(str(tmp_path))
        assert builder.is_github_actions is True
    
    def test_github_actions_not_set(self, tmp_path, monkeypatch):
        """Test when not in GitHub Actions"""
        monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
        builder = ALBuilder(str(tmp_path))
        assert builder.is_github_actions is False


class TestALBuilderCompilation:
    """Test compilation-related functionality"""
    
    @pytest.fixture
    def builder(self, tmp_path):
        """Create ALBuilder with mock setup"""
        builder = ALBuilder(str(tmp_path))
        # Create minimal required structure
        (tmp_path / ".symbols").mkdir()
        return builder
    
    @patch('subprocess.run')
    def test_compilation_command_construction(self, mock_run, builder, tmp_path):
        """Test AL compilation command is constructed correctly"""
        # This would test the actual compile method
        # Placeholder for actual implementation testing
        pass


class TestALBuilderEdgeCases:
    """Test edge cases and error handling"""
    
    def test_malformed_json(self, tmp_path):
        """Test handling of malformed app.json"""
        builder = ALBuilder(str(tmp_path))
        app_json_path = tmp_path / "app.json"
        
        with open(app_json_path, 'w') as f:
            f.write("{ invalid json }")
        
        with pytest.raises((json.JSONDecodeError, SystemExit)):
            builder.load_app_json()
    
    def test_missing_required_fields(self, builder, tmp_path):
        """Test app.json with missing required fields"""
        app_json_path = tmp_path / "app.json"
        incomplete_data = {"name": "Test"}
        
        with open(app_json_path, 'w') as f:
            json.dump(incomplete_data, f)
        
        result = builder.load_app_json()
        assert result.get("name") == "Test"
        assert "version" not in result
