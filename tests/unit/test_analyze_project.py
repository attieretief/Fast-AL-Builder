"""
Unit tests for analyze_project.py
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from analyze_project import ALProjectAnalyzer


class TestALProjectAnalyzer:
    """Test suite for ALProjectAnalyzer class"""
    
    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create analyzer instance with temporary directory"""
        return ALProjectAnalyzer(str(tmp_path))
    
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
            "dependencies": [
                {
                    "id": "63ca2fa4-4f03-4f2b-a480-172fef340d3f",
                    "name": "System Application",
                    "publisher": "Microsoft",
                    "version": "22.0.0.0"
                }
            ]
        }
    
    def test_init_working_directory(self, tmp_path):
        """Test initialization with working directory"""
        analyzer = ALProjectAnalyzer(str(tmp_path))
        assert analyzer.working_directory == tmp_path
    
    def test_log_without_color(self, analyzer, capsys):
        """Test logging without color"""
        analyzer.log("Test message")
        captured = capsys.readouterr()
        assert "Test message" in captured.out
    
    def test_log_with_color(self, analyzer, capsys):
        """Test logging with color"""
        analyzer.log("Test message", "green")
        captured = capsys.readouterr()
        assert "Test message" in captured.out
    
    def test_parse_app_json_not_found(self, analyzer, capsys):
        """Test parse_app_json when file doesn't exist"""
        result = analyzer.parse_app_json()
        assert result is None
        captured = capsys.readouterr()
        assert "not found" in captured.out
    
    def test_parse_app_json_success(self, analyzer, tmp_path, sample_app_json):
        """Test successful app.json parsing"""
        app_json_path = tmp_path / "app.json"
        with open(app_json_path, 'w') as f:
            json.dump(sample_app_json, f)
        
        result = analyzer.parse_app_json()
        
        assert result is not None
        assert result["name"] == "Test Extension"
        assert result["version"] == "1.0.0.0"
    
    def test_parse_app_json_invalid_json(self, analyzer, tmp_path, capsys):
        """Test handling of invalid JSON"""
        app_json_path = tmp_path / "app.json"
        with open(app_json_path, 'w') as f:
            f.write("{ invalid json }")
        
        result = analyzer.parse_app_json()
        assert result is None
        captured = capsys.readouterr()
        assert "Failed to parse" in captured.out
    
    def test_analyze_id_ranges_appsource(self, analyzer):
        """Test ID range analysis for AppSource app"""
        app_data = {
            "idRanges": [
                {"from": 100000, "to": 100099}
            ]
        }
        
        result = analyzer.analyze_id_ranges(app_data)
        
        assert result["isAppSource"] is True
        assert result["isPTE"] is False
        assert result["isInternal"] is False
    
    def test_analyze_id_ranges_pte(self, analyzer):
        """Test ID range analysis for PTE"""
        app_data = {
            "idRanges": [
                {"from": 50000, "to": 50099}
            ]
        }
        
        result = analyzer.analyze_id_ranges(app_data)
        
        assert result["isAppSource"] is False
        assert result["isPTE"] is True
        assert result["isInternal"] is False
    
    def test_analyze_id_ranges_custom(self, analyzer):
        """Test ID range analysis for custom range"""
        app_data = {
            "idRanges": [
                {"from": 1000, "to": 1999}
            ]
        }
        
        result = analyzer.analyze_id_ranges(app_data)
        
        assert result["hasCustomRange"] is True
    
    def test_analyze_id_ranges_empty(self, analyzer):
        """Test ID range analysis with empty ranges"""
        app_data = {"idRanges": []}
        
        result = analyzer.analyze_id_ranges(app_data)
        
        assert result["isAppSource"] is False
        assert result["isPTE"] is False
        assert result["ranges"] == []
    
    def test_analyze_dependencies(self, analyzer, sample_app_json):
        """Test dependency analysis"""
        result = analyzer.analyze_dependencies(sample_app_json)
        
        assert result is not None
        # Should identify System Application dependency
    
    @pytest.mark.parametrize("id_range,expected_type", [
        ({"from": 100000, "to": 199999}, "AppSource"),
        ({"from": 50000, "to": 99999}, "PTE"),
        ({"from": 1, "to": 49999}, "Custom"),
    ])
    def test_id_range_detection_parametrized(self, analyzer, id_range, expected_type):
        """Test various ID range types"""
        app_data = {"idRanges": [id_range]}
        result = analyzer.analyze_id_ranges(app_data)
        
        if expected_type == "AppSource":
            assert result["isAppSource"] is True
        elif expected_type == "PTE":
            assert result["isPTE"] is True
        elif expected_type == "Custom":
            assert result["hasCustomRange"] is True


class TestALProjectAnalyzerAdvanced:
    """Advanced test cases for project analysis"""
    
    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create analyzer with test project structure"""
        analyzer = ALProjectAnalyzer(str(tmp_path))
        
        # Create test AL files
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        
        (src_dir / "TestTable.Table.al").write_text("""
        table 50000 "Test Table"
        {
            fields
            {
                field(1; "Code"; Code[20]) { }
            }
        }
        """)
        
        (src_dir / "TestPage.Page.al").write_text("""
        page 50000 "Test Page"
        {
            SourceTable = "Test Table";
        }
        """)
        
        return analyzer
    
    def test_multiple_dependencies(self, tmp_path):
        """Test analysis with multiple dependencies"""
        analyzer = ALProjectAnalyzer(str(tmp_path))
        
        app_data = {
            "dependencies": [
                {"id": "guid1", "name": "Dep1", "version": "1.0.0.0"},
                {"id": "guid2", "name": "Dep2", "version": "2.0.0.0"},
                {"id": "guid3", "name": "Dep3", "version": "3.0.0.0"}
            ]
        }
        
        result = analyzer.analyze_dependencies(app_data)
        assert result is not None
    
    def test_mixed_id_ranges(self, tmp_path):
        """Test app with mixed ID ranges"""
        analyzer = ALProjectAnalyzer(str(tmp_path))
        
        app_data = {
            "idRanges": [
                {"from": 50000, "to": 50099},  # PTE
                {"from": 100000, "to": 100099}  # AppSource
            ]
        }
        
        result = analyzer.analyze_id_ranges(app_data)
        
        # Should detect both types
        assert result["isPTE"] is True
        assert result["isAppSource"] is True
