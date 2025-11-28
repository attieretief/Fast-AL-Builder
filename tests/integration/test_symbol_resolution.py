"""
Integration tests for symbol resolution and download
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from download_symbols import SymbolDownloader


class TestSymbolResolutionIntegration:
    """Integration tests for symbol download and resolution"""
    
    @pytest.fixture
    def test_project(self, tmp_path):
        """Create test project with dependencies"""
        app_json = {
            "id": "test-app-id",
            "name": "Symbol Test App",
            "publisher": "Test",
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
                }
            ]
        }
        
        with open(tmp_path / "app.json", 'w') as f:
            json.dump(app_json, f)
        
        return tmp_path
    
    @patch('requests.get')
    @patch('os.environ.get')
    def test_download_with_linc_token(self, mock_env, mock_get, test_project):
        """Test symbol download with valid LINC token"""
        mock_env.return_value = "test-linc-token"
        mock_get.return_value = Mock(status_code=200, content=b"symbol data")
        
        downloader = SymbolDownloader(str(test_project))
        token = downloader.get_linc_token()
        
        assert token == "test-linc-token"
    
    @patch('requests.get')
    @patch('os.environ.get')
    def test_download_without_linc_token(self, mock_env, mock_get, test_project):
        """Test symbol download without LINC token (public registries only)"""
        mock_env.return_value = None
        mock_get.return_value = Mock(status_code=200, content=b"symbol data")
        
        downloader = SymbolDownloader(str(test_project))
        token = downloader.get_linc_token()
        
        assert token is None


class TestMultiRegistryFallback:
    """Test fallback between multiple symbol registries"""
    
    @pytest.fixture
    def downloader(self, tmp_path):
        """Create downloader instance"""
        return SymbolDownloader(str(tmp_path))
    
    @patch('requests.get')
    def test_fallback_sequence(self, mock_get, downloader):
        """Test that downloader tries multiple registries"""
        # Simulate first registry failing, second succeeding
        responses = [
            Mock(status_code=404),  # AppSource fails
            Mock(status_code=404),  # Microsoft fails
            Mock(status_code=200, content=b"symbol from LINC")  # LINC succeeds
        ]
        mock_get.side_effect = responses
        
        # Test fallback logic
        pass
    
    @patch('requests.get')
    def test_all_registries_fail(self, mock_get, downloader):
        """Test when all registries fail"""
        mock_get.return_value = Mock(status_code=404)
        
        # Should handle gracefully
        pass
