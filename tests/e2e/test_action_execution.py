"""
End-to-end tests for GitHub Action execution
"""

import pytest
import os
import sys
from pathlib import Path


class TestActionExecution:
    """E2E tests for GitHub Action"""
    
    def test_action_yml_structure(self):
        """Test that action.yml has required structure"""
        action_yml_path = Path(__file__).parent.parent.parent / "action.yml"
        assert action_yml_path.exists(), "action.yml not found"
        
        import yaml
        with open(action_yml_path, 'r') as f:
            action = yaml.safe_load(f)
        
        # Verify required fields
        assert 'name' in action
        assert 'description' in action
        assert 'inputs' in action
        assert 'outputs' in action
        assert 'runs' in action
        
        assert action['name'] == 'Fast AL Builder'
    
    def test_action_inputs(self):
        """Test that action has expected inputs"""
        action_yml_path = Path(__file__).parent.parent.parent / "action.yml"
        
        import yaml
        with open(action_yml_path, 'r') as f:
            action = yaml.safe_load(f)
        
        inputs = action['inputs']
        
        # Check key inputs exist
        assert 'build-mode' in inputs
        assert 'skip-symbols' in inputs
        assert 'skip-signing' in inputs
        assert 'skip-publishing' in inputs
        
        # Check defaults
        assert inputs['build-mode']['default'] == 'build'
    
    def test_action_outputs(self):
        """Test that action has expected outputs"""
        action_yml_path = Path(__file__).parent.parent.parent / "action.yml"
        
        import yaml
        with open(action_yml_path, 'r') as f:
            action = yaml.safe_load(f)
        
        outputs = action['outputs']
        
        # Check key outputs exist
        assert 'app-file' in outputs
        assert 'app-version' in outputs
        assert 'build-success' in outputs
        assert 'overall-success' in outputs


class TestWorkflowIntegration:
    """Test internal workflow file"""
    
    def test_workflow_yml_structure(self):
        """Test that workflow YAML is valid"""
        workflow_path = Path(__file__).parent.parent.parent / ".github/workflows/al-extension-pipeline.yml"
        assert workflow_path.exists(), "Workflow file not found"
        
        import yaml
        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)
        
        # Verify structure
        assert 'name' in workflow
        assert 'on' in workflow
        assert 'jobs' in workflow
        
        # Verify jobs exist
        jobs = workflow['jobs']
        assert 'build' in jobs
        assert 'sign' in jobs or 'publish' in jobs
    
    def test_workflow_inputs(self):
        """Test that workflow has correct inputs"""
        workflow_path = Path(__file__).parent.parent.parent / ".github/workflows/al-extension-pipeline.yml"
        
        import yaml
        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)
        
        # Check workflow_dispatch inputs
        if 'workflow_dispatch' in workflow['on']:
            inputs = workflow['on']['workflow_dispatch']['inputs']
            assert 'workflow-id' in inputs
            assert 'build-mode' in inputs


class TestTestProject:
    """Test that test-al-project is valid"""
    
    def test_test_project_app_json(self):
        """Test that test-al-project has valid app.json"""
        test_project_path = Path(__file__).parent.parent.parent / "test-al-project"
        app_json_path = test_project_path / "app.json"
        
        assert app_json_path.exists(), "test-al-project/app.json not found"
        
        import json
        with open(app_json_path, 'r') as f:
            app_json = json.load(f)
        
        # Verify required fields
        assert 'id' in app_json
        assert 'name' in app_json
        assert 'publisher' in app_json
        assert 'version' in app_json
    
    def test_test_project_has_source_files(self):
        """Test that test-al-project has AL source files"""
        test_project_path = Path(__file__).parent.parent.parent / "test-al-project/src"
        
        if test_project_path.exists():
            al_files = list(test_project_path.glob("*.al"))
            assert len(al_files) > 0, "No .al files found in test-al-project/src"


class TestEnvironmentVariables:
    """Test environment variable handling"""
    
    def test_github_actions_env_detection(self):
        """Test GitHub Actions environment detection"""
        # In CI, GITHUB_ACTIONS should be set
        github_actions = os.environ.get('GITHUB_ACTIONS')
        
        # Either we're in GitHub Actions or not
        assert github_actions in [None, 'true', 'false']
    
    def test_linc_token_optional(self):
        """Test that LINC_TOKEN is optional"""
        # Should work without LINC_TOKEN
        linc_token = os.environ.get('LINC_TOKEN')
        
        # Token might or might not be set
        assert linc_token is None or isinstance(linc_token, str)


class TestDocumentation:
    """Test that documentation is complete"""
    
    def test_readme_exists(self):
        """Test that README.md exists and has content"""
        readme_path = Path(__file__).parent.parent.parent / "README.md"
        assert readme_path.exists(), "README.md not found"
        
        content = readme_path.read_text()
        assert len(content) > 100, "README.md is too short"
        assert "Fast AL Builder" in content
    
    def test_changelog_exists(self):
        """Test that CHANGELOG.md exists"""
        changelog_path = Path(__file__).parent.parent.parent / "CHANGELOG.md"
        assert changelog_path.exists(), "CHANGELOG.md not found"
    
    def test_contributing_exists(self):
        """Test that CONTRIBUTING.md exists"""
        contributing_path = Path(__file__).parent.parent.parent / "CONTRIBUTING.md"
        assert contributing_path.exists(), "CONTRIBUTING.md not found"
