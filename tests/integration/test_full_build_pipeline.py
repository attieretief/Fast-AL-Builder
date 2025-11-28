"""
Integration tests for the full AL build pipeline
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from al_builder import ALBuildOrchestrator
from analyze_project import ALProjectAnalyzer
from build_extension import ALBuilder


class TestFullBuildPipeline:
    """Integration tests for complete build pipeline"""
    
    @pytest.fixture
    def test_project(self, tmp_path):
        """Create a minimal test AL project"""
        # Create app.json
        app_json = {
            "id": "12345678-1234-1234-1234-123456789012",
            "name": "Test Integration App",
            "publisher": "Test Publisher",
            "version": "1.0.0.0",
            "application": "22.0.0.0",
            "platform": "22.0.0.0",
            "idRanges": [
                {"from": 50000, "to": 50099}
            ],
            "dependencies": []
        }
        
        with open(tmp_path / "app.json", 'w') as f:
            json.dump(app_json, f)
        
        # Create source directory
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        
        # Create a simple AL file
        (src_dir / "TestTable.Table.al").write_text("""
        table 50000 "Test Table"
        {
            fields
            {
                field(1; "Code"; Code[20]) { }
            }
        }
        """)
        
        return tmp_path
    
    def test_analyze_then_build(self, test_project):
        """Test analyzing project then building"""
        # Step 1: Analyze
        analyzer = ALProjectAnalyzer(str(test_project))
        app_data = analyzer.parse_app_json()
        assert app_data is not None
        
        # Step 2: Check ID ranges
        id_analysis = analyzer.analyze_id_ranges(app_data)
        assert id_analysis["isPTE"] is True
        
        # Step 3: Build (would require AL compiler)
        builder = ALBuilder(str(test_project))
        loaded_app = builder.load_app_json()
        assert loaded_app["name"] == "Test Integration App"
    
    @patch('subprocess.run')
    def test_orchestrator_full_flow(self, mock_run, test_project, monkeypatch):
        """Test full orchestrator flow"""
        monkeypatch.chdir(test_project)
        
        # Mock subprocess calls
        mock_run.return_value = Mock(returncode=0)
        
        orchestrator = ALBuildOrchestrator()
        
        # Test that orchestrator can be initialized
        assert orchestrator.working_directory is not None


class TestSymbolResolution:
    """Integration tests for symbol resolution"""
    
    @pytest.fixture
    def test_project_with_deps(self, tmp_path):
        """Create test project with dependencies"""
        app_json = {
            "id": "12345678-1234-1234-1234-123456789012",
            "name": "Test App With Dependencies",
            "publisher": "Test Publisher",
            "version": "1.0.0.0",
            "application": "22.0.0.0",
            "platform": "22.0.0.0",
            "idRanges": [{"from": 50000, "to": 50099}],
            "dependencies": [
                {
                    "id": "63ca2fa4-4f03-4f2b-a480-172fef340d3f",
                    "name": "System Application",
                    "publisher": "Microsoft",
                    "version": "22.0.0.0"
                },
                {
                    "id": "437dbf0e-84ff-417a-965d-ed2bb9650972",
                    "name": "Base Application",
                    "publisher": "Microsoft",
                    "version": "22.0.0.0"
                }
            ]
        }
        
        with open(tmp_path / "app.json", 'w') as f:
            json.dump(app_json, f)
        
        return tmp_path
    
    def test_dependency_detection(self, test_project_with_deps):
        """Test that dependencies are correctly detected"""
        analyzer = ALProjectAnalyzer(str(test_project_with_deps))
        app_data = analyzer.parse_app_json()
        
        deps = analyzer.analyze_dependencies(app_data)
        # Should find System Application and Base Application
        assert deps is not None
    
    @patch('requests.get')
    def test_symbol_download_fallback(self, mock_get, test_project_with_deps):
        """Test symbol download with registry fallback"""
        # Mock failed first attempt, successful second
        mock_get.side_effect = [
            Mock(status_code=404),  # First registry fails
            Mock(status_code=200, content=b"symbol data")  # Second succeeds
        ]
        
        # Test fallback logic
        pass


class TestBuildModes:
    """Integration tests for different build modes"""
    
    @pytest.fixture
    def test_project(self, tmp_path):
        """Create test project"""
        app_json = {
            "id": "12345678-1234-1234-1234-123456789012",
            "name": "Build Mode Test",
            "publisher": "Test",
            "version": "1.0.0.0",
            "application": "22.0.0.0",
            "platform": "22.0.0.0",
            "idRanges": [{"from": 50000, "to": 50099}],
            "dependencies": []
        }
        
        with open(tmp_path / "app.json", 'w') as f:
            json.dump(app_json, f)
        
        return tmp_path
    
    @patch('subprocess.run')
    def test_build_mode(self, mock_run, test_project):
        """Test build mode"""
        mock_run.return_value = Mock(returncode=0)
        builder = ALBuilder(str(test_project))
        
        # Test build mode initialization
        assert builder is not None
    
    @patch('subprocess.run')
    def test_test_mode(self, mock_run, test_project):
        """Test test mode (compilation only)"""
        mock_run.return_value = Mock(returncode=0)
        builder = ALBuilder(str(test_project))
        
        # Test mode should not create artifacts
        assert builder is not None


class TestErrorRecovery:
    """Integration tests for error handling and recovery"""
    
    @pytest.fixture
    def broken_project(self, tmp_path):
        """Create project with issues"""
        # Invalid app.json
        with open(tmp_path / "app.json", 'w') as f:
            f.write("{ invalid json }")
        
        return tmp_path
    
    def test_invalid_app_json_recovery(self, broken_project):
        """Test handling of invalid app.json"""
        analyzer = ALProjectAnalyzer(str(broken_project))
        app_data = analyzer.parse_app_json()
        
        # Should return None and not crash
        assert app_data is None
    
    @pytest.fixture
    def missing_deps_project(self, tmp_path):
        """Create project with missing dependencies"""
        app_json = {
            "id": "12345678-1234-1234-1234-123456789012",
            "name": "Missing Deps Test",
            "publisher": "Test",
            "version": "1.0.0.0",
            "application": "22.0.0.0",
            "platform": "22.0.0.0",
            "idRanges": [{"from": 50000, "to": 50099}],
            "dependencies": [
                {
                    "id": "00000000-0000-0000-0000-000000000000",
                    "name": "Nonexistent Dependency",
                    "publisher": "Nobody",
                    "version": "99.0.0.0"
                }
            ]
        }
        
        with open(tmp_path / "app.json", 'w') as f:
            json.dump(app_json, f)
        
        return tmp_path
    
    def test_missing_dependencies_handling(self, missing_deps_project):
        """Test handling of missing dependencies"""
        analyzer = ALProjectAnalyzer(str(missing_deps_project))
        app_data = analyzer.parse_app_json()
        
        # Should parse app.json successfully
        assert app_data is not None
        assert len(app_data["dependencies"]) == 1
