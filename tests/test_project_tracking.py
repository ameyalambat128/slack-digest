import pytest
import json
import os
from user_settings import UserSettings, create_project_prompt

class TestProjectTracking:
    def setup_method(self):
        """Setup test environment"""
        self.test_settings_file = "test_user_settings.json"
        self.user_settings = UserSettings(self.test_settings_file)
        self.test_user_id = "U12345TEST"
        
    def teardown_method(self):
        """Clean up test files"""
        if os.path.exists(self.test_settings_file):
            os.remove(self.test_settings_file)
    
    def test_create_project(self):
        """Test project creation"""
        project_name = "test-hardware-project"
        channels = ["hardware", "software", "mechanical"]
        keywords = ["PCB", "schematic", "test"]
        
        self.user_settings.create_project(self.test_user_id, project_name, channels, keywords)
        
        # Verify project was created
        project = self.user_settings.get_project(self.test_user_id, project_name)
        assert project is not None
        assert project["channels"] == channels
        assert project["keywords"] == keywords
        assert project["active"] == True
        assert "created_at" in project
    
    def test_get_user_projects(self):
        """Test retrieving all user projects"""
        # Create multiple projects
        self.user_settings.create_project(self.test_user_id, "project1", ["ch1", "ch2"])
        self.user_settings.create_project(self.test_user_id, "project2", ["ch3", "ch4"], ["keyword1"])
        
        projects = self.user_settings.get_user_projects(self.test_user_id)
        assert len(projects) == 2
        assert "project1" in projects
        assert "project2" in projects
    
    def test_update_project_channels(self):
        """Test updating project channels"""
        project_name = "test-project"
        original_channels = ["ch1", "ch2"]
        new_channels = ["ch1", "ch2", "ch3"]
        
        self.user_settings.create_project(self.test_user_id, project_name, original_channels)
        self.user_settings.update_project_channels(self.test_user_id, project_name, new_channels)
        
        project = self.user_settings.get_project(self.test_user_id, project_name)
        assert project["channels"] == new_channels
    
    def test_update_project_keywords(self):
        """Test updating project keywords"""
        project_name = "test-project"
        channels = ["ch1"]
        original_keywords = ["keyword1"]
        new_keywords = ["keyword1", "keyword2", "keyword3"]
        
        self.user_settings.create_project(self.test_user_id, project_name, channels, original_keywords)
        self.user_settings.update_project_keywords(self.test_user_id, project_name, new_keywords)
        
        project = self.user_settings.get_project(self.test_user_id, project_name)
        assert project["keywords"] == new_keywords
    
    def test_toggle_project_status(self):
        """Test toggling project active status"""
        project_name = "test-project"
        channels = ["ch1"]
        
        self.user_settings.create_project(self.test_user_id, project_name, channels)
        
        # Toggle to inactive
        new_status = self.user_settings.toggle_project_status(self.test_user_id, project_name)
        assert new_status == False
        
        project = self.user_settings.get_project(self.test_user_id, project_name)
        assert project["active"] == False
        
        # Toggle back to active
        new_status = self.user_settings.toggle_project_status(self.test_user_id, project_name)
        assert new_status == True
        
        project = self.user_settings.get_project(self.test_user_id, project_name)
        assert project["active"] == True
    
    def test_delete_project(self):
        """Test project deletion"""
        project_name = "test-project"
        channels = ["ch1"]
        
        self.user_settings.create_project(self.test_user_id, project_name, channels)
        assert self.user_settings.get_project(self.test_user_id, project_name) is not None
        
        self.user_settings.delete_project(self.test_user_id, project_name)
        assert self.user_settings.get_project(self.test_user_id, project_name) is None
    
    def test_create_project_prompt(self):
        """Test project-specific prompt creation"""
        project_name = "hardware-v2"
        channels = ["hardware", "software", "mechanical"]
        
        prompt = create_project_prompt(project_name, channels)
        
        assert project_name in prompt
        assert "hardware" in prompt
        assert "software" in prompt
        assert "mechanical" in prompt
        assert "PROJECT-FOCUSED" in prompt
        assert "Cross-team coordination" in prompt
        assert "json_object" in prompt.lower() or "json" in prompt.lower()
        
    def test_create_project_prompt_with_custom_prompt(self):
        """Test project prompt with user customization"""
        project_name = "test-project"
        channels = ["ch1", "ch2"]
        custom_prompt = "Focus on technical risks and compliance issues"
        
        prompt = create_project_prompt(project_name, channels, custom_prompt)
        
        assert project_name in prompt
        assert custom_prompt in prompt
        assert "ADDITIONAL PROJECT CONTEXT" in prompt 